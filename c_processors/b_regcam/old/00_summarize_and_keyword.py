# g_src/summarize/00_summarize_and_keyword.py (v1.4 - Salva Testo e Keyword)

import os
import pypandoc
import json
import re
import time
import google.generativeai as genai
from dotenv import load_dotenv

# --- 1. CONFIGURAZIONE E INIZIALIZZAZIONE ---
def load_config():
    proj_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    load_dotenv(os.path.join(proj_root, "a_chiavi", ".env"))
    
    config = {
        "gemini_model": "gemini-2.5-pro-preview-06-05",
        "input_corpo_docx": os.path.join(proj_root, "b_testi", "regolamento_camera.docx"),
        "input_structure_file": os.path.join(proj_root, "d_structured_outputs", "regolamento_camera_structure.json"),
        "output_dir": os.path.join(proj_root, "d_structured_outputs"),
        "output_enriched_file": os.path.join(proj_root, "d_structured_outputs", "enriched_data_v2.json"),
        "progress_file": os.path.join(proj_root, "d_structured_outputs", "enrichment_progress_v2.json")
    }
    
    os.makedirs(config["output_dir"], exist_ok=True)
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel(config["gemini_model"])
    
    print("✅ Configurazione caricata e client AI inizializzato.")
    return config, model

# --- 2. FUNZIONI DI UTILITÀ E ANALISI AI ---

def clean_text(text: str) -> str:
    text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
    text = re.sub(r'\n{2,}', '\n\n', text)
    return text.strip()

def clean_json_from_text(text: str, expected_type='list'):
    pattern_map = {'list': r'```json\s*(\[[\s\S]*?\])\s*```', 'object': r'```json\s*(\{[\s\S]*?\})\s*```'}
    fallback_map = {'list': ('[', ']'), 'object': ('{', '}')}
    default_return_map = {'list': "[]", 'object': "{}"}

    pattern = pattern_map.get(expected_type)
    fallback_start, fallback_end = fallback_map.get(expected_type)
    default_return = default_return_map.get(expected_type)

    match = re.search(pattern, text)
    if match: return match.group(1)
    start = text.find(fallback_start)
    end = text.rfind(fallback_end)
    if start != -1 and end != -1: return text[start:end+1]
    return default_return

def get_commi_from_ai(model, testo_articolo: str):
    prompt = (
        "Sei un assistente di parsing legale di massima precisione. Il tuo unico compito è prendere il testo di un articolo del 'Regolamento della Camera dei Deputati' e suddividerlo in un array di oggetti JSON. Ogni oggetto rappresenta un singolo comma.\n\n"
        "**SCHEMA DELL'OGGETTO JSON PER OGNI COMMA:**\n"
        "- `\"comma_num\"`: il numero del comma come stringa.\n"
        "- `\"testo_comma\"`: il testo completo del comma, incluso il numero iniziale.\n\n"
        "Restituisci SOLO l'array JSON valido.\n\n"
        f"--- TESTO DA SEGMENTARE ---\n{testo_articolo}\n---\n\nJSON di output:"
    )
    try:
        response = model.generate_content(prompt)
        json_text = clean_json_from_text(response.text, 'list')
        return json.loads(json_text)
    except Exception as e:
        print(f"  ⚠️ Errore parsing commi: {e}.")
        return []

def get_chapter_summary(model, chapter_text: str, chapter_title: str):
    print(f"  -> Analizzando il Capitolo: {chapter_title}...")
    prompt = (
        "Il tuo unico compito è riassumere il testo fornito. Non usare alcuna conoscenza esterna. Se il testo fornito è vuoto o insufficiente, rispondi con 'INSUFFICIENTE'.\n"
        f"**Testo da riassumere (estratto dal '{chapter_title}' del 'Regolamento della Camera dei Deputati'):**\n"
        f"```\n{chapter_text}\n```\n\n"
        "**Compito:** Fornisci un riassunto di 2-3 frasi basato solo sul testo qui sopra."
    )
    response = model.generate_content(prompt)
    return response.text.strip()

def get_keywords_for_comma(model, comma_text: str, chapter_summary: str):
    prompt = (
        "Sei un esperto di indicizzazione semantica per documenti legali italiani. Il tuo compito è generare keyword specifiche per un singolo comma del 'Regolamento della Camera dei Deputati', tenendo conto del contesto del capitolo.\n\n"
        f"**Contesto Globale del Capitolo:**\n{chapter_summary}\n\n"
        "**Testo del Comma da Analizzare:**\n"
        f"```\n{comma_text}\n```\n\n"
        "**Compito:** Restituisci un array JSON di 3-5 parole chiave o brevi frasi (massimo 3 parole) che descrivano specificamente il contenuto di questo comma. Le keyword devono essere in minuscolo."
    )
    response = model.generate_content(prompt)
    json_text = clean_json_from_text(response.text, 'list')
    return json.loads(json_text)

