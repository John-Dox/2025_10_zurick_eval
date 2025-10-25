import os
import re
import json
import time
import pypandoc
import google.generativeai as genai
from dotenv import load_dotenv

# --- 1. CONFIGURAZIONE ---
def load_config():
    """Carica le configurazioni e inizializza i client per il processo della Costituzione."""
    proj_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    load_dotenv(os.path.join(proj_root, "a_chiavi", ".env"))
    
    output_dir = os.path.join(proj_root, "d_outputs", "00_structured", "a_cost")
    
    config = {
        "model": "gemini-2.5-pro",
        "model_summary": "gemini-2.5-pro",
        "input_structure_json": os.path.join(output_dir, "cost_structure.json"),
        "input_text_docx": os.path.join(proj_root, "b_testi", "a_cost", "cost_2023_22_10_testo.docx"),
        "output_dir": output_dir,
        "output_summaries_json": os.path.join(output_dir, "cost_summaries.json"),
        "output_enriched_progress_json": os.path.join(output_dir, "cost_enriched_progress.json"),
        "output_enriched_final_json": os.path.join(output_dir, "cost_enriched_data.json")
    }
    
    try:
        os.makedirs(config["output_dir"], exist_ok=True)
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        clients = {
            "default": genai.GenerativeModel(config["model"]),
            "summary": genai.GenerativeModel(config["model_summary"])
        }
        print("✅ Configurazione caricata e client AI inizializzato.")
        return config, clients
    except Exception as e:
        print(f"❌ ERRORE CRITICO in fase di inizializzazione: {e}")
        exit()

# --- 2. FUNZIONI DI UTILITÀ ---

def extract_articles_from_docx(file_path: str) -> dict:
    print(f"📄 Estrazione testo degli articoli da: {os.path.basename(file_path)}")
    try:
        full_text = pypandoc.convert_file(file_path, 'plain', format='docx')
        
        # --- RIGA DI CORREZIONE DA AGGIUNGERE ---
        full_text = full_text.replace('\r\n', '\n')
        # ----------------------------------------
        
        if not full_text or not full_text.strip():
            print("⚠️ ATTENZIONE: pypandoc ha restituito un testo vuoto. Il file DOCX potrebbe essere vuoto, corrotto o c'è un problema con pandoc.")
            return {}
        # --- FINE AGGIUNTA ---

    except Exception as e:
        print(f"❌ ERRORE PANDOC durante la lettura del file di testo: {e}")
        return {}
    
    # Il resto della funzione rimane invariato...
    pattern = r'(?m)^(Art\.\s*(\d+)|([IVXLCDM]+))$'
    matches = list(re.finditer(pattern, full_text))
    
    articles_map = {}
    for i, match in enumerate(matches):
        article_id_raw = match.group(0)
        article_id = article_id_raw.replace("Art.", "").strip()
        start_pos = match.end()
        end_pos = matches[i+1].start() if i + 1 < len(matches) else len(full_text)
        article_text = full_text[start_pos:end_pos].strip()
        articles_map[article_id] = article_text
        
    print(f"✅ Estratti {len(articles_map)} articoli/disposizioni dal testo.")
    return articles_map

def find_summary_nodes(nodes: list) -> list:
    leaf_nodes = []
    for node in nodes:
        if node.get("articles") and len(node["articles"]) > 0:
            leaf_nodes.append(node)
        if node.get("children"):
            leaf_nodes.extend(find_summary_nodes(node["children"]))
    return leaf_nodes

def get_summary_for_node(node_title: str, progress_data: dict) -> str | None:
    """Recupera un riassunto già generato dai dati di progresso."""
    return progress_data.get("summaries", {}).get(node_title)

# --- 3. LOGICA PRINCIPALE ---

