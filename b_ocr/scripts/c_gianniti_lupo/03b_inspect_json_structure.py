# b_ocr/scripts/c_gianniti_lupo/03b_inspect_json_structure.py

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
# --- FINE CONFIGURAZIONE ---

def print_json_structure(data, indent=""):
    """
    Funzione ricorsiva per stampare la struttura gerarchica (l'albero) di un oggetto JSON.
    """
    if isinstance(data, dict):
        for key, value in data.items():
            highlight = ""
            if key in ['entities', 'text']:
                highlight = f"  <-- CHIAVE DI INTERESSE"
            
            if isinstance(value, dict):
                print(f"{indent} L- '{key}': (Oggetto dict){highlight}")
                # Entriamo in ricorsione solo se è la prima volta, per non essere troppo verbosi
                if indent == "": print_json_structure(value, indent + "    ")
            elif isinstance(value, list):
                print(f"{indent} L- '{key}': (Lista di {len(value)} elementi){highlight}")
                if value and indent == "": # Analizza il primo elemento della lista solo al primo livello
                    print_json_structure(value[0], indent + "    ")
            else:
                pass # Non stampiamo i valori finali per brevità
    elif isinstance(data, list):
        if data:
            print_json_structure(data[0], indent)


def inspect_all_json_files():
    """
    Analizza TUTTI i file JSON in una directory e ne stampa un riepilogo strutturale.
    """
    print(f"--- INIZIO ISPEZIONE STRUTTURALE di tutti i file in: {OCR_INPUT_DIR} ---")
    
    if not os.path.isdir(OCR_INPUT_DIR):
        print(f"ERRORE: La cartella di input non esiste: '{OCR_INPUT_DIR}'")
        return

    file_list = sorted([f for f in os.listdir(OCR_INPUT_DIR) if f.lower().endswith('.json')])

    if not file_list:
        print("ERRORE: Nessun file .json trovato nella cartella di input.")
        return

    print(f"Trovati {len(file_list)} file JSON da analizzare.\n")
    
    # --- CORREZIONE: Rimosso il limitatore per analizzare TUTTI i file ---
    for filename in file_list:
        filepath = os.path.join(OCR_INPUT_DIR, filename)
        print(f"--- Ispeziono: {filename} ---")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Analisi della struttura per ogni file
            entities = data.get('entities')
            text_content = data.get('text')
            
            # Stampa un riepilogo conciso per ogni file
            if entities is not None and isinstance(entities, list) and len(entities) > 0:
                print(f"  [✅] Trovata chiave 'entities' al primo livello con {len(entities)} elementi.")
            else:
                print(f"  [❌] Chiave 'entities' non trovata o vuota al primo livello.")

            if text_content is not None and isinstance(text_content, str) and len(text_content) > 0:
                print(f"  [✅] Trovata chiave 'text' al primo livello con {len(text_content)} caratteri.")
            else:
                print(f"  [❌] Chiave 'text' non trovata o vuota.")
                
            print("-" * (len(filename) + 16))

        except Exception as e:
            print(f"  - ERRORE CRITICO durante l'analisi del file: {e}")
            print("-" * (len(filename) + 16))

    print("\n✅ Ispezione di tutti i file completata.")
    print(">>> OBIETTIVO: Confermare che TUTTI i file hanno una chiave 'entities' al primo livello.")

if __name__ == '__main__':
    inspect_all_json_files()