import os
import re
import json
import pypandoc
import google.generativeai as genai
from dotenv import load_dotenv

# --- 1. CONFIGURAZIONE ---
def load_config():
    """Carica le configurazioni per il processo del Regolamento Camera."""
    proj_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    load_dotenv(os.path.join(proj_root, "a_chiavi", ".env"))
    
    output_dir = os.path.join(proj_root, "d_outputs", "00_structured", "b_regcam")
    
    config = {
        "model": "gemini-2.5-pro",
        "input_indice_docx": os.path.join(proj_root, "b_testi", "b_regcam", "regcam_indice.docx"),
        "output_dir": output_dir,
        "output_json_structure": os.path.join(output_dir, "regcam_structure.json")
    }
    
    try:
        os.makedirs(config["output_dir"], exist_ok=True)
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        client = genai.GenerativeModel(config["model"])
        print("✅ Configurazione caricata e client AI inizializzato.")
        return config, client
    except Exception as e:
        print(f"❌ ERRORE CRITICO in fase di inizializzazione: {e}")
        exit()

# --- 2. FUNZIONI DI UTILITÀ ---
def clean_text(text: str) -> str:
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
    text = re.sub(r'\n{2,}', '\n', text)
    return text.strip()

def clean_json_from_text(text: str) -> str:
    match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', text)
    if match:
        return match.group(1)
    json_start = text.find('{')
    json_end = text.rfind('}')
    return text[json_start:json_end+1] if json_start != -1 and json_end != -1 else "{}"

# --- 3. LOGICA DI ESTRAZIONE STRUTTURA ---
def create_structure_file(config, client):
    """Legge l'indice del Regolamento e lo struttura secondo lo schema canonico."""
    try:
        print(f"📄 Estrazione testo dall'indice: {os.path.basename(config['input_indice_docx'])}")
        raw_text = pypandoc.convert_file(config['input_indice_docx'], 'plain', format='docx')
        indice_text = clean_text(raw_text)
        print("✅ Testo dell'indice del Regolamento estratto e pulito.")
    except Exception as e:
        print(f"❌ ERRORE PANDOC: {e}")
        return

    prompt = (
        "Sei un assistente di data engineering. Il tuo compito è analizzare l'indice del Regolamento della Camera e trasformarlo in un oggetto JSON che segue uno schema canonico ricorsivo.\n\n"
        "**1. SCHEMA CANONICO DELL'OUTPUT JSON (SEGUIRE ALLA LETTERA):**\n"
        "L'oggetto JSON radice deve avere le seguenti chiavi:\n"
        "- `document_title`: 'Regolamento della Camera dei Deputati'.\n"
        "- `document_type`: 'regolamento_parlamentare'.\n"
        "- `total_articles`: Il numero totale di articoli unici (conta '15-bis' come un articolo).\n"
        "- `structure`: Un array di oggetti 'nodo'.\n\n"
        "Ogni 'nodo' nella struttura deve avere le seguenti chiavi:\n"
        "- `node_id`: Un ID programmatico (es. 'P1', 'P1-C1').\n"
        "- `level`: Il livello di profondità (1 per le Parti, 2 per i Capi).\n"
        "- `title`: Il titolo completo del nodo (es. 'PARTE PRIMA - ...', 'CAPO I - ...').\n"
        "- `articles`: Un array di stringhe con i numeri degli articoli del nodo. Se il nodo è un contenitore, l'array è vuoto.\n"
        "- `children`: Un array di altri oggetti 'nodo' per i sottonodi.\n\n"
        "**2. GERARCHIA DA MAPPARE (PARTE -> CAPO):**\n"
        "La gerarchia è semplice: Le 'Parti' sono nodi di `level: 1` e contengono un array di `children` che sono i 'Capi'. I 'Capi' sono nodi di `level: 2` e contengono direttamente gli `articles`.\n"
        "**ATTENZIONE:** La 'DISPOSIZIONE TRANSITORIA' alla fine deve essere trattata come un NODO di `level: 2` (come un Capo) dentro l'ultima Parte.\n\n"
        "**3. REGOLE FINALI:**\n"
        "- Sii meticoloso. Includi tutti gli articoli.\n"
        "- Produci SOLO l'oggetto JSON valido, senza testo o commenti, racchiuso in ```json ... ```.\n\n"
        "--- TESTO DELL'INDICE DA ANALIZZARE ---\n"
        f"{indice_text}\n"
        "--- FINE DEL TESTO ---"
    )

    try:
        print("🧠 Invio indice del Regolamento all'IA per l'analisi strutturale...")
        response = client.generate_content(prompt)
        json_text = clean_json_from_text(response.text)
        
        print("✅ Analisi AI completata. Tento il parsing del JSON...")
        structure_data = json.loads(json_text)
        
        with open(config['output_json_structure'], "w", encoding="utf-8") as f:
            json.dump(structure_data, f, ensure_ascii=False, indent=2)
        
        print(f"🎉 File di struttura del Regolamento creato con successo in:\n{config['output_json_structure']}")
        print(f"   - Articoli totali rilevati: {structure_data.get('total_articles', 'N/D')}")
        
    except Exception as e:
        print(f"⚠️ Errore durante la creazione del file di struttura: {e}")
        if 'response' in locals():
            print(f"--- Risposta grezza ricevuta: ---\n{response.text}")

# --- 4. AVVIO ---
if __name__ == "__main__":
    config, client = load_config()
    create_structure_file(config, client)