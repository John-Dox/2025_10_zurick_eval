# c_processors/b_regcam/4_create_chunks.py

"""
PASSO 4 della pipeline di processamento per il Regolamento della Camera.

Questo script agisce come un "assemblatore". Il suo compito è unire le
diverse fonti di dati strutturati e arricchiti che abbiamo creato nei passaggi
precedenti in un unico file di "chunk" finali.

Ogni chunk rappresenta un singolo comma e contiene tutti i metadati necessari
per il filtraggio e l'arricchimento del contesto in fase di retrieval.

INPUT:
- d_outputs/03_structured/b_regcam/regcam_structure.json (generato da 00_...)
- d_outputs/03_structured/b_regcam/regcam_keywords_data.json (generato da 2_...)
- d_outputs/03_structured/b_regcam/regcam_tags_data.json (generato da 3_...)

OUTPUT:
- d_outputs/04_chunks/b_regcam/regcam_chunks.json
  Un file JSON contenente la lista completa dei chunk, pronti per la fase
  di generazione degli embedding. Ogni oggetto chunk include metadati gerarchici,
  testo, keyword e i nuovi tag semantici.
"""

import os
import sys
import json

# --- Setup del Percorso ---
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Definizione dei Percorsi ---
STRUCTURED_DIR = os.path.join(project_root, "d_outputs", "03_structured", "b_regcam")
CHUNKS_DIR = os.path.join(project_root, "d_outputs", "04_chunks", "b_regcam")

INPUT_STRUCTURE_PATH = os.path.join(STRUCTURED_DIR, "regcam_structure.json")
INPUT_KEYWORDS_PATH = os.path.join(STRUCTURED_DIR, "regcam_keywords_data.json")
INPUT_TAGS_PATH = os.path.join(STRUCTURED_DIR, "regcam_tags_data.json")
OUTPUT_CHUNKS_PATH = os.path.join(CHUNKS_DIR, "regcam_chunks.json")


def build_metadata_map(structure_data: dict) -> dict:
    """Costruisce una mappa articolo -> metadati navigando la struttura ricorsiva."""
    print("🧠 Costruzione della mappa dei metadati gerarchici...")
    metadata_map = {}
    
    doc_title = structure_data.get("document_title", "N/D")
    doc_type = structure_data.get("document_type", "N/D")

    def recursive_traverse(nodes: list, parent_path: list):
        for node in nodes:
            current_path = parent_path + [node.get("title")]
            
            if node.get("articles"):
                for article_id in node["articles"]:
                    metadata = {
                        "document_title": doc_title,
                        "document_type": doc_type,
                        "livello_1_title": current_path[0] if len(current_path) > 0 else None,
                        "livello_2_title": current_path[1] if len(current_path) > 1 else None,
                        "livello_3_title": current_path[2] if len(current_path) > 2 else None,
                    }
                    metadata_map[str(article_id)] = {k: v for k, v in metadata.items() if v is not None}

            if node.get("children"):
                recursive_traverse(node["children"], current_path)

    recursive_traverse(structure_data.get("structure", []), [])
    print(f"✅ Mappa dei metadati costruita per {len(metadata_map)} articoli.")
    return metadata_map

def build_tags_map(tags_data: list) -> dict:
    """Costruisce una mappa (articolo, comma) -> lista_di_tag."""
    print("🧠 Costruzione della mappa dei tag...")
    tags_map = {}
    for item in tags_data:
        unique_id = f"art_{item.get('articolo')}_comma_{item.get('comma')}"
        tags_map[unique_id] = item.get("tags", [])
    print(f"✅ Mappa dei tag costruita per {len(tags_map)} commi.")
    return tags_map


def main():
    """Funzione principale che orchestra il processo di creazione dei chunk."""
    print("--- PASSO 4: Inizio Assemblaggio Chunk Finali per il Regolamento ---")
    os.makedirs(CHUNKS_DIR, exist_ok=True)

    try:
        with open(INPUT_STRUCTURE_PATH, 'r', encoding='utf-8') as f:
            structure_data = json.load(f)
        with open(INPUT_KEYWORDS_PATH, 'r', encoding='utf-8') as f:
            keywords_data = json.load(f)
        with open(INPUT_TAGS_PATH, 'r', encoding='utf-8') as f:
            tags_data = json.load(f)
        print("📄 File di struttura, keyword e tag caricati con successo.")
    except FileNotFoundError as e:
        print(f"❌ ERRORE CRITICO: File di input non trovato: {e}"); sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ ERRORE CRITICO: Impossibile decodificare un file JSON: {e}"); sys.exit(1)

    # 1. Costruisci le mappe per un accesso efficiente
    metadata_map = build_metadata_map(structure_data)
    tags_map = build_tags_map(tags_data)
    
    final_chunks = []
    print("\n--- Unione dei dati in corso... ---")
    
    # 2. Itera sui dati principali (keywords_data) e arricchisci
    for record in keywords_data:
        article_id = str(record.get("articolo"))
        comma_id = str(record.get("comma", "1"))
        unique_id = f"art_{article_id}_comma_{comma_id}"
        
        # Recupera i metadati strutturali
        structural_metadata = metadata_map.get(article_id)
        if not structural_metadata:
            print(f"  -> ⚠️  WARNING: Metadati strutturali non trovati per Articolo '{article_id}'. Salto.")
            continue

        # Recupera i tag
        record_tags = tags_map.get(unique_id, []) # Default a lista vuota se non trovato
        if not record_tags:
             print(f"  -> ℹ️  INFO: Nessun tag trovato per {unique_id}.")


        # 3. Assembla l'oggetto chunk finale
        chunk = {
            **structural_metadata,
            "articolo": article_id,
            "comma": comma_id,
            "testo_originale_comma": record.get("testo_originale_comma", ""),
            "keywords": record.get("keywords", []),
            "tags": record_tags # Aggiunta del nuovo campo
        }
        
        final_chunks.append(chunk)

    # 4. Salva il risultato finale
    with open(OUTPUT_CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump(final_chunks, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 Creazione chunk completata!")
    print(f"✅ Creati {len(final_chunks)} chunk finali.")
    print(f"📁 File salvato in: {OUTPUT_CHUNKS_PATH}")


if __name__ == "__main__":
    main()