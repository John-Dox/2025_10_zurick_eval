import os
import json
import uuid
from qdrant_client import QdrantClient, models
from dotenv import load_dotenv

# --- 1. CONFIGURAZIONE ---
def load_config_and_client():
    """Carica configurazioni, percorsi e inizializza il client Qdrant."""
    proj_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    load_dotenv(os.path.join(proj_root, "a_chiavi", ".env"))
    
    embeddings_dir = os.path.join(proj_root, "d_outputs", "02_embeddings", "a_cost")
    
    config = {
        "qdrant_url": os.getenv("QDRANT_HOST"), # Uso QDRANT_HOST per coerenza con .env
        "qdrant_api_key": os.getenv("QDRANT_API_KEY"),
        "qdrant_collection_name": "regcam_v11",
        "input_embeddings_file": os.path.join(embeddings_dir, "cost_embeddings.json")
    }
    
    try:
        client = QdrantClient(url=config["qdrant_url"], api_key=config["qdrant_api_key"])
            
        collection_name = config["qdrant_collection_name"]
        if not client.collection_exists(collection_name=collection_name):
            # Se non esiste, la crea
            print(f"⚠️ Collezione '{collection_name}' non trovata. La creo ora.")
            client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE)
            )
            print(f"✅ Collezione '{collection_name}' creata con successo.")
        else:
            print(f"✅ Collezione '{collection_name}' già esistente. Procedo.")

        
        print(f"✅ Connessione a Qdrant riuscita.")
        return config, client
    except Exception as e:
        print(f"❌ ERRORE CRITICO durante la gestione della collezione: {e}")
        exit()

# --- 2. LOGICA DI INGEST ---

def ingest_data_to_qdrant():
    """
    Carica i dati con embedding dal file JSON alla collezione Qdrant esistente.
    """
    config, client = load_config_and_client()

    try:
        with open(config["input_embeddings_file"], 'r', encoding='utf-8') as f:
            embeddings_data = json.load(f)
        print(f"📄 Caricati {len(embeddings_data)} record con embedding da: {os.path.basename(config['input_embeddings_file'])}")
    except FileNotFoundError:
        print(f"❌ ERRORE: File di embedding non trovato: {config['input_embeddings_file']}")
        return
    except json.JSONDecodeError:
        print(f"❌ ERRORE: Impossibile decodificare il JSON dal file di embedding.")
        return

    points_to_upload = []
    for chunk in embeddings_data:
        payload = {key: value for key, value in chunk.items() if key != 'embedding'}
        point = models.PointStruct(
            id=str(uuid.uuid4()),
            vector=chunk['embedding'],
            payload=payload
        )
        points_to_upload.append(point)

    print(f"\n--- Inizio Ingest di {len(points_to_upload)} punti in Qdrant ---")
    try:
        client.upsert(
            collection_name=config["qdrant_collection_name"],
            points=points_to_upload,
            wait=True
        )
        print(f"✅ Ingest completato con successo.")
    except Exception as e:
        print(f"❌ ERRORE durante l'operazione di upsert su Qdrant: {e}")
        return

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
                collection_name=config["qdrant_collection_name"],
                field_name=field,
                field_schema="keyword"
            )
            print(f"  -> Indice per il campo '{field}' creato/verificato.")
        except Exception:
            # Questo errore è atteso se l'indice esiste già. Lo gestiamo come un successo.
            print(f"  -> Indice per il campo '{field}' probabilmente già esistente.")
            
    print("\n🎉 Processo di Ingest terminato.")


# --- 3. AVVIO ---
if __name__ == "__main__":
    ingest_data_to_qdrant()