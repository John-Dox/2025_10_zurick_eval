# b_ocr/scripts/c_gianniti_lupo/03c_list_actual_labels.py

import os
import sys
import json
from collections import Counter

# --- CONFIGURAZIONE E SETUP PERCORSI ---
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
# --- FINE CONFIGURAZIONE ---

def find_all_unique_labels():
    """
    Scansiona tutti i file JSON, estrae tutte le etichette ('type') delle entità
    e stampa un elenco unico e un conteggio di ciascuna.
    """
    print(f"--- Inizio Scansione Etichette Reali in: {OCR_INPUT_DIR} ---")
    
    if not os.path.isdir(OCR_INPUT_DIR):
        print(f"ERRORE: La cartella di input non esiste: '{OCR_INPUT_DIR}'")
        return

    all_labels_found = []
    file_list = [f for f in os.listdir(OCR_INPUT_DIR) if f.lower().endswith('.json')]

    if not file_list:
        print("ERRORE: Nessun file JSON trovato nella cartella di input.")
        return

    print(f"Trovati {len(file_list)} file JSON da analizzare...")
    for filename in file_list:
        filepath = os.path.join(OCR_INPUT_DIR, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Cerca le entità al primo livello (come confermato dalla diagnostica precedente)
                entities = data.get('entities', [])
                for entity in entities:
                    label = entity.get('type')
                    if label:
                        all_labels_found.append(label)
        except Exception as e:
            print(f"AVVISO: Impossibile processare il file {filename}. Errore: {e}")

    if not all_labels_found:
        print("\n--- RISULTATO SCANSIONE ---")
        print("❌ NESSUNA ETICHETTA TROVATA in nessun file.")
        print("Questo indica un problema grave nel processo OCR o nella versione del processore utilizzata.")
        return
        
    # Conta le occorrenze di ciascuna etichetta
    label_counts = Counter(all_labels_found)
    unique_labels = sorted(label_counts.keys())

    print("\n--- RISULTATO SCANSIONE ETICHETTE ---")
    print("Elenco delle etichette UNICHE realmente presenti nei file JSON:")
    print("Questo elenco è la nostra 'fonte di verità'.")
    
    # Stampa in un formato facile da copiare e incollare
    print("\nELENCO DA COPIARE:")
    print("--------------------")
    print("{")
    for label in unique_labels:
        print(f'    "{label}",')
    print("}")
    print("--------------------")

    print("\nCONTEGGIO DETTAGLIATO (per diagnostica):")
    for label, count in label_counts.items():
        print(f"  - '{label}': trovata {count} volte")

    print("\n✅ Scansione completata.")

if __name__ == '__main__':
    find_all_unique_labels()