import os
import re
import json
import time
import pypandoc
import google.generativeai as genai
from dotenv import load_dotenv

# --- 1. CONFIGURAZIONE ---
def load_config():
    """Carica le configurazioni per il processo di generazione dei riassunti del Regolamento."""
    proj_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    load_dotenv(os.path.join(proj_root, "a_chiavi", ".env"))
    
    output_dir = os.path.join(proj_root, "d_outputs", "00_structured", "b_regcam")
    
    config = {
        "model_summary": "gemini-2.5-pro",
        "input_structure_json": os.path.join(output_dir, "regcam_structure.json"),
        "input_text_docx": os.path.join(proj_root, "b_testi", "b_regcam", "regcam_testo.docx"),
        "output_summaries_json": os.path.join(output_dir, "regcam_summaries.json"),
        # --- CLAUSOLA DI TEST ---
        "max_summaries_to_generate": 3
    }
    
    try:
        os.makedirs(output_dir, exist_ok=True)
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        client = genai.GenerativeModel(config["model_summary"])
        print("✅ Configurazione caricata e client AI inizializzato.")
        return config, client
    except Exception as e:
        print(f"❌ ERRORE CRITICO in fase di inizializzazione: {e}")
        exit()

# --- 2. FUNZIONI DI UTILITÀ ---

def extract_articles_from_docx(file_path: str) -> dict:
    """Estrae il testo degli articoli dal DOCX del Regolamento."""
    print(f"📄 Estrazione testo degli articoli da: {os.path.basename(file_path)}")
    try:
        full_text = pypandoc.convert_file(file_path, 'plain', format='docx')
        full_text = full_text.replace('\r\n', '\n')

        # --- RIGHE DA AGGIUNGERE PER IL DEBUG ---
        print("\n--- INIZIO OUTPUT GREZZO PANDOC (REGOLAMENTO) ---")
        print(repr(full_text[:1000])) # Stampiamo i primi 1000 caratteri
        print("--- FINE OUTPUT GREZZO PANDOC (REGOLAMENTO) ---\n")
        # --- FINE RIGHE DA AGGIUNGERE ---

    except Exception as e:
        print(f"❌ ERRORE PANDOC: {e}")
        return {}
    
    # Pattern per trovare "Articolo [numero]"
    pattern = r'(?m)^ART\.\s+(\d+(?:-bis|-ter|-quater|-quinquies|-sexies)?)'
    matches = list(re.finditer(pattern, full_text, re.IGNORECASE))
    
    articles_map = {}
    for i, match in enumerate(matches):
        article_id = match.group(1)
        start_pos = match.start() # Includiamo "Articolo X" nel testo
        end_pos = matches[i+1].start() if i + 1 < len(matches) else len(full_text)
        article_text = full_text[start_pos:end_pos].strip()
        articles_map[article_id] = article_text
        
    print(f"✅ Estratti {len(articles_map)} articoli dal testo.")
    return articles_map

def find_leaf_nodes(nodes: list) -> list:
    """Funzione ricorsiva per trovare tutti i nodi 'foglia' (quelli con articoli)."""
    leaf_nodes = []
    for node in nodes:
        if node.get("articles") and len(node["articles"]) > 0:
            leaf_nodes.append(node)
        if node.get("children"):
            leaf_nodes.extend(find_leaf_nodes(node["children"]))
    return leaf_nodes

# --- 3. LOGICA PRINCIPALE ---

def generate_summaries():
    """Genera i riassunti per i Capi del Regolamento."""
    config, client = load_config()

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
        print(f"📄 File di progresso dei riassunti caricato ({len(summaries_data.get('summaries', []))} presenti).")
    except FileNotFoundError:
        summaries_data = {"summaries": {}}
        print("ℹ️  Nessun file di progresso trovato. Ne verrà creato uno nuovo.")

    print("\n--- Inizio Generazione Riassunti per il Regolamento ---")
    
    nodes_to_summarize = find_leaf_nodes(structure_data.get("structure", []))
    document_title = structure_data.get("document_title", "N/D")
    
    limit = config.get("max_summaries_to_generate")
    if limit is not None:
        print(f"⚠️ ATTENZIONE: Esecuzione in modalità TEST. Verranno generati al massimo {limit} riassunti.")
    
    generated_count = 0
    for node in nodes_to_summarize:
        if limit is not None and generated_count >= limit:
            print(f"\nℹ️ Limite di test ({limit}) raggiunto. Interruzione.")
            break

        node_title = node["title"]
        if node_title in summaries_data.get("summaries", {}):
            print(f"  -> Riassunto per '{node_title}' già presente. Salto.")
            continue

        print(f"  -> Generazione riassunto per: '{node_title}'...")
        generated_count += 1
        
        full_node_text = "\n\n".join(
            articles_text_map.get(art_id, '')
            for art_id in node["articles"]
            if articles_text_map.get(art_id)
        )

        if not full_node_text.strip():
            print(f"     -> ATTENZIONE: Nessun testo trovato per gli articoli di questo nodo. Salto.")
            continue

        # Utilizzo del prompt migliorato e definitivo
        prompt = (
            "Sei un giurista e un analista di testi normativi. Il tuo compito è leggere un insieme di articoli di legge e produrre un riassunto astratto e conciso del loro scopo collettivo.\n\n"
            "**CONTESTO:**\n"
            f"- Nome del Documento: {document_title}\n"
            f"- Titolo della Sezione da riassumere: {node_title}\n\n"
            "**ISTRUZIONI FONDAMENTALI:**\n"
            "1. **Principio Guida:** Il tuo obiettivo primario è identificare e articolare il principio giuridico o lo scopo fondamentale che unisce gli articoli forniti. Non fare un elenco dei contenuti di ogni articolo.\n"
            "2. **Sintesi e Astrazione:** Crea un paragrafo di 3-5 frasi che sia una sintesi astratta, non una semplice descrizione.\n"
            "3. **Output Diretto e Pulito:** La tua risposta deve contenere **SOLO ED ESCLUSIVAMENTE** il testo del riassunto. Non includere MAI frasi introduttive come 'Certamente, ecco il riassunto', 'In qualità di giurista', o qualsiasi altra forma di preambolo.\n\n"
            "**TESTO DEGLI ARTICOLI DA ANALIZZARE:**\n"
            f"{full_node_text}"
        )
        
        try:
            response = client.generate_content(prompt)
            new_summary = response.text.strip()
            summaries_data["summaries"][node_title] = new_summary
            
            with open(config["output_summaries_json"], 'w', encoding='utf-8') as f:
                json.dump(summaries_data, f, ensure_ascii=False, indent=2)
            print(f"     ✅ Riassunto generato e salvato.")
            time.sleep(2)
        except Exception as e:
            print(f"     ❌ ERRORE durante la generazione del riassunto per '{node_title}': {e}")
            break

    print("\n🎉 Processo di generazione riassunti terminato.")

# --- 4. AVVIO ---
if __name__ == "__main__":
    generate_summaries()