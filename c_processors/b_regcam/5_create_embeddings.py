# c_processors/b_regcam/5_create_embeddings.py

"""
PASSO 5 della pipeline di processamento per il Regolamento della Camera.

Questo script calcola la rappresentazione vettoriale (embedding) per ogni chunk
del Regolamento, utilizzando l'elaborazione in BATCH per massimizzare
l'efficienza.

Utilizza la "ricetta" di embedding standard e robusta, che si è dimostrata
efficace nel preservare il segnale semantico.

Logica di Robustezza Implementata:
- Carica un file di output esistente per riprendere i progressi.
- Salva i progressi in modo incrementale dopo aver processato ogni batch.
- Implementa un "Circuit Breaker" per interrompersi dopo errori API consecutivi.

INPUT:
- d_outputs/04_chunks/b_regcam/regcam_chunks.json

OUTPUT:
- d_outputs/05_embeddings/b_regcam/regcam_embeddings.json
"""

import os
import sys
import json
import time
import google.generativeai as genai
from dotenv import load_dotenv

# --- Setup del Percorso ---
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Caricamento Configurazione ---
env_path = os.path.join(project_root, "a_chiavi", ".env")
load_dotenv(dotenv_path=env_path)

# --- Definizione dei Percorsi (specifici per b_regcam) ---
CHUNKS_DIR = os.path.join(project_root, "d_outputs", "04_chunks", "b_regcam")
EMBEDDINGS_DIR = os.path.join(project_root, "d_outputs", "05_embeddings", "b_regcam")

INPUT_CHUNKS_PATH = os.path.join(CHUNKS_DIR, "regcam_chunks.json")
OUTPUT_EMBEDDINGS_PATH = os.path.join(EMBEDDINGS_DIR, "regcam_embeddings.json")

# --- Costanti ---
EMBEDDING_MODEL = "text-embedding-004"
BATCH_SIZE = 100
CONSECUTIVE_ERROR_LIMIT = 3

def build_text_to_embed(chunk: dict) -> str:
    # Usiamo solo il titolo della sezione più specifica, che è il contesto più rilevante.
    contesto_specifico = chunk.get('livello_3_title') or chunk.get('livello_2_title') or chunk.get('livello_1_title', '')

    parts = []
    # Diamo un'etichetta forte al contesto specifico
    if contesto_specifico:
        parts.append(f"Argomento Principale: {contesto_specifico}.")
    
    # Il testo rimane il cuore
    parts.append(f"Testo: {chunk.get('testo_originale_comma', '')}.")
    
    # Le keyword concludono
    if chunk.get("keywords"):
        parts.append(f"Concetti Chiave: {', '.join(chunk['keywords'])}.")
        
    return " ".join(parts)

# def build_text_to_embed(chunk: dict) -> str:
#     """
#     Costruisce la "super-stringa" da vettorializzare secondo la ricetta standard.
#     """
#     parts = []
#     if chunk.get("document_title"): parts.append(f"Titolo del Documento: {chunk['document_title']}.")
#     if chunk.get("document_type"): parts.append(f"Tipo di Documento: {chunk['document_type']}.")
#     if chunk.get("livello_1_title"): parts.append(f"Sezione Principale: {chunk['livello_1_title']}.")
#     if chunk.get("livello_2_title"): parts.append(f"Sottosezione: {chunk['livello_2_title']}.")
#     if chunk.get("livello_3_title"): parts.append(f"Ulteriore Sottosezione: {chunk['livello_3_title']}.")
#     parts.append(f"Articolo: {chunk.get('articolo', 'N/A')}, Comma: {chunk.get('comma', 'N/A')}.")
#     parts.append(f"Testo: {chunk.get('testo_originale_comma', '')}.")
#     if chunk.get("keywords"):
#         parts.append(f"Parole Chiave: {', '.join(chunk['keywords'])}.")
#     return " ".join(parts)

