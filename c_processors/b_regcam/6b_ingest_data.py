# c_processors/b_regcam/6b_ingest_data.py

"""
PASSO 6b (FINALE) della pipeline di processamento per il Regolamento della Camera.

Questo script prende i dati finali, completi di metadati, testo, keyword, tag
e vettori di embedding, e li carica (ingerisce) nel database vettoriale Qdrant.

Questo è l'ultimo passo della pipeline di elaborazione dati. Una volta completato,
i dati del documento sono pronti per essere interrogati dal sistema RAG.

Logica di Robustezza Implementata:
- Assicura che la collezione in Qdrant esista prima di procedere.
- Crea in modo esplicito gli indici di payload necessari (incluso quello per i
  nuovi 'tags') per garantire query filtrate efficienti.
- Implementa un controllo di idempotenza per prevenire il caricamento di dati
  duplicati per un documento già presente nella collezione.

INPUT:
- d_outputs/05_embeddings/b_regcam/regcam_embeddings.json

OUTPUT:
- Dati caricati nella collezione Qdrant specificata.
"""

import os
import sys
import json
import uuid
from qdrant_client import QdrantClient, models
from dotenv import load_dotenv

# --- Setup del Percorso ---
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Caricamento Configurazione ---
env_path = os.path.join(project_root, "a_chiavi", ".env")
load_dotenv(dotenv_path=env_path)

# --- Definizione dei Percorsi e della Configurazione ---
EMBEDDINGS_DIR = os.path.join(project_root, "d_outputs", "05_embeddings", "b_regcam")
INPUT_EMBEDDINGS_PATH = os.path.join(EMBEDDINGS_DIR, "regcam_embeddings.json")
QDRANT_URL = os.getenv("QDRANT_HOST")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_COLLECTION_NAME = "regcam_v11"


def ensure_collection_and_indexes(client: QdrantClient, collection_name: str):
    """Assicura che la collezione e gli indici necessari esistano in Qdrant."""
    try:
        collections = client.get_collections()
        collection_names = [c.name for c in collections.collections]
        if collection_name not in collection_names:
            print(f"⚠️ Collezione '{collection_name}' non trovata. La creo ora.")
            client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE)
            )
            print(f"✅ Collezione '{collection_name}' creata con successo.")
        else:
            print(f"✅ Collezione '{collection_name}' già esistente.")
    except Exception as e:
        print(f"❌ ERRORE durante la verifica/creazione della collezione: {e}"); sys.exit(1)

    print("\n--- Verifica e creazione degli indici sul payload ---")
    
    fields_to_index = [
        "document_title", "document_type", "articolo",
        "livello_1_title", "livello_2_title", "livello_3_title",
        "tags" 
    ]
    
    for field in fields_to_index:
        try:
            client.create_payload_index(collection_name=collection_name, field_name=field, field_schema="keyword")
            print(f"  -> Indice per il campo '{field}' creato/verificato.")
        except Exception:
            print(f"  -> Indice per il campo '{field}' probabilmente già esistente.")

def main():
    """Funzione principale che orchestra il processo di ingest in Qdrant."""
    print(f"--- PASSO 6b: Inizio Ingest Dati per il Regolamento in Qdrant ---")

    try:
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        print("✅ Connessione a Qdrant riuscita.")
    except Exception as e:
        print(f"❌ ERRORE CRITICO durante la connessione a Qdrant: {e}"); sys.exit(1)

    ensure_collection_and_indexes(client, QDRANT_COLLECTION_NAME)

    try:
        with open(INPUT_EMBEDDINGS_PATH, 'r', encoding='utf-8') as f:
            embeddings_data = json.load(f)
        if not embeddings_data:
            print("❌ File di embedding vuoto. Nessun dato da caricare."); return
        print(f"\n📄 Caricati {len(embeddings_data)} record con embedding dal file di input.")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌ ERRORE nel caricamento del file di embedding: {e}"); return

    document_title_to_check = embeddings_data[0].get("document_title")
    print(f"\n--- Verifica di idempotenza per il documento: '{document_title_to_check}' ---")
    try:
        existing_points, _ = client.scroll(
            collection_name=QDRANT_COLLECTION_NAME,
            scroll_filter=models.Filter(must=[models.FieldCondition(key="document_title", match=models.MatchValue(value=document_title_to_check))]),
            limit=1, with_payload=False, with_vectors=False
        )
        if existing_points:
            print(f"✅ DATI GIÀ PRESENTI. Trovati punti per '{document_title_to_check}'. Ingest interrotto per evitare duplicati.")
            return
        print(f"ℹ️  Nessun dato trovato per '{document_title_to_check}'. Procedo con l'ingest.")
    except Exception as e:
        print(f"❌ ERRORE durante il controllo di idempotenza: {e}"); return
    
    points_to_upload = []
    for chunk in embeddings_data:
        payload = {k: v for k, v in chunk.items() if k != 'embedding'}
        point = models.PointStruct(
            id=str(uuid.uuid4()),
            vector=chunk['embedding'],
            payload=payload
        )
        points_to_upload.append(point)
    
    print(f"\n--- Inizio Ingest di {len(points_to_upload)} punti in Qdrant ---")
    try:
        client.upsert(collection_name=QDRANT_COLLECTION_NAME, points=points_to_upload, wait=True)
        print(f"✅ Ingest completato con successo.")
    except Exception as e:
        print(f"❌ ERRORE durante l'operazione di upsert: {e}"); return
            
    print("\n🎉 Processo di Ingest terminato.")

if __name__ == "__main__":
    main()