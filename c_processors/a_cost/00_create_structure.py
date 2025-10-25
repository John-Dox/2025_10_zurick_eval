import os
import re
import json
import pypandoc
import google.generativeai as genai
from dotenv import load_dotenv

# --- 1. CONFIGURAZIONE SPECIFICA PER LA COSTITUZIONE ---
def load_config():
    """Carica le configurazioni e inizializza i client per il processo della Costituzione."""
    # Percorsi basati sulla nuova struttura della repository
    proj_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    load_dotenv(os.path.join(proj_root, "a_chiavi", ".env"))
    
    config = {
        "model": "gemini-2.5-pro",
        "input_indice_docx": os.path.join(proj_root, "b_testi", "a_cost", "cost_2023_22_10_indice.docx"),
        "output_dir": os.path.join(proj_root, "d_outputs", "00_structured", "a_cost"),
        "output_json_structure": ""
    }
    config["output_json_structure"] = os.path.join(config["output_dir"], "cost_structure.json")
    
    try:
        os.makedirs(config["output_dir"], exist_ok=True)
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        client = genai.GenerativeModel(config["model"])
        print("✅ Configurazione caricata e client AI inizializzato.")
        return config, client
    except Exception as e:
        print(f"❌ ERRORE CRITICO in fase di inizializzazione: {e}")
        exit()

# --- 2. FUNZIONI DI UTILITÀ (INVARIATE) ---

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

# --- 3. LOGICA DI ESTRAZIONE STRUTTURA PER LA COSTITUZIONE ---

