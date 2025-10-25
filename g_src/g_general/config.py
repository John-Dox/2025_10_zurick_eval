import os
import sys
import json
from dotenv import load_dotenv
from qdrant_client import QdrantClient
import google.generativeai as genai
from openai import OpenAI

def load_config_and_clients():
    """
    Carica tutte le configurazioni, le chiavi API, i client, i prompt di sistema
    e aggrega i file di dati da tutte le fonti documentali disponibili.
    """
    print("--- Inizializzazione Sistema RAG Multi-Documento ---")
    
    try:
        proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    except NameError:
        proj_root = os.path.abspath('.')

    env_path = os.path.join(proj_root, "a_chiavi", ".env")
    load_dotenv(env_path)

    config = {
        # --- MODIFICA: Nomi dei modelli corretti e aggiornati ---
        "models": { 
            "router": "gemini-2.5-flash", 
            "default_generator": "gemini-2.5-flash", # Associato a @flash
            "gpt": "gpt-4o-mini",                     # Associato a @gpt
            "pro": "gemini-2.5-pro"                      # Associato a @pro
        },
        "gemini_embedding_model": "text-embedding-004",
        "qdrant_collection_name": "regcam_v11",
        "structured_data_dir": os.path.join(proj_root, "d_outputs", "03_structured"),
        "chunks_data_dir": os.path.join(proj_root, "d_outputs", "04_chunks"),
        "prompts_dir": os.path.join(proj_root, "g_src", "a_prompts") # Percorso centralizzato per i prompt
    }

    DOC_INFO_MAP = {
        "a_cost": {
            "document_title": "Costituzione della Repubblica Italiana",
            "document_type": "costituzione"
        },
        "b_regcam": {
            "document_title": "Regolamento della Camera dei Deputati",
            "document_type": "regolamento_parlamentare"
        }
    }

    try:
        openai_api_key = os.getenv("OPENAI_API_KEY")
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not openai_api_key or not gemini_api_key:
            raise ValueError("API Keys mancanti nel file .env")

        genai.configure(api_key=gemini_api_key)

        clients = {
            "openai_generator": OpenAI(api_key=openai_api_key),
            "qdrant": QdrantClient(url=os.getenv("QDRANT_HOST"), api_key=os.getenv("QDRANT_API_KEY")),
            "gemini_models": {
                key: genai.GenerativeModel(model_name)
                for key, model_name in config["models"].items() if key != 'gpt'
            }
        }
        print("✅ Client AI e Qdrant inizializzati.")

        # ======================================================================
        # --- NUOVA SEZIONE: CARICAMENTO DINAMICO DEI PROMPT DI SISTEMA ---
        # ======================================================================
        print("📚 Caricamento dei prompt di sistema...")
        config["prompts"] = {}
        prompts_dir = config["prompts_dir"]
        if os.path.isdir(prompts_dir):
            for filename in os.listdir(prompts_dir):
                if filename.endswith(".txt"):
                    prompt_key = filename.replace(".txt", "")
                    try:
                        with open(os.path.join(prompts_dir, filename), "r", encoding="utf-8") as f:
                            config["prompts"][prompt_key] = f.read()
                    except Exception as e:
                        print(f"⚠️  WARNING: Impossibile leggere il file prompt '{filename}'. Errore: {e}")
            
            if config["prompts"]:
                print(f"   - Trovati {len(config['prompts'])} prompt: {list(config['prompts'].keys())}")
            else:
                print("   - Nessun file .txt di prompt trovato nella cartella.")
        else:
            print(f"   - ⚠️  WARNING: Cartella dei prompt non trovata a '{prompts_dir}'.")
        # ======================================================================
            

        print("🔎 Caricamento e aggregazione dati da tutte le fonti...")
        
        all_docs_structures = []
        all_docs_summaries = {}
        all_docs_chunks = []

        structured_dir = config["structured_data_dir"]
        for doc_folder_name in sorted(os.listdir(structured_dir)):
            doc_folder_path = os.path.join(structured_dir, doc_folder_name)
            if os.path.isdir(doc_folder_path) and doc_folder_name in DOC_INFO_MAP:
                print(f"  -> Processo fonte: '{doc_folder_name}'")
                
                doc_metadata = DOC_INFO_MAP[doc_folder_name]

                structure_file = next((f for f in os.listdir(doc_folder_path) if f.endswith('_structure.json')), None)
                if structure_file:
                    with open(os.path.join(doc_folder_path, structure_file), "r", encoding="utf-8") as f:
                        data = json.load(f)
                        data['document_title'] = doc_metadata['document_title']
                        data['document_type'] = doc_metadata['document_type']
                        all_docs_structures.append(data)
                    print(f"     - File Struttura '{structure_file}' caricato e normalizzato.")
                
                summaries_file = next((f for f in os.listdir(doc_folder_path) if f.endswith('_summaries.json')), None)
                if summaries_file:
                    with open(os.path.join(doc_folder_path, summaries_file), "r", encoding="utf-8") as f:
                        summaries_content = json.load(f)
                        all_docs_summaries.update(summaries_content.get("summaries", {}))
                    print(f"     - File Riassunti '{summaries_file}' caricato e unito.")
        
        chunks_folder_path = config["chunks_data_dir"]
        for doc_folder in sorted(os.listdir(chunks_folder_path)):
             doc_chunks_path = os.path.join(chunks_folder_path, doc_folder)
             if os.path.isdir(doc_chunks_path):
                 chunk_file = next((f for f in os.listdir(doc_chunks_path) if f.endswith('_chunks.json')), None)
                 if chunk_file:
                     with open(os.path.join(doc_chunks_path, chunk_file), "r", encoding="utf-8") as f:
                         all_docs_chunks.extend(json.load(f))
                     print(f"     - File Chunks '{chunk_file}' caricato e unito.")

        print(f"\n✅ Aggregazione completata.")
        print(f"   - Totale documenti strutturati: {len(all_docs_structures)}")
        print(f"   - Totale riassunti: {len(all_docs_summaries)}")
        print(f"   - Totale chunks in memoria: {len(all_docs_chunks)}")
        
        return config, clients, all_docs_structures, all_docs_summaries, all_docs_chunks

    except Exception as e:
        print(f"❌ ERRORE CRITICO in fase di inizializzazione: {e}")
        sys.exit(1)

if __name__ == '__main__':
    load_config_and_clients()