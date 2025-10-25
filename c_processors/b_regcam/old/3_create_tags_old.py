# c_processors/b_regcam/3_create_tags.py

"""
PASSO 3 della pipeline di processamento per il Regolamento della Camera.

Questo script arricchisce i dati dei commi con tag semantici categorici.
Utilizza un LLM per analizzare ogni comma nel contesto del riassunto della sua sezione
e assegna una o più categorie da una lista predefinita.

INPUT:
- d_outputs/00_structured/b_regcam/regcam_keywords_data.json (generato da 2_create_keywords.py)
- d_outputs/00_structured/b_regcam/regcam_summaries.json (generato da 1_create_summaries.py)

OUTPUT:
- d_outputs/00_structured/b_regcam/regcam_tags_data.json
  Un file JSON contenente una lista di oggetti, dove ogni oggetto rappresenta un comma
  e include i dati precedenti più un nuovo campo "tags" (una lista di stringhe).
"""

import os
import sys
import json
import google.generativeai as genai
from dotenv import load_dotenv
import time
import re

# --- Setup del Percorso per l'import corretto dei moduli ---
# Questo garantisce che lo script possa essere eseguito da qualsiasi posizione
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Caricamento delle configurazioni e delle chiavi API ---
env_path = os.path.join(project_root, "a_chiavi", ".env")
load_dotenv(dotenv_path=env_path)

# --- Definizione dei Percorsi ---
INPUT_KEYWORDS_PATH = os.path.join(project_root, "d_outputs", "03_structured", "b_regcam", "regcam_keywords_data_test.json")
INPUT_SUMMARIES_PATH = os.path.join(project_root, "d_outputs", "03_structured", "b_regcam", "regcam_summaries.json")
OUTPUT_TAGS_PATH = os.path.join(project_root, "d_outputs", "03_structured", "b_regcam", "regcam_tags_data_test.json")

# --- Prompt Engineering di Precisione ---
# Definiamo una lista controllata di tag per guidare l'LLM e garantire coerenza.
TAGS_POSSIBILI = [
    "organizzazione_camera", "presidenza", "gruppi_parlamentari", "commissioni", "giunte",
    "procedure_legislative", "sedute", "discussione", "votazioni", "ordine_e_disciplina",
    "bilancio_e_finanze", "controllo_e_indirizzo", "rapporti_internazionali", "atti_normativi_gov",
    "diritti_e_doveri_deputati", "regolamento_interno", "trasparenza_e_pubblicita"
]

PROMPT_TAGS = f"""
Sei un esperto di indicizzazione giuridica e archivistica. Il tuo compito è analizzare il testo di un comma di un regolamento parlamentare e, considerando il suo contesto generale, estrarre una lista di tag categorici.

Scegli uno o più tag pertinenti dalla seguente lista predefinita:
{json.dumps(TAGS_POSSIBILI, indent=2)}

Analizza attentamente il testo fornito e il suo contesto per assegnare i tag più appropriati.

**Contesto Generale della Sezione:**
{{context_summary}}

**Testo del Comma:**
{{comma_text}}

Restituisci SOLO un array JSON di stringhe con i tag scelti. Esempio: ["sedute", "ordine_e_disciplina"]
"""

def clean_json_from_text(text: str) -> str:
    """
    Estrae una stringa JSON pulita da un blocco di testo,
    gestendo anche i markdown di codice ```json ... ```.
    """
    match = re.search(r'```json\s*(\[[\s\S]*?\])\s*```', text)
    if match:
        return match.group(1)
    
    # Fallback per JSON senza markdown
    start_index = text.find('[')
    end_index = text.rfind(']')
    if start_index != -1 and end_index != -1:
        return text[start_index:end_index + 1]
    
    return "[]" # Restituisce un array JSON vuoto in caso di fallimento

def main():
    """
    Funzione principale che orchestra il processo di generazione dei tag.
    """
    print("--- PASSO 3: Inizio Generazione Tag Semantici per il Regolamento della Camera ---")

    # Configurazione del client Gemini
    try:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel('gemini-1.5-pro-latest') # Usiamo un modello potente per questo task
    except Exception as e:
        print(f"❌ ERRORE CRITICO: Impossibile configurare il client Gemini. Verifica la chiave API. Errore: {e}")
        sys.exit(1)

    # Caricamento dei file di input
    print(f"Caricamento dati da '{os.path.basename(INPUT_KEYWORDS_PATH)}'...")
    try:
        with open(INPUT_KEYWORDS_PATH, 'r', encoding='utf-8') as f:
            keywords_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ ERRORE CRITICO: File di input non trovato: {INPUT_KEYWORDS_PATH}")
        sys.exit(1)

    print(f"Caricamento riassunti da '{os.path.basename(INPUT_SUMMARIES_PATH)}'...")
    try:
        with open(INPUT_SUMMARIES_PATH, 'r', encoding='utf-8') as f:
            summaries_data = json.load(f).get("summaries", {})
    except FileNotFoundError:
        print(f"❌ ERRORE CRITICO: File dei riassunti non trovato: {INPUT_SUMMARIES_PATH}")
        sys.exit(1)

    tags_results = []
    total_items = len(keywords_data)
    print(f"Inizio elaborazione di {total_items} commi...")

    for i, item in enumerate(keywords_data):
        # Estrazione delle informazioni necessarie
        comma_text = item.get("testo_originale_comma", "")
        parent_node_title = item.get("metadati", {}).get("livello_2_title") or item.get("metadati", {}).get("livello_1_title", "N/D")
        
        # Recupero del riassunto di contesto
        context_summary = summaries_data.get(parent_node_title, "Nessun contesto generale disponibile.")
        
        # Formattazione del prompt
        prompt = PROMPT_TAGS.format(context_summary=context_summary, comma_text=comma_text)

        # Chiamata all'LLM con gestione robusta degli errori
        try:
            response = model.generate_content(prompt)
            cleaned_json_str = clean_json_from_text(response.text)
            
            # Parsing del JSON con gestione robusta degli errori
            try:
                tags = json.loads(cleaned_json_str)
                if not isinstance(tags, list): # Ulteriore controllo di validità
                    print(f"⚠️  WARNING: L'LLM non ha restituito una lista per il comma dell'articolo {item.get('articolo')}. Assegno una lista vuota.")
                    tags = []
            except json.JSONDecodeError:
                print(f"⚠️  WARNING: Errore di parsing JSON per il comma dell'articolo {item.get('articolo')}. Assegno una lista vuota.")
                tags = []

        except Exception as e:
            print(f"⚠️  WARNING: Errore API per il comma dell'articolo {item.get('articolo')}. Assegno una lista vuota. Errore: {e}")
            tags = []
            time.sleep(2) # Pausa in caso di errori API per evitare di sovraccaricare il servizio

        # Aggiunta del nuovo campo 'tags' all'oggetto originale
        item['tags'] = tags
        tags_results.append(item)

        # Log di avanzamento
        if (i + 1) % 20 == 0 or (i + 1) == total_items:
            print(f"   ... Elaborati {i + 1}/{total_items} commi.")

    # Salvataggio del file di output
    print(f"Salvataggio dei dati arricchiti con i tag in '{os.path.basename(OUTPUT_TAGS_PATH)}'...")
    os.makedirs(os.path.dirname(OUTPUT_TAGS_PATH), exist_ok=True)
    with open(OUTPUT_TAGS_PATH, 'w', encoding='utf-8') as f:
        json.dump(tags_results, f, indent=2, ensure_ascii=False)

    print("✅ --- PASSO 3: Generazione Tag Semantici completata con successo. ---")


if __name__ == "__main__":
    main()