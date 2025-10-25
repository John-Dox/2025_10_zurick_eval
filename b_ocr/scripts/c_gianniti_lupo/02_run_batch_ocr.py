# b_ocr/scripts/c_gianniti_lupo/02_run_batch_ocr.py

import os
import sys
import re
import json
from typing import Optional
from google.api_core.client_options import ClientOptions
from google.cloud import documentai, storage
from google.oauth2 import service_account

try:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    if project_root not in sys.path:
        sys.path.append(project_root)
    from g_src.g_general.utils import confirm_execution
except ImportError as e:
    print(f"ERRORE CRITICO: Impossibile importare 'confirm_execution'. Errore: {e}")
    exit()

# --- CONFIGURAZIONE ---
PROJECT_ID = "docai-gemini-rag"
LOCATION = "eu"
PROCESSOR_ID = "ab260baa64ea0cb" # Il nostro processore, in formato ab260baa64ea0cb
# --- MODIFICA: VERSIONE SPECIFICA DA UTILIZZARE ---
PROCESSOR_VERSION_ID = "pretrained-foundation-model-v1.5-pro-2025-06-20" # Forziamo la versione
GCS_BUCKET_NAME = "rag-doc-ai-bucket-storia"
BOOK_NAME = "c_gianniti_lupo"
TARGET_FOLDER = "cap_9" 
GCS_INPUT_PREFIX = f"gcs_input_ocr/{BOOK_NAME}/{TARGET_FOLDER}/"
GCS_OUTPUT_PREFIX = f"gcs_output_ocr/{BOOK_NAME}/{TARGET_FOLDER}/"
SERVICE_ACCOUNT_FILE = os.path.join(project_root, "a_chiavi", "service-account-key.json")
LOCAL_OUTPUT_DIRECTORY = os.path.join(project_root, "b_ocr", "output_json", BOOK_NAME, TARGET_FOLDER)
#LOCAL_OUTPUT_DIRECTORY = os.path.join(project_root, "b_ocr", "output_json", BOOK_NAME, "cap_1_ocr")
TIMEOUT = 400
# --- FINE CONFIGURAZIONE ---

def download_and_save_json_results(metadata: documentai.BatchProcessMetadata, local_output_dir: str, credentials):
    # ... (questa funzione rimane invariata) ...
    storage_client = storage.Client(credentials=credentials)
    os.makedirs(local_output_dir, exist_ok=True)
    for process_status in metadata.individual_process_statuses:
        output_gcs_destination = process_status.output_gcs_destination
        match = re.match(r"gs://(.*?)/(.*)", output_gcs_destination)
        if not match:
            print(f"ATTENZIONE: Impossibile parsare URI: {output_gcs_destination}")
            continue

        output_bucket_name, output_prefix = match.groups()
        blobs = storage_client.list_blobs(output_bucket_name, prefix=output_prefix)
        
        for blob in blobs:
            if not blob.name.lower().endswith(".json"):
                continue

            print(f"  - Download di: {blob.name}")
            json_content = blob.download_as_string()
            local_filename = os.path.basename(blob.name)
            local_filepath = os.path.join(local_output_dir, local_filename)

            with open(local_filepath, "w", encoding="utf-8") as f:
                parsed_json = json.loads(json_content)
                json.dump(parsed_json, f, indent=4, ensure_ascii=False)
            print(f"    -> Salvato in: {local_filepath}")
def run_batch_ocr(
    project_id: str, location: str, processor_id: str,
    gcs_bucket_name: str, gcs_input_prefix: str, gcs_output_prefix: str,
    local_output_dir: str, service_account_path: str, timeout: int,
    processor_version_id: Optional[str] = None # Nuovo parametro opzionale
):
    print("--- Inizio del processo di OCR Batch ---")
    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
    
    try:
        credentials = service_account.Credentials.from_service_account_file(service_account_path)
    except FileNotFoundError:
        print(f"ERRORE: File della chiave di servizio non trovato in '{service_account_path}'.")
        return
        
    client = documentai.DocumentProcessorServiceClient(client_options=opts, credentials=credentials)

    # --- MODIFICA: LOGICA CONDIZIONALE PER COSTRUIRE IL NOME DELLA RISORSA ---
    if processor_version_id:
        # Se è specificata una versione, si costruisce il percorso completo della versione.
        name = client.processor_version_path(
            project_id, location, processor_id, processor_version_id
        )
        print(f"Target: Versione specifica del processore -> {processor_version_id}")
    else:
        # Altrimenti, si usa la versione di default del processore.
        name = client.processor_path(project_id, location, processor_id)
        print("Target: Versione di default del processore.")

    gcs_prefix_config = documentai.GcsPrefix(gcs_uri_prefix=f"gs://{gcs_bucket_name}/{gcs_input_prefix}")
    input_config = documentai.BatchDocumentsInputConfig(gcs_prefix=gcs_prefix_config)
    print(f"1. Input configurato per leggere da: gs://{gcs_bucket_name}/{gcs_input_prefix}")

    gcs_output_uri = f"gs://{gcs_bucket_name}/{gcs_output_prefix}"
    gcs_output_config = documentai.DocumentOutputConfig.GcsOutputConfig(gcs_uri=gcs_output_uri)
    output_config = documentai.DocumentOutputConfig(gcs_output_config=gcs_output_config)
    print(f"2. Output configurato per scrivere su: {gcs_output_uri}")

    request = documentai.BatchProcessRequest(
        name=name, # La variabile 'name' ora contiene il percorso corretto
        input_documents=input_config, 
        document_output_config=output_config
    )

    try:
        operation = client.batch_process_documents(request)
        print(f"3. Operazione avviata. Nome operazione: {operation.operation.name}")
        print(f"   In attesa del completamento (timeout: {timeout} secondi)...")
        operation.result(timeout=timeout)
    except Exception as e:
        print(f"ERRORE durante l'avvio o l'attesa dell'operazione. Dettagli: {e}")
        return
        
    print("4. Operazione completata con successo.")
    metadata = documentai.BatchProcessMetadata(operation.metadata)
    if metadata.state != documentai.BatchProcessMetadata.State.SUCCEEDED:
        print(f"ERRORE: Elaborazione batch fallita. Stato: {metadata.state}, Messaggio: {metadata.state_message}")
        return

    print("\n5. Inizio download dei file di output JSON...")
    download_and_save_json_results(metadata, local_output_dir, credentials)
    print("\n--- Processo di OCR Batch completato. ---")
    print(f"I file JSON sono stati salvati in '{local_output_dir}'.")


if __name__ == "__main__":
    execution_settings = {
        "Script": "02_run_batch_ocr.py", "Target": TARGET_FOLDER,
        "Input GCS": GCS_INPUT_PREFIX, "Output GCS": GCS_OUTPUT_PREFIX,
        "Output Locale": LOCAL_OUTPUT_DIRECTORY
    }
    
    if confirm_execution(execution_settings):
        # La chiamata ora è corretta e corrisponde alla definizione della funzione.
        run_batch_ocr(
            project_id=PROJECT_ID, location=LOCATION, processor_id=PROCESSOR_ID, 
            processor_version_id=PROCESSOR_VERSION_ID, # Passiamo la versione
            gcs_bucket_name=GCS_BUCKET_NAME, gcs_input_prefix=GCS_INPUT_PREFIX,
            gcs_output_prefix=GCS_OUTPUT_PREFIX, local_output_dir=LOCAL_OUTPUT_DIRECTORY,
            service_account_path=SERVICE_ACCOUNT_FILE, timeout=TIMEOUT,
        )