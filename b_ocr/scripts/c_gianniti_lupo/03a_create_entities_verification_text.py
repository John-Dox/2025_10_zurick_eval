# b_ocr/scripts/c_gianniti_lupo/03a_create_entities_verification_text.py

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
VERIFICATION_OUTPUT_DIR = os.path.join(project_root, "d_outputs", "01_ocr_structured", BOOK_NAME, TARGET_FOLDER)
OUTPUT_FILENAME = "entities_verification_text.txt"

# --- DEFINIZIONE DELLO SCHEMA DI ETICHETTE DA ESTRARRE (BASATO SULLA DIAGNOSTICA) ---
# Questo elenco è basato sull'output reale dello script 03c_list_actual_labels.py
# e contiene solo le etichette che rappresentano blocchi di testo leggibile.
TEXT_ENTITY_LABELS = {
    "box_numero",
    "box_testo",
    "box_titolo",
    "capitolo_abstract",
    "note_testo",
    "pagina_numero",
    "paragrafo_titolo",
    "text_regular",
}
# Le etichette puramente numeriche (es. 'pagina_numero', 'box_num') sono escluse.
# --- FINE CONFIGURAZIONE ---

def get_entity_sort_key(entity: dict):
    """
    Restituisce una chiave di ordinamento (y, x) per un'entità basata
    sulla coordinata del suo primo vertice.
    """
    try:
        # La chiave corretta è 'pageAnchor'
        page_anchor = entity.get('pageAnchor', {})
        page_refs = page_anchor.get('pageRefs', [{}])
        bounding_poly = page_refs[0].get('boundingPoly', {})
        vertices = bounding_poly.get('normalizedVertices', [])
        
        if not vertices: 
            return (float('inf'), float('inf'))
        
        y_coord = vertices[0].get('y', float('inf'))
        x_coord = vertices[0].get('x', float('inf'))
        return (y_coord, x_coord)
    except (IndexError, TypeError, KeyError):
        return (float('inf'), float('inf'))

def create_entities_verification_file():
    print(f"--- Inizio Estrazione TESTO DA ENTITÀ per '{BOOK_NAME}/{TARGET_FOLDER}' ---")
    
    if not os.path.isdir(OCR_INPUT_DIR):
        print(f"ERRORE: La cartella di input '{OCR_INPUT_DIR}' non è stata trovata."); return

    final_output_content = []
    file_list = sorted([f for f in os.listdir(OCR_INPUT_DIR) if f.endswith('.json')])

    if not file_list:
        print(f"AVVISO: Nessun file JSON trovato in '{OCR_INPUT_DIR}'."); return

    for filename in file_list:
        filepath = os.path.join(OCR_INPUT_DIR, filename)
        final_output_content.append(f"--- INIZIO PAGINA: {filename} ---\n")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f: data = json.load(f)
            
            # PASSO 1: Estrarre la lista 'entities' dal primo livello, come confermato dalla diagnostica.
            entities_in_document = data.get('entities', [])
            
            if not entities_in_document:
                final_output_content.append(f"\n--- FINE PAGINA: {filename} ---\n\n")
                continue

            # PASSO 2: Filtrare le entità che ci interessano.
            text_entities = [entity for entity in entities_in_document if entity.get('type') in TEXT_ENTITY_LABELS]
            
            if not text_entities:
                final_output_content.append(f"\n--- FINE PAGINA: {filename} ---\n\n")
                continue

            # PASSO 3: Ordinare le entità trovate per posizione.
            sorted_entities = sorted(text_entities, key=get_entity_sort_key)
            
            # PASSO 4: Estrarre il testo (mentionText) da ogni entità valida.
            page_text_parts = []
            for entity in sorted_entities:
                mention_text = entity.get('mentionText', '').strip()
                if mention_text:
                    # Sostituisce i newline con spazi per evitare rotture di riga indesiderate
                    cleaned_text = mention_text.replace('\n', ' ')
                    page_text_parts.append(cleaned_text)

            # PASSO 5: Unire le parti di testo di questa pagina.
            if page_text_parts:
                final_output_content.append("\n\n".join(page_text_parts))

        except Exception as e:
            print(f"AVVISO: Impossibile processare il file {filename}. Errore: {e}")
        
        final_output_content.append(f"\n--- FINE PAGINA: {filename} ---\n\n")

    full_verification_text = "".join(final_output_content)
    
    os.makedirs(VERIFICATION_OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(VERIFICATION_OUTPUT_DIR, OUTPUT_FILENAME)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(full_verification_text)
        
    print(f"\n--- Processo completato con successo! ---")
    print(f"File di testo delle entità salvato in: {output_path}")

if __name__ == '__main__':
    create_entities_verification_file()