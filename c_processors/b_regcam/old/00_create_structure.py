# g_src/dispatcher/0_create_structure.py

import os
import re
import json
import pypandoc
import google.generativeai as genai
from dotenv import load_dotenv

# --- 1. CONFIGURAZIONE ---
def load_config():
    """Carica le configurazioni e inizializza i client."""
    proj_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    load_dotenv(os.path.join(proj_root, "a_chiavi", ".env"))
    
    config = {
        "model": "gemini-2.5-pro-preview-06-05",
        "input_indice_docx": os.path.join(proj_root, "b_testi", "regolamento_indice.docx"),
        "output_dir": os.path.join(proj_root, "d_structured_outputs"),
        "output_json_structure": "" # Verrà completato dopo
    }
    config["output_json_structure"] = os.path.join(config["output_dir"], "regolamento_camera_structure.json")
    
    try:
        os.makedirs(config["output_dir"], exist_ok=True)
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        client = genai.GenerativeModel(config["model"])
        print("✅ Configurazione caricata e client AI inizializzato.")
        return config, client
    except Exception as e:
        print(f"❌ ERRORE CRITICO in fase di inizializzazione: {e}")
        exit()

# --- 2. LOGICA DI ESTRAZIONE STRUTTURA ---

def clean_text(text: str) -> str:
    """Pulisce il testo estratto da pandoc."""
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
    text = re.sub(r'\n{2,}', '\n', text)
    return text.strip()

def clean_json_from_text(text: str) -> str:
    """Estrae in modo robusto un blocco JSON da una stringa di testo."""
    match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', text)
    if match:
        return match.group(1)
    json_start = text.find('{')
    json_end = text.rfind('}')
    if json_start != -1 and json_end != -1:
        return text[json_start:json_end+1]
    return "{}"

def create_structure_file(config, client):
    """
    Legge un file DOCX contenente un indice, usa un LLM per strutturarlo
    e salva il risultato in un file JSON.
    """
    try:
        print(f"📄 Estrazione testo dall'indice: {os.path.basename(config['input_indice_docx'])}")
        raw_text = pypandoc.convert_file(config['input_indice_docx'], 'plain', format='docx')
        indice_text = clean_text(raw_text)
        print("✅ Testo dell'indice estratto e pulito.")
    except Exception as e:
        print(f"❌ ERRORE PANDOC: {e}")
        return

    # Prompt per l'IA, istruita a creare la struttura JSON desiderata
    prompt = (
        "Sei un assistente di data engineering. Il tuo compito è analizzare il testo di un indice di un documento legale e trasformarlo in un oggetto JSON strutturato. L'obiettivo è creare una 'mappa' del documento.\n\n"
        "**SCHEMA DEL JSON DI OUTPUT:**\n"
        "L'oggetto JSON deve avere le seguenti chiavi:\n"
        "- `documento_titolo`: Il titolo del documento.\n"
        "- `totale_articoli`: Il numero totale di articoli menzionati nell'indice.\n"
        "- `parti`: Un array di oggetti, dove ogni oggetto rappresenta una 'Parte' e contiene:\n"
        "  - `parte_titolo`: Il titolo completo della parte.\n"
        "  - `capi`: Un array di oggetti, dove ogni oggetto rappresenta un 'Capo' e contiene:\n"
        "    - `capo_titolo`: Il titolo completo del capo.\n"
        "    - `articoli`: Un array di stringhe, contenente i numeri di tutti gli articoli che appartengono a quel capo.\n"
        "    - `conta_articoli`: Il numero totale di articoli in quel capo.\n\n"
        "**ISTRUZIONI IMPORTANTI:**\n"
        "1.  Analizza attentamente la gerarchia (Parti, Capi, Articoli).\n"
        "2.  Estrai i numeri degli articoli associati a ogni capo. Se un capo copre un range (es. Art. 1-10), elenca tutti i numeri individualmente.\n"
        "3.  Calcola il conteggio totale degli articoli e il conteggio per ogni capo.\n"
        "4.  Produci SOLO l'oggetto JSON valido, senza testo o spiegazioni aggiuntive.\n\n"
        "--- TESTO DELL'INDICE DA ANALIZZARE ---\n"
        f"{indice_text}\n"
        "--- FINE DEL TESTO ---"
    )

    try:
        print("🧠 Invio indice all'IA per l'analisi strutturale...")
        response = client.generate_content(prompt)
        json_text = clean_json_from_text(response.text)
        
        print("✅ Analisi AI completata. Tento il parsing del JSON...")
        structure_data = json.loads(json_text)
        
        # Salvataggio del file JSON strutturato
        with open(config['output_json_structure'], "w", encoding="utf-8") as f:
            json.dump(structure_data, f, ensure_ascii=False, indent=2)
        
        print(f"🎉 File di struttura creato con successo in:\n{config['output_json_structure']}")
        
    except Exception as e:
        print(f"⚠️ Errore durante la creazione del file di struttura: {e}")
        if 'response' in locals():
            print(f"--- Risposta grezza ricevuta: ---\n{response.text}")

# --- 3. AVVIO ---
if __name__ == "__main__":
    app_config, app_client = load_config()
    create_structure_file(app_config, app_client)