def run_enrichment_pipeline():
    config, clients = load_config()

    try:
        with open(config["input_structure_json"], 'r', encoding='utf-8') as f:
            structure_data = json.load(f)
        articles_text_map = extract_articles_from_docx(config["input_text_docx"])
    except FileNotFoundError as e:
        print(f"❌ ERRORE: File di input non trovato: {e}")
        return
        
    if not articles_text_map:
        print("❌ Impossibile procedere senza il testo degli articoli.")
        return

    try:
        with open(config["output_summaries_json"], 'r', encoding='utf-8') as f:
            summaries_data = json.load(f)
        print("📄 File di progresso dei riassunti caricato.")
    except FileNotFoundError:
        summaries_data = {"summaries": {}}
        print("ℹ️  Nessun file di progresso dei riassunti trovato. Ne verrà creato uno nuovo.")

    print("\n--- FASE A: Generazione Riassunti dei Nodi ---")
    nodes_to_summarize = find_summary_nodes(structure_data.get("structure", []))
    
    for node in nodes_to_summarize:
        node_title = node["title"]
        if get_summary_for_node(node_title, summaries_data):
            print(f"  -> Riassunto per '{node_title}' già presente. Salto.")
            continue

        print(f"  -> Generazione riassunto per: '{node_title}'...")
        full_node_text = "\n\n".join(
            f"Testo Articolo {art_id}:\n{articles_text_map.get(art_id, '')}"
            for art_id in node["articles"]
            if articles_text_map.get(art_id)
        )

        if not full_node_text.strip():
            print(f"     -> ATTENZIONE: Nessun testo trovato per gli articoli di questo nodo. Salto.")
            continue

        prompt_summary = (
            f"Sei un giurista esperto. Riassumi il contenuto e lo scopo degli articoli di legge forniti di seguito, che appartengono alla sezione '{node_title}' della Costituzione Italiana. "
            "Il riassunto deve essere conciso, chiaro e cogliere l'essenza giuridica delle norme. Concentrati sul principio guida della sezione.\n\n"
            f"--- INIZIO TESTO DA RIASSUMERE ---\n{full_node_text}\n--- FINE TESTO ---"
        )
        
        try:
            response = clients["summary"].generate_content(prompt_summary)
            new_summary = response.text
            summaries_data["summaries"][node_title] = new_summary
            with open(config["output_summaries_json"], 'w', encoding='utf-8') as f:
                json.dump(summaries_data, f, ensure_ascii=False, indent=2)
            print(f"     ✅ Riassunto generato e salvato.")
            time.sleep(2)
        except Exception as e:
            print(f"     ❌ ERRORE durante la generazione del riassunto per '{node_title}': {e}")
    
    print("✅ FASE A completata.")

    print("\n--- FASE B: Arricchimento Commi con Keyword ---")
    
    try:
        with open(config["output_enriched_progress_json"], 'r', encoding='utf-8') as f:
            enriched_data = json.load(f)
        print(f"📄 File di progresso di arricchimento caricato. {len(enriched_data)} record presenti.")
    except FileNotFoundError:
        enriched_data = []
        print("ℹ️  Nessun file di progresso di arricchimento trovato. Ne verrà creato uno nuovo.")

    processed_articles = {record['articolo'] for record in enriched_data}
    article_to_nodetitle_map = {art_id: node["title"] for node in nodes_to_summarize for art_id in node["articles"]}
    all_articles_ids = list(articles_text_map.keys())

    for i, article_id in enumerate(all_articles_ids):
        if article_id in processed_articles:
            print(f"  -> Articolo {article_id} già processato. Salto.")
            continue

        print(f"  -> Processo Articolo {article_id} ({i+1}/{len(all_articles_ids)})")
        article_text = articles_text_map.get(article_id)

        if not article_text:
            print(f"     -> ATTENZIONE: Testo per l'articolo {article_id} non trovato. Salto.")
            continue
        
        prompt_commi = (
            "Sei un assistente legale. Dividi il seguente testo di un articolo di legge in commi numerati. Ogni comma deve essere un oggetto JSON separato in una lista. "
            "Ogni oggetto deve avere due chiavi: 'comma' (il numero del comma come stringa, es. '1', '2') e 'testo' (il testo completo del comma).\n"
            "Restituisci SOLO l'array JSON valido, senza testo o commenti, racchiuso in ```json ... ```.\n\n"
            f"--- TESTO ARTICOLO ---\n{article_text}"
        )

        try:
            response_commi = clients["default"].generate_content(prompt_commi)
            cleaned_json_text = re.search(r'```json\s*(\[[\s\S]*?\])\s*```', response_commi.text)
            commi_list = json.loads(cleaned_json_text.group(1) if cleaned_json_text else response_commi.text)

            temp_article_chunks = []
            for comma_item in commi_list:
                comma_num = comma_item.get("comma")
                comma_text = comma_item.get("testo")
                
                parent_node_title = article_to_nodetitle_map.get(article_id, "Contesto Generale")
                context_summary = summaries_data.get("summaries", {}).get(parent_node_title, "")

                prompt_keywords = (
                    "Estrai da 5 a 10 parole chiave o brevi frasi chiave (massimo 3 parole) dal seguente testo di un comma di legge. "
                    "Le parole chiave devono catturare gli aspetti legali, i soggetti e gli oggetti principali della norma. Considera il contesto generale fornito.\n"
                    f"**Contesto Generale della Sezione ({parent_node_title}):**\n{context_summary}\n\n"
                    f"**Testo del Comma:**\n{comma_text}\n\n"
                    "Restituisci SOLO un array JSON di stringhe."
                )
                
                response_keywords = clients["default"].generate_content(prompt_keywords)
                cleaned_kw_text = re.search(r'```json\s*(\[[\s\S]*?\])\s*```', response_keywords.text)
                keywords = json.loads(cleaned_kw_text.group(1) if cleaned_kw_text else response_keywords.text)
                
                temp_article_chunks.append({
                    "articolo": article_id,
                    "comma": comma_num,
                    "testo_originale_comma": comma_text,
                    "keywords": keywords
                })
                print(f"     - Comma {comma_num} processato.")
            
            enriched_data.extend(temp_article_chunks)
            with open(config["output_enriched_progress_json"], 'w', encoding='utf-8') as f:
                json.dump(enriched_data, f, ensure_ascii=False, indent=2)
            print(f"     ✅ Progresso per Art. {article_id} salvato.")

            time.sleep(2)
        except Exception as e:
            print(f"     ❌ ERRORE durante il processo dell'articolo {article_id}: {e}")
            print("         Interruzione del processo. Rilanciare per riprendere.")
            return

    os.rename(config["output_enriched_progress_json"], config["output_enriched_final_json"])

    print("\n🎉 Arricchimento completato!")
    print(f"✅ Creati {len(enriched_data)} record arricchiti.")
    print(f"📁 File finale salvato in: {config['output_enriched_final_json']}")

# --- 4. AVVIO ---
if __name__ == "__main__":
    run_enrichment_pipeline()