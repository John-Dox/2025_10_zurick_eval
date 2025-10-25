import os
import json
from qdrant_client import QdrantClient, models
from dotenv import load_dotenv

def load_config():
    """Carica la configurazione e si connette a Qdrant."""
    proj_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    load_dotenv(os.path.join(proj_root, "a_chiavi", ".env"))

    # Configurazione aggiornata per puntare ai nuovi file e alla nuova collezione
    config = {
        "input_embeddings_file": os.path.join(proj_root, "c_outputs_embeddings", "embeddings_v11.json"),
        "qdrant_collection_name": "regcam_v11",
        "vector_dimension": 768  # Dimensione per il modello text-embedding-004 di Gemini
    }

    try:
        client = QdrantClient(url=os.getenv("QDRANT_HOST"), api_key=os.getenv("QDRANT_API_KEY"))
        print("🔌 Connesso a Qdrant.")
        return config, client
    except Exception as e:
        print(f"❌ ERRORE CRITICO in fase di connessione a Qdrant: {e}")
        exit()

def ingest_data(config, client):
    """Esegue il processo di ingest dei dati nella collezione Qdrant specificata."""
    collection_name = config["qdrant_collection_name"]

    print(f"🔧 Tentativo di creare/ricreare la collezione '{collection_name}'...")
    try:
        client.recreate_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=config["vector_dimension"],
                distance=models.Distance.COSINE
            )
        )
        print(f"✅ Collezione '{collection_name}' ricreata con successo.")
    except Exception as e:
        print(f"❌ Errore durante la creazione della collezione: {e}")
        return

    # --- LISTA CAMPI DA INDICIZZARE - CORRETTA E AGGIORNATA ---
    # Questi campi corrispondono allo schema pulito di chunks_v11_final.json
    # e includono il nuovo campo per la futura gestione multi-documento.
    keyword_index_fields = [
        "document_type",
        "articolo",
        "capo_id_roman",
        "parte_id_roman"
    ]
    
    try:
        print("📈 Creazione indici KEYWORD sui campi strutturali...")
        for field in keyword_index_fields:
            client.create_payload_index(
                collection_name=collection_name,
                field_name=field,
                field_schema=models.PayloadSchemaType.KEYWORD,
                wait=True
            )
            print(f"  - ✅ Indice creato su: {field}")
    except Exception as e:
        print(f"❌ Errore durante la creazione degli indici: {e}")
        return

    try:
        with open(config["input_embeddings_file"], 'r', encoding='utf-8') as f:
            documents = json.load(f)
        print(f"📄 Caricati {len(documents)} documenti da {os.path.basename(config['input_embeddings_file'])}.")
    except FileNotFoundError:
        print(f"❌ ERRORE: File non trovato: {config['input_embeddings_file']}")
        return

    print(f"📤 Caricamento di {len(documents)} punti in Qdrant...")
    try:
        # Crea i punti da caricare, escludendo il campo 'embedding' dal payload
        points_to_upsert = [
            models.PointStruct(
                id=i,
                vector=doc["embedding"],
                payload={k: v for k, v in doc.items() if k != 'embedding'}
            )
            for i, doc in enumerate(documents)
        ]

        client.upload_points(
            collection_name=collection_name,
            points=points_to_upsert,
            wait=True,
            batch_size=100  # Batch size per ottimizzare l'upload
        )
        info = client.get_collection(collection_name)
        print(f"✅ Ingest completato. Totale punti nella collezione: {info.points_count}")
    except Exception as e:
        print(f"❌ Errore durante l'upload: {e}")

if __name__ == "__main__":
    config, client = load_config()
    ingest_data(config, client)