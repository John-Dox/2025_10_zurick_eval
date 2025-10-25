# b_ocr/scripts/d_sabbatucci_vidotto/01_upload_to_gcs.py

import os
import sys
import json
from google.cloud import storage
from google.api_core.exceptions import NotFound
from google.oauth2 import service_account

# --- CONFIGURAZIONE E SETUP PERCORSI ---
try:
    # Naviga indietro di 3 livelli dalla posizione dello script per trovare la root del progetto
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    if project_root not in sys.path:
        sys.path.append(project_root)
except Exception as e:
    print(f"ERRORE CRITICO di configurazione percorsi: {e}")
    exit()

# Impostazioni generali
GCS_BUCKET_NAME = "rag-doc-ai-bucket-storia"
# Modificare questa variabile per cambiare il libro target
BOOK_NAME = "c_gianniti_lupo" 
# Modificare questa variabile per cambiare la cartella target (es. "0_indice", "cap_1", ecc.)
TARGET_FOLDER = "cap_9" 

# Percorsi calcolati dinamicamente
SERVICE_ACCOUNT_FILE = os.path.join(project_root, "a_chiavi", "service-account-key.json")
LOCAL_IMAGE_DIRECTORY = os.path.join(project_root, "b_ocr", "input_images", BOOK_NAME, TARGET_FOLDER)
GCS_DESTINATION_PREFIX = f"gcs_input_ocr/{BOOK_NAME}/{TARGET_FOLDER}/"
STATUS_FILE_PATH = os.path.join(project_root, "b_ocr", "status_files", BOOK_NAME, f"upload_status_{TARGET_FOLDER}.json")
# --- FINE CONFIGURAZIONE ---


def load_upload_status(status_file: str) -> set:
    """Carica l'elenco dei file già caricati con successo."""
    try:
        os.makedirs(os.path.dirname(status_file), exist_ok=True)
        with open(status_file, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

def save_upload_status(status_file: str, uploaded_files: set):
    """Salva l'elenco aggiornato dei file caricati."""
    with open(status_file, "w", encoding="utf-8") as f:
        json.dump(sorted(list(uploaded_files)), f, indent=4)

def upload_files_to_gcs_resumable(
    bucket_name: str,
    source_directory: str,
    destination_prefix: str,
    status_file: str,
    service_account_path: str
):
    """Carica i file da una cartella locale a GCS, riprendendo da dove si era interrotto."""
    print("--- Inizio del processo di upload su Google Cloud Storage (con ripristino) ---")

    if not os.path.isdir(source_directory):
        print(f"ERRORE: La cartella locale '{source_directory}' non è stata trovata.")
        return

    already_uploaded = load_upload_status(status_file)
    print(f"Trovati {len(already_uploaded)} file già caricati in esecuzioni precedenti.")

    try:
        local_files = {f for f in os.listdir(source_directory) if os.path.isfile(os.path.join(source_directory, f))}
    except FileNotFoundError:
        print(f"ERRORE: La cartella '{source_directory}' non esiste.")
        return
    
    files_to_upload = local_files - already_uploaded
    
    if not files_to_upload:
        print("Tutti i file locali sono già presenti su Google Cloud Storage. Nessuna azione richiesta.")
        return
        
    print(f"File locali totali: {len(local_files)}. File da caricare in questa sessione: {len(files_to_upload)}.")

    try:
        # Autenticazione esplicita usando il file della chiave di servizio
        credentials = service_account.Credentials.from_service_account_file(service_account_path)
        storage_client = storage.Client(credentials=credentials, project=credentials.project_id)
        bucket = storage_client.get_bucket(bucket_name)
    except FileNotFoundError:
        print(f"ERRORE: File della chiave di servizio non trovato in '{service_account_path}'.")
        return
    except NotFound:
        print(f"ERRORE: Il bucket '{bucket_name}' non è stato trovato.")
        return
    except Exception as e:
        print(f"ERRORE: Impossibile connettersi a GCS. Dettagli: {e}")
        return

    for i, filename in enumerate(sorted(list(files_to_upload))):
        local_file_path = os.path.join(source_directory, filename)
        destination_blob_name = f"{destination_prefix}{filename}"
        blob = bucket.blob(destination_blob_name)
        
        print(f"  [{i+1}/{len(files_to_upload)}] Caricamento di '{filename}'...")
        
        try:
            blob.upload_from_filename(local_file_path)
            already_uploaded.add(filename)
            save_upload_status(status_file, already_uploaded)
            print(f"    -> Caricato con successo. Stato aggiornato.")
        except Exception as e:
            print(f"    -> ERRORE durante il caricamento di {filename}. Dettagli: {e}")
            continue

    print("\n--- Processo di upload completato. ---")

if __name__ == "__main__":
    upload_files_to_gcs_resumable(
        bucket_name=GCS_BUCKET_NAME,
        source_directory=LOCAL_IMAGE_DIRECTORY,
        destination_prefix=GCS_DESTINATION_PREFIX,
        status_file=STATUS_FILE_PATH,
        service_account_path=SERVICE_ACCOUNT_FILE
    )