def create_structure_file(config, client):
    """
    Legge l'indice della Costituzione, usa un LLM per strutturarlo secondo lo
    schema canonico e lo salva in un file JSON.
    """
    try:
        print(f"📄 Estrazione testo dall'indice: {os.path.basename(config['input_indice_docx'])}")
        raw_text = pypandoc.convert_file(config['input_indice_docx'], 'plain', format='docx')
        indice_text = clean_text(raw_text)
        print("✅ Testo dell'indice della Costituzione estratto e pulito.")
    except Exception as e:
        print(f"❌ ERRORE PANDOC: {e}")
        return

    # --- NUOVO PROMPT SPECIFICO PER LA COSTITUZIONE CON SCHEMA CANONICO E AD ALBERO ---
    prompt = (
        "Sei un assistente di data engineering esperto in diritto costituzionale. Il tuo compito è analizzare l'indice della Costituzione Italiana e trasformarlo in un oggetto JSON che segue uno schema canonico ricorsivo.\n\n"
        "**1. SCHEMA CANONICO DELL'OUTPUT JSON:**\n"
        "L'oggetto JSON radice deve avere le seguenti chiavi:\n"
        "- `document_title`: 'Costituzione della Repubblica Italiana'.\n"
        "- `document_type`: 'costituzione'.\n"
        "- `total_articles`: Il numero totale di articoli (solo quelli con numero arabo, da 1 a 139).\n"
        "- `total_disposizioni_finali`: Il numero totale delle Disposizioni Transitorie e Finali (quelle con numero romano).\n"
        "- `structure`: Un array di oggetti 'nodo', che rappresentano le sezioni di primo livello.\n\n"
        "Ogni 'nodo' nella struttura, a qualsiasi livello, deve avere le seguenti chiavi:\n"
        "- `node_id`: Un ID programmatico univoco (es. 'P1', 'P1-T1', 'P2-T1-S1').\n"
        "- `level`: Il livello di profondità del nodo (1 per il livello più alto).\n"
        "- `title`: Il titolo completo e testuale del nodo (es. 'PARTE PRIMA. DIRITTI E DOVERI DEI CITTADINI').\n"
        "- `articles`: Un array di stringhe contenente i numeri degli articoli che appartengono DIRETTAMENTE a questo nodo. Se un nodo raggruppa solo altri nodi, questo array sarà vuoto.\n"
        "- `children`: Un array di altri oggetti 'nodo' che rappresentano i sottonodi. Se un nodo è una 'foglia' (non ha suddivisioni), questo array sarà vuoto.\n\n"
        "**2. ESEMPIO DI GERARCHIA AD ALBERO DA SEGUIRE:**\n"
        "Questa è la gerarchia che devi mappare:\n"
        "```\n"
        "./\n"
        "├── PRINCIPI FONDAMENTALI\n"
        "├── PARTE PRIMA. DIRITTI E DOVERI DEI CITTADINI/\n"
        "│   ├── Titolo I. Rapporti civili\n"
        "│   ├── Titolo II. Rapporti etico-sociali\n"
        "│   ├── Titolo III. Rapporti economici\n"
        "│   └── Titolo IV. Rapporti politici\n"
        "├── PARTE SECONDA. ORDINAMENTO DELLA REPUBBLICA/\n"
        "│   ├── Titolo I. Il Parlamento/\n"
        "│   │   ├── Sezione I. Le Camere\n"
        "│   │   └── Sezione II. La formazione delle leggi\n"
        "│   ├── Titolo II. Il Presidente della Repubblica\n"
        "│   ├── Titolo III. Il Governo/\n"
        "│   │   ├── Sezione I. Il Consiglio dei ministri\n"
        "│   │   ├── Sezione II. La Pubblica Amministrazione\n"
        "│   │   └── Sezione III. Gli organi ausiliari\n"
        "│   ├── Titolo IV. La magistratura/\n"
        "│   │   ├── Sezione I. Ordinamento giurisdizionale\n"
        "│   │   └── Sezione II. Norme sulla giurisdizione\n"
        "│   ├── Titolo V. Le Regioni, le Province, i Comuni\n"
        "│   └── Titolo VI. Garanzie costituzionali/\n"
        "│       ├── Sezione I. La Corte costituzionale\n"
        "│       └── Sezione II. Revisione della Costituzione. Leggi costituzionali\n"
        "└── DISPOSIZIONI TRANSITORIE E FINALI\n"
        "```\n\n"
        "**3. REGOLE FINALI:**\n"
        "- Le sezioni 'PRINCIPI FONDAMENTALI' e 'DISPOSIZIONI TRANSITORIE E FINALI' sono nodi di `level: 1`.\n"
        "- Per le 'DISPOSIZIONI TRANSITORIE E FINALI', gli 'articoli' sono i numeri romani ('I', 'II', ecc.).\n"
        "- Sii meticoloso. Includi tutti gli articoli e le disposizioni. La precisione è fondamentale.\n"
        "- Produci SOLO l'oggetto JSON valido, senza testo o commenti aggiuntivi, racchiuso in ```json ... ```.\n\n"
        "--- TESTO DELL'INDICE DA ANALIZZARE ---\n"
        f"{indice_text}\n"
        "--- FINE DEL TESTO ---"
    )

    try:
        print("🧠 Invio indice della Costituzione all'IA per l'analisi strutturale...")
        response = client.generate_content(prompt)
        json_text = clean_json_from_text(response.text)
        
        print("✅ Analisi AI completata. Tento il parsing del JSON...")
        structure_data = json.loads(json_text)
        
        with open(config['output_json_structure'], "w", encoding="utf-8") as f:
            json.dump(structure_data, f, ensure_ascii=False, indent=2)
        
        print(f"🎉 File di struttura della Costituzione creato con successo in:\n{config['output_json_structure']}")
        print(f"   - Articoli totali (numerici): {structure_data.get('total_articles', 'N/D')}")
        print(f"   - Disposizioni Finali (romane): {structure_data.get('total_disposizioni_finali', 'N/D')}")
        
    except Exception as e:
        print(f"⚠️ Errore durante la creazione del file di struttura: {e}")
        if 'response' in locals():
            print(f"--- Risposta grezza ricevuta: ---\n{response.text}")

# --- 4. AVVIO ---
if __name__ == "__main__":
    app_config, app_client = load_config()
    create_structure_file(app_config, app_client)