# --- 3. PROCESSO PRINCIPALE ---
def run_enrichment(config, model):
    with open(config["input_structure_file"], "r", encoding="utf-8") as f:
        structure_map = json.load(f)
    
    testo_corpo = clean_text(pypandoc.convert_file(config["input_corpo_docx"], 'plain', format='docx'))
    pattern_articolo = re.compile(r'(Art\.\s*\d+(?:-[a-zA-Z]+)*)', re.IGNORECASE)
    parti_testo = pattern_articolo.split(testo_corpo)[1:]
    articoli_testo_mappa = {re.search(r'(\d+(?:-[a-zA-Z]+)*)', p[0]).group(1): f"{p[0]}\n{p[1].strip()}" for p in zip(parti_testo[0::2], parti_testo[1::2])}
    
    progress = {"last_processed_article": "0", "summaries": {}, "enriched_data": []}
    if os.path.exists(config["progress_file"]):
        try:
            with open(config["progress_file"], 'r', encoding='utf-8') as f:
                progress = json.load(f)
        except json.JSONDecodeError:
            os.remove(config["progress_file"])

    last_processed_article = progress.get("last_processed_article", "0")
    final_enriched_data = progress.get("enriched_data", [])
    chapter_summaries = progress.get("summaries", {})
    
    all_chapters = [capo for parte in structure_map["parti"] for capo in parte["capi"]]
    
    print("\n--- FASE A: Generazione Riassunti dei Capitoli ---")
    for chapter in all_chapters:
        chapter_title = chapter["capo_titolo"]
        if chapter_title not in chapter_summaries:
            articles_in_this_chapter_from_docx = [art_id for art_id in chapter["articoli"] if art_id in articoli_testo_mappa]
            chapter_text = "\n\n".join([articoli_testo_mappa[art_id] for art_id in articles_in_this_chapter_from_docx]) if articles_in_this_chapter_from_docx else ""
            summary = get_chapter_summary(model, chapter_text, chapter_title)
            if "INSUFFICIENTE" not in summary:
                chapter_summaries[chapter_title] = summary
            else:
                print(f"  -> Testo insufficiente per il Capitolo {chapter_title}. Riassunto saltato.")
            time.sleep(1)

    progress["summaries"] = chapter_summaries
    with open(config["progress_file"], "w", encoding="utf-8") as f: json.dump(progress, f, ensure_ascii=False, indent=2)
    print("✅ Riassunti dei capitoli generati e salvati.")

    print("\n--- FASE B: Arricchimento Commi con Keyword ---")
    articles_to_process = sorted(articoli_testo_mappa.keys(), key=lambda x: int(re.match(r'\d+', x).group()))

    for article_id in articles_to_process:
        if int(re.match(r'\d+', article_id).group()) <= int(re.match(r'\d+', last_processed_article).group()):
            continue
            
        print(f"\n--- Elaborazione Articolo {article_id} ---")
        
        current_chapter_title = next((capo["capo_titolo"] for parte in structure_map["parti"] for capo in parte["capi"] if article_id in capo["articoli"]), None)
        if not current_chapter_title: continue
            
        global_context_summary = chapter_summaries.get(current_chapter_title, "Nessun contesto di capitolo disponibile.")
        
        commi_obj = get_commi_from_ai(model, articoli_testo_mappa[article_id])
        print(f"  Segmentazione AI: Trovati {len(commi_obj)} commi.")
        
        for comma_data in commi_obj:
            comma_num = comma_data.get("comma_num", "1")
            comma_text = comma_data.get("testo_comma", "")
            if not comma_text: continue
            
            print(f"  -> Generando keyword per comma {comma_num}...")
            keywords = get_keywords_for_comma(model, comma_text, global_context_summary)
            
            # --- MODIFICA CHIAVE: Salva testo e keyword insieme ---
            final_enriched_data.append({
                "articolo": article_id,
                "comma": comma_num,
                "testo_originale_comma": comma_text,
                "keywords": keywords
            })
            time.sleep(1)
        
        progress["last_processed_article"] = article_id
        progress["enriched_data"] = final_enriched_data
        with open(config["progress_file"], "w", encoding="utf-8") as f: json.dump(progress, f, ensure_ascii=False, indent=2)
        print(f"✅ Progresso per Art. {article_id} salvato.")

    with open(config["output_enriched_file"], "w", encoding="utf-8") as f:
        json.dump(final_enriched_data, f, ensure_ascii=False, indent=2)

    print(f"\n\n🎉 Arricchimento dati completato! File salvato in: {config['output_enriched_file']}")

if __name__ == "__main__":
    app_config, app_model = load_config()
    run_enrichment(app_config, app_model)