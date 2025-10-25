import os
import json
import time
import google.generativeai as genai
from dotenv import load_dotenv

# --- 1. CONFIGURAZIONE ---
def load_config_and_clients():
    """Carica configurazioni, percorsi e client AI per il Regolamento."""
    proj_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    load_dotenv(os.path.join(proj_root, "a_chiavi", ".env"))
    
    chunks_dir = os.path.join(proj_root, "d_outputs", "01_chunks", "b_regcam")
    embeddings_dir = os.path.join(proj_root, "d_outputs", "02_embeddings", "b_regcam")
    os.makedirs(embeddings_dir, exist_ok=True)
    
    config = {
        "embedding_model": "text-embedding-004",
        "input_chunks_file": os.path.join(chunks_dir, "regcam_chunks.json"),
        "output_embeddings_file": os.path.join(embeddings_dir, "regcam_embeddings.json")
    }
    
    try:
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        print("✅ Configurazione caricata e client AI inizializzato.")
        return config
    except Exception as e:
        print(f"❌ ERRORE CRITICO in fase di inizializzazione: {e}")
        exit()

# --- 2. LOGICA DI EMBEDDING ---

def generate_embeddings():
    """
    Carica i chunk finali del Regolamento, genera gli embedding e salva il risultato.
    """
    config = load_config_and_clients()

    try:
        with open(config["input_chunks_file"], 'r', encoding='utf-8') as f:
            chunks_data = json.load(f)
        print(f"📄 Caricati {len(chunks_data)} chunk da: {os.path.basename(config['input_chunks_file'])}")
    except FileNotFoundError:
        print(f"❌ ERRORE: File dei chunk non trovato: {config['input_chunks_file']}")
        return
    except json.JSONDecodeError:
        print(f"❌ ERRORE: Impossibile decodificare il JSON dal file dei chunk.")
        return

    embeddings_data = []
    
    print("\n--- Inizio Processo di Generazione Embedding per il Regolamento ---")
    total_chunks = len(chunks_data)
    for i, chunk in enumerate(chunks_data):
        text_to_embed = (
            f"Titolo del Documento: {chunk.get('document_title', '')}. "
            f"Tipo di Documento: {chunk.get('document_type', '')}. "
            f"Parte: {chunk.get('livello_1_title', '')}. "
            f"Capo: {chunk.get('livello_2_title', '')}. "
            f"Articolo: {chunk.get('articolo', '')}, Comma: {chunk.get('comma', '')}. "
            f"Testo: {chunk.get('testo_originale_comma', '')}. "
            f"Parole Chiave: {', '.join(chunk.get('keywords', []))}."
        )

        try:
            result = genai.embed_content(
                model=f"models/{config['embedding_model']}",
                content=text_to_embed,
                task_type="RETRIEVAL_DOCUMENT"
            )
            embedding_vector = result['embedding']
            
            chunk['embedding'] = embedding_vector
            embeddings_data.append(chunk)
            
            print(f"  -> Embedding generato per chunk #{i+1}/{total_chunks} (Art. {chunk.get('articolo')}, Comma {chunk.get('comma')})")
            
            time.sleep(1.1)

        except Exception as e:
            print(f"❌ ERRORE durante la generazione dell'embedding per il chunk #{i+1}: {e}")
            print("    Interruzione del processo.")
            if embeddings_data:
                partial_save_path = config["output_embeddings_file"].replace(".json", "_PARTIAL.json")
                with open(partial_save_path, "w", encoding="utf-8") as f:
                    json.dump(embeddings_data, f, ensure_ascii=False, indent=2)
                print(f"    ⚠️ Salvataggio parziale effettuato in: {partial_save_path}")
            return
            
    with open(config["output_embeddings_file"], "w", encoding="utf-8") as f:
        json.dump(embeddings_data, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 Generazione embedding completata!")
    print(f"✅ Generati {len(embeddings_data)} vettori.")
    print(f"📁 File salvato in: {config['output_embeddings_file']}")

# --- 3. AVVIO ---
if __name__ == "__main__":
    generate_embeddings()