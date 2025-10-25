# c_processors/b_regcam/3_create_tags.py

"""
PASSO 3 della pipeline di processamento per il Regolamento della Camera.

Questo script arricchisce i dati dei commi con tag semantici categorici.
Utilizza la logica di ripristino "elegante" (ispirata da 2_create_keywords.py),
lavorando con un file di progresso separato per garantire robustezza,
efficienza e il mantenimento dell'ordine originale dei dati.

Logica di Robustezza Implementata:
- Usa un file `_progress.json` per salvare i risultati intermedi.
- All'avvio, carica i progressi e salta gli articoli già completati.
- Salva i dati dopo aver processato tutti i commi di un intero articolo.
- Se il processo si completa, rinomina il file di progresso in quello finale.
- Mantiene un "Circuit Breaker" per interrompersi dopo errori API consecutivi.

INPUT:
- d_outputs/03_structured/b_regcam/regcam_keywords_data.json
- d_outputs/03_structured/b_regcam/regcam_summaries.json

OUTPUT:
- d_outputs/03_structured/b_regcam/regcam_tags_data.json
"""

import os
import sys
import json
import google.generativeai as genai
from dotenv import load_dotenv
import time
import re
from collections import defaultdict

# --- Setup del Percorso ---
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Caricamento Configurazione ---
env_path = os.path.join(project_root, "a_chiavi", ".env")
load_dotenv(dotenv_path=env_path)

# --- Definizione dei Percorsi ---
STRUCTURED_DIR = os.path.join(project_root, "d_outputs", "03_structured", "b_regcam")
INPUT_KEYWORDS_PATH = os.path.join(STRUCTURED_DIR, "regcam_keywords_data.json")
INPUT_SUMMARIES_PATH = os.path.join(STRUCTURED_DIR, "regcam_summaries.json")
OUTPUT_PROGRESS_PATH = os.path.join(STRUCTURED_DIR, "regcam_tags_progress.json")
OUTPUT_FINAL_PATH = os.path.join(STRUCTURED_DIR, "regcam_tags_data.json")

# --- Costanti ---
CONSECUTIVE_ERROR_LIMIT = 5

# --- Prompt Engineering ---
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
    match = re.search(r'```json\s*(\[[\s\S]*?\])\s*```', text)
    if match: return match.group(1)
    start_index = text.find('[')
    end_index = text.rfind(']')
    if start_index != -1 and end_index != -1:
        return text[start_index:end_index + 1]
    return "[]"

