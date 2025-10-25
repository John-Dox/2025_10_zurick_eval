import os
import re
import sys
import json
from qdrant_client import models
import google.generativeai as genai
from openai import OpenAI

def preprocess_query_for_ordinals(query: str) -> str:
    """
    Esegue un pre-processing leggero per aiutare l'AI Router,
    convertendo solo le parole ordinali più comuni in numeri arabi.
    """
    ordinals_map = { "primo": "1", "secondo": "2", "terzo": "3", "quarto": "4", "quinto": "5", "sesto": "6", "settimo": "7", "ottavo": "8", "nono": "9", "decimo": "10", "prima": "1", "seconda": "2" }
    processed_query = query
    for word, number in ordinals_map.items():
        processed_query = re.sub(rf"\b{word}\b", number, processed_query, flags=re.IGNORECASE)
    return processed_query

def clean_json_from_text(text: str) -> str:
    """Estrae una stringa JSON pulita da un blocco di testo."""
    match = re.search(r'```json\s*(\{[\s\S]*?\})\s*```', text)
    if match: return match.group(1)
    start, end = text.find('{'), text.rfind('}')
    return text[start:end+1] if start != -1 and end != -1 else "{}"

def analyze_query_for_rag(router_client, model_name, user_query: str) -> dict:
    """Analizza la query dell'utente per estrarre l'intent e le entità."""
    prompt = ( "Sei un analista di query legali. Il tuo compito è analizzare la domanda di un utente e classificarla, estraendo le entità chiave. Restituisci un oggetto JSON.\n\n" "**INTENT POSSIBILI:**\n" "- `ricerca_contenuto`: Domande sul contenuto di uno o più articoli (es. 'cosa dice l'articolo 5?', 'spiega gli articoli 3 e 4 della Costituzione').\n" "- `ricerca_strutturale`: Domande sulla struttura di un documento (es. 'quanti capi ha la parte prima del regolamento?', 'qual è il titolo del capo I?', 'a quale parte appartiene l'art. 50?').\n" "- `ricerca_generale`: Domande tematiche che non specificano articoli o strutture (es. 'parlami delle immunità parlamentari').\n\n" "**ENTITIES DA ESTRARRE:**\n" "- `documento`: Il nome del documento (es. 'costituzione', 'regolamento'). Se non specificato, non estrarre nulla.\n" "- `articolo`: Il numero dell'articolo o una lista di numeri (es. '5', ['3', '4'], 'V').\n" "- `nome_sezione`: Il nome o numero di una sezione (es. 'parte prima', 'principi fondamentali', 'capo 1', 'capo x', 'titolo 2').\n\n" "**ESEMPI:**\n" "- Domanda: 'spiega l'art. 1 della costituzione' -> intent: 'ricerca_contenuto', entities: {'articolo': '1', 'documento': 'costituzione'}\n" "- Domanda: 'quanti titoli ha la parte seconda della costituzione?' -> intent: 'ricerca_strutturale', entities: {'nome_sezione': 'parte seconda', 'documento': 'costituzione'}\n" "- Domanda: 'cosa dice l'art. 5 del regolamento?' -> intent: 'ricerca_contenuto', entities: {'articolo': '5', 'documento': 'regolamento'}\n" "- Domanda: 'parlami della libertà di stampa' -> intent: 'ricerca_generale', entities: {}\n" f"**Analizza la seguente domanda e produci SOLO l'oggetto JSON:**\n**Domanda Utente:** \"{user_query}\"" )
    try:
        response = router_client.generate_content(prompt)
        return json.loads(clean_json_from_text(response.text))
    except Exception as e:
        print(f"⚠️ Errore durante l'analisi della query: {e}")
        return {"intent": "ricerca_generale", "entities": {}}

def handle_structural_query(analysis: dict, all_structures: list) -> str | None:
    """Gestisce le query strutturali navigando le strutture canoniche."""
    if analysis.get("intent") != 'ricerca_strutturale':
        return None

    entities = analysis.get("entities", {})
    doc_entity = entities.get("documento")
    article_entity = str(entities.get("articolo")) if entities.get("articolo") else None
    section_entity = entities.get("nome_sezione")

    doc_type_map = {"costituzione": "costituzione", "regolamento": "regolamento_parlamentare"}
    target_doc_type = doc_type_map.get(doc_entity.lower()) if doc_entity else None
    
    docs_to_search = [doc for doc in all_structures if not target_doc_type or doc.get('document_type') == target_doc_type]

    for doc in docs_to_search:
        doc_title = doc.get('document_title', 'Sconosciuto')
        
        if article_entity:
            path_to_article = []
            def find_article_path_recursive(nodes, current_path):
                for node in nodes:
                    articles_as_str = [str(a) for a in node.get("articles", [])]
                    if article_entity in articles_as_str:
                        path_to_article.extend(current_path + [node.get("title")])
                        return True
                    if node.get("children") and find_article_path_recursive(node["children"], current_path + [node.get("title")]):
                        return True
                return False

            if find_article_path_recursive(doc.get("structure", []), []):
                return f"L'articolo {article_entity} si trova nel documento '{doc_title}' all'interno del percorso: {' -> '.join(path_to_article)}."

        if section_entity:
            search_term_norm = section_entity.lower().replace(" ", "").replace("-", "")
            def normalize_title_with_romans(title: str) -> str:
                roman_map = {'i': '1', 'ii': '2', 'iii': '3', 'iv': '4', 'v': '5', 'vi': '6', 'vii': '7', 'viii': '8', 'ix': '9', 'x': '10'}
                title_lower = title.lower()
                for roman, arabic in roman_map.items():
                    title_lower = re.sub(rf'\b{roman}\b', arabic, title_lower)
                return title_lower.replace(" ", "").replace("-", "")

            def find_node_by_title_recursive(nodes, name_to_find):
                for node in nodes:
                    title_norm = normalize_title_with_romans(node.get("title", ""))
                    if name_to_find in title_norm:
                        return node
                    if node.get("children"):
                        found = find_node_by_title_recursive(node["children"], name_to_find)
                        if found: return found
                return None
                
            found_node = find_node_by_title_recursive(doc.get("structure", []), search_term_norm)
            if found_node:
                return f"Nel documento '{doc_title}', la sezione trovata per '{section_entity}' è: \"{found_node.get('title')}\"."

    if article_entity:
        doc_info = f"nel documento '{doc_entity}'" if doc_entity else "in nessun documento"
        return f"Non è stato possibile trovare l'articolo {article_entity} {doc_info}."
    if section_entity:
        doc_info = f"nel documento '{doc_entity}'" if doc_entity else "in nessun documento"
        return f"Nessuna sezione corrispondente a '{section_entity}' è stata trovata {doc_info}."
    return "Query strutturale non riconosciuta."

