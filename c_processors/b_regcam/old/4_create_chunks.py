import os
import json

# --- 1. CONFIGURAZIONE DEI PERCORSI ---
def load_paths():
    """Definisce i percorsi per la creazione dei chunk del Regolamento."""
    proj_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    structured_dir = os.path.join(proj_root, "d_outputs", "00_structured", "b_regcam")
    chunks_dir = os.path.join(proj_root, "d_outputs", "01_chunks", "b_regcam")
    
    os.makedirs(chunks_dir, exist_ok=True)
    
    paths = {
        "structure": os.path.join(structured_dir, "regcam_structure.json"),
        "keywords_data": os.path.join(structured_dir, "regcam_keywords_data.json"),
        "final_chunks": os.path.join(chunks_dir, "regcam_chunks.json")
    }
    print("✅ Percorsi di input e output configurati.")
    return paths

# --- 2. LOGICA PRINCIPALE ---

def build_metadata_map(structure_data: dict) -> dict:
    """Costruisce una mappa articolo -> metadati navigando la struttura ricorsiva."""
    print("🧠 Costruzione della mappa dei metadati dalla struttura ricorsiva...")
    metadata_map = {}
    
    doc_title = structure_data.get("document_title", "N/D")
    doc_type = structure_data.get("document_type", "N/D")

    def recursive_traverse(nodes: list, parent_path: list):
        """Funzione di aiuto ricorsiva per navigare l'albero dei nodi."""
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
                    metadata_map[article_id] = {k: v for k, v in metadata.items() if v is not None}

            if node.get("children"):
                recursive_traverse(node["children"], current_path)

    recursive_traverse(structure_data.get("structure", []), [])
    print(f"✅ Mappa dei metadati costruita per {len(metadata_map)} articoli/disposizioni.")
    return metadata_map


def create_final_chunks():
    """Unisce i dati strutturali e i dati con keyword per creare i chunk finali."""
    paths = load_paths()

    try:
        with open(paths["structure"], 'r', encoding='utf-8') as f:
            structure_data = json.load(f)
        with open(paths["keywords_data"], 'r', encoding='utf-8') as f:
            keywords_data = json.load(f)
        print("📄 File di struttura e dati keyword caricati.")
    except FileNotFoundError as e:
        print(f"❌ ERRORE: File di input non trovato: {e}")
        return
    except json.JSONDecodeError as e:
        print(f"❌ ERRORE: Impossibile decodificare il JSON da un file di input: {e}")
        return

    metadata_map = build_metadata_map(structure_data)
    final_chunks = []

    print("\n--- Inizio Processo di Creazione Chunk Finali ---")
    for record in keywords_data:
        article_id = record.get("articolo")
        
        if article_id not in metadata_map:
            print(f"  -> Avviso: Articolo '{article_id}' trovato nei dati arricchiti ma non nella mappa. Verrà saltato.")
            continue

        structural_metadata = metadata_map[article_id]

        chunk = {
            **structural_metadata,
            "articolo": article_id,
            "comma": record.get("comma", "1"),
            "testo_originale_comma": record.get("testo_originale_comma", ""),
            "keywords": record.get("keywords", [])
        }
        
        final_chunks.append(chunk)

    with open(paths["final_chunks"], "w", encoding="utf-8") as f:
        json.dump(final_chunks, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 Creazione chunk completata!")
    print(f"✅ Creati {len(final_chunks)} chunk finali.")
    print(f"📁 File salvato in: {paths['final_chunks']}")


# --- 3. AVVIO ---
if __name__ == "__main__":
    create_final_chunks()