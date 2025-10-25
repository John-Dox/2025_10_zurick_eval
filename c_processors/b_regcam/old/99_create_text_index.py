import os
from qdrant_client import QdrantClient, models
from dotenv import load_dotenv

def create_qdrant_text_index():
    """
    Script una tantum per creare un indice di tipo 'text' sul campo
    'testo_originale_comma' per abilitare la ricerca ibrida. (Versione corretta)
    """
    print("🚀 Avvio dello script per la creazione dell'indice di testo su Qdrant...")

    # Carica le variabili d'ambiente dal file .env
    try:
        proj_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        load_dotenv(os.path.join(proj_root, "a_chiavi", ".env"))
        
        qdrant_host = os.getenv("QDRANT_HOST")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")

        if not qdrant_host or not qdrant_api_key:
            raise ValueError("Credenziali QDRANT_HOST o QDRANT_API_KEY mancanti nel file .env")
            
    except Exception as e:
        print(f"❌ Errore nel caricamento della configurazione: {e}")
        return

    collection_name = "regcam_gemini_v9"
    field_name = "testo_originale_comma"

    try:
        client = QdrantClient(url=qdrant_host, api_key=qdrant_api_key)
        print(f"✅ Connesso a Qdrant: {qdrant_host}")

        print(f"⏳ Tentativo di creazione dell'indice di tipo 'text' sul campo '{field_name}' per la collezione '{collection_name}'...")
        
        # --- CORREZIONE: Rimossi i parametri min_gram e max_gram ---
        client.create_payload_index(
            collection_name=collection_name,
            field_name=field_name,
            field_schema=models.TextIndexParams(
                type=models.TextIndexType.TEXT,
                tokenizer=models.TokenizerType.WHITESPACE,
                lowercase=True
            )
        )
        # --- FINE CORREZIONE ---

        print(f"✅ SUCCESSO! L'indice di testo sul campo '{field_name}' è stato creato o già esisteva.")
        print("Ora puoi eseguire nuovamente lo script '5_3ricerca_ibrida.py'.")

    except Exception as e:
        print(f"❌ ERRORE durante la creazione dell'indice: {e}")
        print("L'indice potrebbe già esistere. Se l'errore persiste, controlla la UI di Qdrant.")

if __name__ == "__main__":
    create_qdrant_text_index()