def rerank_results(search_results: list, user_query: str) -> list:
    """Aggiunge un bonus allo score se le parole della query sono nelle keyword."""
    query_words = set(re.findall(r'\b\w{3,}\b', user_query.lower()))
    reranked_results = []
    for hit in search_results:
        payload_keywords = hit.payload.get("keywords", []) or []
        bonus_score = sum(0.01 for kw in payload_keywords for word in query_words if word in kw.lower())
        final_score = hit.score + bonus_score
        reranked_results.append((final_score, hit))
    reranked_results.sort(key=lambda x: x[0], reverse=True)
    return [hit for score, hit in reranked_results]

def run_rag_search(clients, config, domanda_pulita, analysis):
    """Esegue la ricerca vettoriale su Qdrant, applicando filtri e re-ranking."""
    try:
        entities = analysis.get("entities", {})
        query_filter = None
        must_conditions = []
        doc_entity = entities.get("documento")
        if doc_entity:
            doc_type_map = {"costituzione": "costituzione", "regolamento": "regolamento_parlamentare"}
            if doc_entity.lower() in doc_type_map:
                must_conditions.append(models.FieldCondition(key="document_type", match=models.MatchValue(value=doc_type_map[doc_entity.lower()])))
        if "articolo" in entities:
            article_values = entities["articolo"]
            if isinstance(article_values, list):
                should_conditions = [models.FieldCondition(key="articolo", match=models.MatchValue(value=str(val))) for val in article_values]
                must_conditions.append(models.Filter(should=should_conditions))
            else:
                must_conditions.append(models.FieldCondition(key="articolo", match=models.MatchValue(value=str(article_values))))
        
        if must_conditions:
            query_filter = models.Filter(must=must_conditions)
            print(f"⚙️ Filtro RAG attivato. Condizioni: {entities}")
        else:
            print("⚙️ Ricerca RAG Tematica (Vettoriale Pura) attivata.")

        embedding_model = f'models/{config["gemini_embedding_model"]}'
        embedding_result = genai.embed_content(model=embedding_model, content=[domanda_pulita], task_type="RETRIEVAL_QUERY")
        query_vector = embedding_result['embedding'][0]
        
        initial_results = clients["qdrant"].search(
            collection_name=config["qdrant_collection_name"], 
            query_vector=query_vector, 
            query_filter=query_filter, 
            limit=20
        )
        
        print("🔍 Eseguo re-ranking dei risultati basato su keyword...")
        reranked_hits = rerank_results(initial_results, domanda_pulita)
        return reranked_hits

    except Exception as e:
        print(f"❌ ERRORE durante la ricerca RAG: {e}")
        return []

def generate_response(clients, config, context: str, domanda: str, model_key: str, system_prompt: str) -> str:
    """
    Genera una risposta utilizzando un modello LLM, basandosi su un contesto,
    una domanda e un prompt di sistema fornito dinamicamente.
    """
    try:
        model_to_use_name = config["models"][model_key]
        
        if model_key == "gpt":
            model_instance = clients["openai_generator"]
            response = model_instance.chat.completions.create(
                model=model_to_use_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"**Contesto:**\n{context}\n\n**Domanda:**\n{domanda}"}
                ]
            )
            return response.choices[0].message.content
        
        model_instance = clients["gemini_models"].get(model_key)
        if model_instance:
             final_prompt = f"{system_prompt}\n\n**Contesto:**\n{context}\n\n**Domanda:**\n{domanda}"
             response = model_instance.generate_content(final_prompt)
             return response.text
        else:
            return f"⚠️ Errore: Modello '{model_key}' non trovato."

    except Exception as e:
        print(f"❌ ERRORE CRITICO in generate_response (modello: {model_key}): {e}")
        return f"⚠️ Si è verificato un errore durante la generazione della risposta."
    
def confirm_execution(settings: dict) -> bool:
    """Mostra un riepilogo delle impostazioni e chiede conferma all'utente."""
    print("\n--- ATTENZIONE: CONFERMA ESECUZIONE SCRIPT ---")
    print("Lo script sta per essere eseguito con le seguenti impostazioni:")
    for key, value in settings.items():
        print(f"  - {key}: {value}")
    print("-" * 45)
    
    try:
        confirm = input("Per confermare, premere 's' e Invio. Qualsiasi altro tasto per annullare: ").lower()
        if confirm == 's':
            print("Confermato. Avvio dello script...")
            return True
        else:
            print("Esecuzione annullata dall'utente.")
            return False
    except KeyboardInterrupt:
        print("\nEsecuzione annullata dall'utente.")
        sys.exit(0)