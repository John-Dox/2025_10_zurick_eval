import os
import json
import uuid
from qdrant_client import QdrantClient, models
from dotenv import load_dotenv

def load_config_and_client():
    """Carica configurazioni, percorsi e inizializza il client Qdrant."""
    proj_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    load_dotenv(os.path.join(proj_root, "a_chiavi", ".env"))
    
    embeddings_dir = os.path.join(proj_root, "d_outputs", "02_embeddings", "a_cost")
    
    config = {
        "qdrant_url": os.getenv("QDRANT_HOST"),
        "qdrant_api_key": os.getenv("QDRANT_API_KEY"),
        "qdrant_collection_name": "regcam_v11",
        "input_embeddings_file": os.path.join(embeddings_dir, "cost_embeddings.json")
    }
    
    try:
        client = QdrantClient(url=config["qdrant_url"], api_key=config["qdrant_api_key"])
        print("✅ Connessione a Qdrant riuscita.")
        return config, client
    except Exception as e:
        print(f"❌ ERRORE CRITICO durante la connessione a Qdrant: {e}")
        exit()

def ensure_collection_and_indexes(client: QdrantClient, collection_name: str):
    """
    Assicura che la collezione e gli indici necessari esistano.
    """
    if not client.collection_exists(collection_name=collection_name):
        print(f"⚠️ Collezione '{collection_name}' non trovata. La creo ora.")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE)
        )
        print(f"✅ Collezione '{collection_name}' creata con successo.")
    else:
        print(f"✅ Collezione '{collection_name}' già esistente.")

    print("\n--- Verifica e creazione degli indici sul payload ---")
    fields_to_index = [
        "document_title", "document_type", "articolo",
        "livello_1_title", "livello_2_title", "livello_3_title"
    ]
    for field in fields_to_index:
        try:
            client.create_payload_index(collection_name=collection_name, field_name=field, field_schema="keyword")
            print(f"  -> Indice per il campo '{field}' creato/verificato.")
        except Exception:
            print(f"  -> Indice per il campo '{field}' probabilmente già esistente.")

def ingest_data_to_qdrant():
    """
    Carica i dati con embedding, con controllo di idempotenza.
    """
    config, client = load_config_and_client()
    collection_name = config["qdrant_collection_name"]
    
    ensure_collection_and_indexes(client, collection_name)

    try:
        with open(config["input_embeddings_file"], 'r', encoding='utf-8') as f:
            embeddings_data = json.load(f)
        if not embeddings_data:
            print("❌ File di embedding vuoto. Nessun dato da caricare.")
            return
        print(f"\n📄 Caricati {len(embeddings_data)} record con embedding.")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌ ERRORE nel caricamento del file di embedding: {e}")
        return

    document_title_to_check = embeddings_data[0].get("document_title")
    print(f"\n--- Verifica di idempotenza per il documento: '{document_title_to_check}' ---")
    try:
        existing_points, _ = client.scroll(
            collection_name=collection_name,
            scroll_filter=models.Filter(must=[models.FieldCondition(key="document_title", match=models.MatchValue(value=document_title_to_check))]),
            limit=1, with_payload=False, with_vectors=False
        )
        if existing_points:
            print(f"✅ DATI GIÀ PRESENTI. Trovati punti per '{document_title_to_check}'. Ingest interrotto.")
            return
        print(f"ℹ️  Nessun dato trovato per '{document_title_to_check}'. Procedo con l'ingest.")
    except Exception as e:
        print(f"❌ ERRORE durante il controllo di idempotenza: {e}")
        return

    points_to_upload = [models.PointStruct(id=str(uuid.uuid4()), vector=chunk['embedding'], payload={k: v for k, v in chunk.items() if k != 'embedding'}) for chunk in embeddings_data]
    
    print(f"\n--- Inizio Ingest di {len(points_to_upload)} punti in Qdrant ---")
    try:
        client.upsert(collection_name=collection_name, points=points_to_upload, wait=True)
        print(f"✅ Ingest completato con successo.")
    except Exception as e:
        print(f"❌ ERRORE durante l'operazione di upsert: {e}")
        return

        # --- Creazione degli indici sui campi del payload ---
    print("\n--- Verifica e creazione degli indici sul payload ---")
    fields_to_index = [
        "document_title",
        "document_type",
        "articolo",
        "livello_1_title",
        "livello_2_title",
        "livello_3_title"
    ]
    
    for field in fields_to_index:
        try:
            client.create_payload_index(
                collection_name=collection_name,
                field_name=field,
                field_schema="keyword"
            )
            print(f"  -> Indice per il campo '{field}' creato/verificato.")
        except Exception:
            print(f"  -> Indice per il campo '{field}' probabilmente già esistente.")
            
    print("\n🎉 Processo di Ingest terminato.")

if __name__ == "__main__":
    ingest_data_to_qdrant()