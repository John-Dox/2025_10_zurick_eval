# b_ocr/scripts/c_gianniti_lupo/04_create_structured_text.py

import os
import sys
import json

# --- CONFIGURAZIONE ---
try:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    if project_root not in sys.path:
        sys.path.append(project_root)
except Exception as e:
    print(f"ERRORE di configurazione percorsi: {e}")
    exit()

BOOK_NAME = "c_gianniti_lupo"
TARGET_FOLDER = "cap_9"
OCR_INPUT_DIR = os.path.join(project_root, "b_ocr", "output_json", BOOK_NAME, TARGET_FOLDER)
# Nuova cartella di output per i file JSON strutturati e ordinati
STRUCTURED_OUTPUT_DIR = os.path.join(project_root, "d_outputs", "02_structured_pages", BOOK_NAME, TARGET_FOLDER)
# --- FINE CONFIGURAZIONE ---

def process_single_json_file(input_filepath: str, output_filepath: str):
    """
    Legge un file JSON di Document AI, ordina le entità in base al loro
    startIndex e salva un nuovo JSON semplificato e ordinato.
    """
    try:
        with open(input_filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        entities = data.get('entities', [])
        if not entities:
            print(f"  - AVVISO: Nessuna entità trovata in {os.path.basename(input_filepath)}. Il file di output sarà vuoto.")
            with open(output_filepath, 'w', encoding='utf-8') as f:
                json.dump([], f)
            return

        logical_blocks = []
        for entity in entities:
            # Estraiamo le informazioni essenziali, in particolare lo startIndex
            entity_type = entity.get('type')
            mention_text = entity.get('mentionText')
            
            text_anchor = entity.get('textAnchor', {})
            text_segments = text_anchor.get('textSegments', [{}])
            start_index = int(text_segments[0].get('startIndex', -1))

            if entity_type and mention_text is not None and start_index != -1:
                logical_blocks.append({
                    "type": entity_type,
                    "text": mention_text.strip(),
                    "startIndex": start_index
                })

        # --- IL PASSAGGIO CHIAVE: ORDINAMENTO DETERMINISTICO ---
        # Ordiniamo i blocchi in base alla loro posizione nel testo grezzo.
        sorted_blocks = sorted(logical_blocks, key=lambda b: b['startIndex'])

        # Rimuoviamo lo startIndex dall'output finale, poiché l'ordine è ora implicito.
        final_structure = [
            {"type": block["type"], "text": block["text"]}
            for block in sorted_blocks
        ]

        with open(output_filepath, 'w', encoding='utf-8') as f:
            json.dump(final_structure, f, indent=4, ensure_ascii=False)
        
        print(f"  - Creato file strutturato e ordinato per {os.path.basename(input_filepath)}")

    except Exception as e:
        print(f"  - ❌ ERRORE CRITICO durante il processamento di {os.path.basename(input_filepath)}: {e}")


def main():
    """
    Orchestra il processo di conversione per tutti i file JSON in una directory.
    """
    print(f"--- Inizio Creazione JSON Strutturati e Ordinati per '{BOOK_NAME}/{TARGET_FOLDER}' ---")
    
    if not os.path.isdir(OCR_INPUT_DIR):
        print(f"ERRORE: La cartella di input '{OCR_INPUT_DIR}' non è stata trovata."); return

    os.makedirs(STRUCTURED_OUTPUT_DIR, exist_ok=True)
    file_list = sorted([f for f in os.listdir(OCR_INPUT_DIR) if f.endswith('.json')])

    if not file_list:
        print(f"AVVISO: Nessun file JSON trovato in '{OCR_INPUT_DIR}'."); return

    print(f"Trovati {len(file_list)} file JSON da processare...")
    for filename in file_list:
        input_path = os.path.join(OCR_INPUT_DIR, filename)
        output_path = os.path.join(STRUCTURED_OUTPUT_DIR, filename) # Mantiene lo stesso nome
        process_single_json_file(input_path, output_path)

    print(f"\n--- Processo completato! ---")
    print(f"I file JSON strutturati sono stati salvati in: {STRUCTURED_OUTPUT_DIR}")


if __name__ == '__main__':
    main()