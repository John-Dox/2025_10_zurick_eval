# b_ocr/scripts/c_gianniti_lupo/03d_inspect_entity_order.py

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
TARGET_FOLDER = "cap_1"
OCR_INPUT_DIR = os.path.join(project_root, "b_ocr", "output_json", BOOK_NAME, TARGET_FOLDER)
# --- FINE CONFIGURAZIONE ---

def inspect_entity_order():
    """
    Analizza tutti i file JSON, estrae la sequenza delle etichette ('type')
    così come appaiono nel file e la stampa per una verifica dell'ordine.
    """
    print(f"--- INIZIO ISPEZIONE ORDINE ENTITÀ in: {OCR_INPUT_DIR} ---")
    
    if not os.path.isdir(OCR_INPUT_DIR):
        print(f"ERRORE: La cartella di input non esiste: '{OCR_INPUT_DIR}'")
        return

    file_list = sorted([f for f in os.listdir(OCR_INPUT_DIR) if f.lower().endswith('.json')])

    if not file_list:
        print("ERRORE: Nessun file .json trovato nella cartella di input.")
        return

    print(f"Trovati {len(file_list)} file JSON da analizzare.\n")

    for filename in file_list:
        filepath = os.path.join(OCR_INPUT_DIR, filename)
        print(f"--- Ispeziono ordine per: {filename} ---")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            entities = data.get('entities', [])
            
            if not entities:
                print("  -> Nessuna entità trovata in questo file.")
            else:
                # Estrae la lista delle etichette nell'ordine esatto in cui appaiono
                entity_order = [entity.get('type', 'TIPO_MANCANTE') for entity in entities]
                print(f"  -> Ordine etichette nel file: {entity_order}")

            print("-" * (len(filename) + 29))

        except Exception as e:
            print(f"  - ERRORE CRITICO durante l'analisi del file: {e}")
            print("-" * (len(filename) + 29))

    print("\n✅ Ispezione dell'ordine completata.")
    print(">>> OBIETTIVO: Confrontare queste liste con l'ordine di lettura visivo delle pagine per capire se Document AI fornisce le entità in un ordine sequenziale o casuale.")


if __name__ == '__main__':
    inspect_entity_order()