def save_progress(data, path):
    """Funzione di aiuto per salvare i dati in un file JSON."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    """Orchestra il processo di generazione degli embedding per il Regolamento."""
    print("--- PASSO 5 (Batch, Regcam): Inizio Generazione Embedding ---")
    os.makedirs(EMBEDDINGS_DIR, exist_ok=True)

    try:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    except Exception as e:
        print(f"❌ ERRORE CRITICO: Configurazione Gemini fallita. Errore: {e}"); sys.exit(1)

    try:
        with open(INPUT_CHUNKS_PATH, 'r', encoding='utf-8') as f:
            chunks_data = json.load(f)
    except FileNotFoundError:
        print(f"❌ ERRORE CRITICO: File di input dei chunk non trovato a: {INPUT_CHUNKS_PATH}"); sys.exit(1)

    embeddings_results = []
    processed_chunk_ids = set()
    if os.path.exists(OUTPUT_EMBEDDINGS_PATH):
        print(f"ℹ️  Trovato file di output esistente. Carico i progressi...")
        with open(OUTPUT_EMBEDDINGS_PATH, 'r', encoding='utf-8') as f:
            try:
                embeddings_results = json.load(f)
                for item in embeddings_results:
                    unique_id = f"art_{item.get('articolo')}_comma_{item.get('comma')}"
                    processed_chunk_ids.add(unique_id)
                print(f"✅  Recuperati {len(processed_chunk_ids)} embedding già generati.")
            except json.JSONDecodeError:
                print("⚠️  WARNING: Il file di output corrotto. Ripartenza da zero."); embeddings_results = []
    
    items_to_process = [c for c in chunks_data if f"art_{c.get('articolo')}_comma_{c.get('comma')}" not in processed_chunk_ids]
    if not items_to_process:
        print("🎉 Tutti i chunk hanno già un embedding. Nessuna azione richiesta."); return

    print(f"\nInizio elaborazione di {len(items_to_process)} chunk rimanenti in batch da {BATCH_SIZE}...")
    consecutive_errors = 0
    
    for i in range(0, len(items_to_process), BATCH_SIZE):
        batch_chunks = items_to_process[i:i + BATCH_SIZE]
        batch_texts = [build_text_to_embed(chunk) for chunk in batch_chunks]
        
        start_idx = len(processed_chunk_ids) + i + 1
        end_idx = min(start_idx + BATCH_SIZE - 1, len(processed_chunk_ids) + len(items_to_process))
        print(f"  -> Generazione embedding per batch #{i//BATCH_SIZE + 1} (chunk da {start_idx} a {end_idx})")

        try:
            result = genai.embed_content(
                model=f"models/{EMBEDDING_MODEL}",
                content=batch_texts,
                task_type="RETRIEVAL_DOCUMENT"
            )
            
            batch_embeddings = result['embedding']
            for chunk, embedding_vector in zip(batch_chunks, batch_embeddings):
                chunk['embedding'] = embedding_vector
            
            embeddings_results.extend(batch_chunks)
            consecutive_errors = 0
            print(f"     ✅ Batch completato. Salvataggio progressi...")
            save_progress(embeddings_results, OUTPUT_EMBEDDINGS_PATH)
            time.sleep(1)

        except Exception as e:
            print(f"     ❌ ERRORE durante la generazione dell'embedding per il batch: {e}")
            consecutive_errors += 1
            if consecutive_errors >= CONSECUTIVE_ERROR_LIMIT:
                print(f"\n❌ ERRORE CRITICO: Rilevati {CONSECUTIVE_ERROR_LIMIT} errori. Interruzione."); break
            time.sleep(5)

    if consecutive_errors < CONSECUTIVE_ERROR_LIMIT:
        print("\n🎉 Processo di generazione embedding terminato con successo.")
    else:
        print("\n⚠️  Processo interrotto. I progressi parziali sono stati salvati.")

if __name__ == "__main__":
    main()