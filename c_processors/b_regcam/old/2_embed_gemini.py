# g_src/summarize/2_embed_gemini.py

import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(PROJ_ROOT, "a_chiavi", ".env"))

INPUT_CHUNKS_FILE = os.path.join(PROJ_ROOT, "c_outputs_chunks", "chunks_v11_final.json")
OUTPUT_DIR = os.path.join(PROJ_ROOT, "c_outputs_embeddings")
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "embeddings_v11.json")
EMBEDDING_MODEL = "text-embedding-004"

def genera_embedding_gemini():
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    
    with open(INPUT_CHUNKS_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    print(f"📄 Caricati {len(chunks)} chunk da: {os.path.basename(INPUT_CHUNKS_FILE)}")

    testi_da_embeddare = []
    for chunk in chunks:
        contesto_gerarchico = (
            f"Documento: {chunk.get('documento_titolo', '')}. "
            f"Parte: {chunk.get('parte_titolo', '')}. "
            f"Capo: {chunk.get('capo_titolo', '')}. "
            f"Articolo: {chunk.get('articolo', '')}."
        )
        keywords_str = ", ".join(chunk.get("keywords", []))
        testo_arricchito = f"Contesto: {contesto_gerarchico}\nParole Chiave: {keywords_str}\nTesto: {chunk.get('testo_originale_comma', '')}"
        testi_da_embeddare.append(testo_arricchito)
    
    print(f"🧠 Preparata richiesta embedding per {len(testi_da_embeddare)} testi...")

    result = genai.embed_content(
        model=f'models/{EMBEDDING_MODEL}',
        content=testi_da_embeddare,
        task_type="RETRIEVAL_DOCUMENT"
    )
    all_embeddings = result['embedding']
    print(f"✅ Ricevuti {len(all_embeddings)} embedding.")
    
    chunks_con_embedding = [
        chunk | {"embedding": all_embeddings[i]}
        for i, chunk in enumerate(chunks)
    ]
        
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(chunks_con_embedding, f, ensure_ascii=False, indent=2)

    print(f"✅ Generazione embedding completata.\n📁 Salvato file in: {OUTPUT_FILE}")

if __name__ == "__main__":
    genera_embedding_gemini()