def main():
    print("--- PASSO 3 (Logica Elegante): Inizio Generazione Tag Semantici ---")

    try:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel('gemini-2.5-flash')
    except Exception as e:
        print(f"❌ ERRORE CRITICO: Configurazione Gemini fallita. Errore: {e}"); sys.exit(1)

    try:
        with open(INPUT_KEYWORDS_PATH, 'r', encoding='utf-8') as f:
            keywords_data = json.load(f)
        with open(INPUT_SUMMARIES_PATH, 'r', encoding='utf-8') as f:
            summaries_data = json.load(f).get("summaries", {})
    except FileNotFoundError as e:
        print(f"❌ ERRORE CRITICO: File di input non trovato: {e}"); sys.exit(1)

    commi_per_articolo = defaultdict(list)
    for comma in keywords_data:
        commi_per_articolo[comma.get("articolo")].append(comma)
    
    all_articles_ids = list(commi_per_articolo.keys())

    enriched_data = []
    processed_articles = set()
    if os.path.exists(OUTPUT_PROGRESS_PATH):
        print(f"ℹ️  Trovato file di progresso. Caricamento...")
        with open(OUTPUT_PROGRESS_PATH, 'r', encoding='utf-8') as f:
            try:
                enriched_data = json.load(f)
                processed_articles = {record['articolo'] for record in enriched_data}
                print(f"✅  Recuperati {len(processed_articles)} articoli già elaborati.")
            except json.JSONDecodeError:
                print("⚠️  WARNING: File di progresso corrotto. Ripartenza da zero.")
    
    articles_to_process_ids = [aid for aid in all_articles_ids if aid not in processed_articles]

    if not articles_to_process_ids:
        print("🎉 Tutti gli articoli sono già stati processati.")
        # Se il file finale non esiste, rinominiamo quello di progresso
        if not os.path.exists(OUTPUT_FINAL_PATH) and os.path.exists(OUTPUT_PROGRESS_PATH):
             os.rename(OUTPUT_PROGRESS_PATH, OUTPUT_FINAL_PATH)
        return
        
    print(f"\nInizio elaborazione di {len(articles_to_process_ids)} articoli rimanenti...")
    consecutive_errors = 0

    for i, article_id in enumerate(articles_to_process_ids):
        print(f"  -> Processo Articolo {article_id} ({i+1}/{len(articles_to_process_ids)})")
        temp_article_chunks = []
        
        commi_da_processare = commi_per_articolo[article_id]
        
        error_in_article = False
        for comma_item in commi_da_processare:
            comma_text = comma_item.get("testo_originale_comma", "")
            parent_node_title = comma_item.get("metadati", {}).get("livello_2_title") or comma_item.get("metadati", {}).get("livello_1_title", "N/D")
            context_summary = summaries_data.get(parent_node_title, "Nessun contesto generale disponibile.")
            prompt = PROMPT_TAGS.format(context_summary=context_summary, comma_text=comma_text)

            tags = []
            try:
                response = model.generate_content(prompt)
                if not response.candidates or not response.candidates[0].content.parts:
                    raise ValueError(f"Risposta API vuota. Finish Reason: {response.candidates[0].finish_reason.name if response.candidates else 'N/A'}")
                
                cleaned_json_str = clean_json_from_text(response.text)
                tags = json.loads(cleaned_json_str)
                if not isinstance(tags, list): 
                    print(f"     ⚠️  WARNING Comma {comma_item.get('comma')}: L'LLM non ha restituito una lista. Assegno lista vuota.")
                    tags = []

                consecutive_errors = 0 # Successo: azzera il contatore
            except Exception as e:
                print(f"     ❌ ERRORE Comma {comma_item.get('comma')}: {e}")
                consecutive_errors += 1
                error_in_article = True
                if consecutive_errors >= CONSECUTIVE_ERROR_LIMIT:
                    break
                time.sleep(2)
                continue

            comma_item['tags'] = tags
            temp_article_chunks.append(comma_item)
            print(f"     - Comma {comma_item.get('comma')} processato.")
            time.sleep(1.5)
        
        if consecutive_errors >= CONSECUTIVE_ERROR_LIMIT or error_in_article:
            print(f"   ⚠️  Errore durante l'elaborazione dell'articolo {article_id}. Il progresso per questo articolo non verrà salvato.")
            if consecutive_errors >= CONSECUTIVE_ERROR_LIMIT:
                break
            else:
                continue

        enriched_data.extend(temp_article_chunks)
        with open(OUTPUT_PROGRESS_PATH, 'w', encoding='utf-8') as f:
            json.dump(enriched_data, f, indent=2, ensure_ascii=False)
        print(f"     ✅ Progresso per Art. {article_id} salvato.")

    if consecutive_errors < CONSECUTIVE_ERROR_LIMIT:
        print("\n🎉 Arricchimento completato!")
        if os.path.exists(OUTPUT_PROGRESS_PATH):
            os.rename(OUTPUT_PROGRESS_PATH, OUTPUT_FINAL_PATH)
            print(f"✅ Creati {len(enriched_data)} record con tag.")
            print(f"📁 File finale salvato in: {OUTPUT_FINAL_PATH}")
    else:
        print("\n⚠️  Processo interrotto a causa di errori. I progressi parziali sono salvati in: " + OUTPUT_PROGRESS_PATH)

if __name__ == "__main__":
    main()