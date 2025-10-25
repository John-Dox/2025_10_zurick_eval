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
    
    output_embeddings_dir = os.path.join(proj_root, "d_outputs", "02_embeddings", "a_cost")
    
    config = {
        "qdrant_host": os.getenv("QDRANT_HOST"),
        "qdrant_api_key": os.getenv("QDRANT_API_KEY"),
        "qdrant_collection_name": "regcam_v11",  # Usiamo la collezione esistente
        "input_embeddings_file": os.path.join(output_embeddings_dir, "cost_embeddings.json")
    }
    
    try:
        client = QdrantClient(url=config["qdrant_host"], api_key=config["qdrant_api_key"])
        print(f"✅ Connessione a Qdrant riuscita. Collezione target: '{config['qdrant_collection_name']}'")
        return config, client
    except Exception as e:
        print(f"❌ ERRORE CRITICO durante la connessione a Qdrant: {e}")
        exit()

# --- 2. LOGICA DI INGEST ---

def ingest_data_to_qdrant():
    """
    Carica i dati con embedding dal file JSON alla collezione Qdrant specificata.
    """
    config, client = load_config_and_client()

    # Carica i dati con embedding
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

    # Prepara i punti per l'upsert
    points_to_upload = []
    for chunk in embeddings_data:
        # Il payload contiene tutti i metadati utili per il filtraggio e la visualizzazione,
        # escluso il vettore di embedding stesso.
        payload = {key: value for key, value in chunk.items() if key != 'embedding'}
        
        point = models.PointStruct(
            id=str(uuid.uuid4()),  # Genera un ID univoco per ogni punto
            vector=chunk['embedding'],
            payload=payload
        )
        points_to_upload.append(point)

    # Esegue l'upsert a lotti (batch) per efficienza
    print(f"\n--- Inizio Ingest di {len(points_to_upload)} punti in Qdrant ---")
    try:
        client.upsert(
            collection_name=config["qdrant_collection_name"],
            points=points_to_upload,
            wait=True  # Attende che l'operazione sia completata e indicizzata
        )
        print(f"✅ Ingest completato con successo.")
    except Exception as e:
        print(f"❌ ERRORE durante l'operazione di upsert su Qdrant: {e}")
        return

    # --- Creazione degli indici sui campi del payload per query veloci ---
    print("\n--- Verifica e creazione degli indici sul payload ---")
    fields_to_index = [
        "document_title",
        "document_type",
        "articolo",
        "livello_1_title",
        "livello_2_title",
        "livello_3_title"
    ]
    
    # NUOVO BLOCCO
    for field in fields_to_index:
        try:
            client.create_payload_index(
                collection_name=config["qdrant_collection_name"],
                field_name=field,
                field_schema="keyword" # Sintassi corretta e semplice per indici keyword
            )
            print(f"  -> Indice per il campo '{field}' creato/verificato.")
        except Exception as e:
            # L'errore qui è normale se l'indice esiste già.
            # Qdrant non ha un metodo "create_if_not_exists", quindi fallisce.
            # Lo interpretiamo come un "indice già presente".
            print(f"  -> Indice per il campo '{field}' probabilmente già esistente.")
            
        except Exception as e:
            # Potrebbe dare un errore se l'indice esiste già con parametri diversi,
            # o altri problemi. Per ora, lo segnaliamo.
            print(f"  -> ⚠️  Attenzione per l'indice '{field}': {e}")
            
    print("\n🎉 Processo di Ingest terminato.")


# --- 3. AVVIO ---
if __name__ == "__main__":
    ingest_data_to_qdrant()