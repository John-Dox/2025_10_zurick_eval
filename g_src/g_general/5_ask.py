import os
import sys
import time
import re

# Logica per aggiungere il percorso radice al sys.path
script_dir = os.path.dirname(__file__)
proj_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

# Import corretti
from g_src.g_general.config import load_config_and_clients
from g_src.g_general.utils import (
    preprocess_query_for_ordinals,
    analyze_query_for_rag,
    handle_structural_query,
    run_rag_search,
    generate_response
)
from g_src.g_general.utils_exporter import export_to_word

def select_task(config: dict) -> str | None:
    """
    Mostra un menu per selezionare il compito (prompt) e restituisce la chiave scelta.
    """
    prompts = config.get("prompts", {})
    if not prompts:
        print("⚠️ Nessun prompt di sistema trovato. L'applicazione non può continuare.")
        return None
    
    prompt_keys = list(prompts.keys())
    print("\n--- Selezione del Compito ---")
    print("Scegli la 'personalità' che l'assistente deve assumere:")
    for i, key in enumerate(prompt_keys):
        print(f"  [{i+1}] {key.replace('_', ' ').title()}")
    
    while True:
        try:
            choice = int(input(f"Inserisci il numero del compito (1-{len(prompt_keys)}): "))
            if 1 <= choice <= len(prompt_keys):
                return prompt_keys[choice - 1]
            else:
                print("Scelta non valida. Riprova.")
        except (ValueError, IndexError):
            print("Input non valido. Inserisci solo il numero corrispondente.")

def select_model(config: dict) -> str:
    """
    Mostra un menu per selezionare il modello di generazione e restituisce la chiave scelta.
    """
    models = config.get("models", {})
    # Filtriamo solo i modelli di generazione, escludendo il router
    generator_models = {k: v for k, v in models.items() if k != 'router'}
    model_keys = list(generator_models.keys())

    print("\n--- Selezione del Modello di Generazione ---")
    for i, key in enumerate(model_keys):
        print(f"  [{i+1}] {key.title()} ({models[key]})")

    while True:
        try:
            choice = int(input(f"Inserisci il numero del modello (1-{len(model_keys)}): "))
            if 1 <= choice <= len(model_keys):
                return model_keys[choice - 1]
            else:
                print("Scelta non valida. Riprova.")
        except (ValueError, IndexError):
            print("Input non valido. Inserisci solo il numero corrispondente.")


def main_cycle(config, clients, all_structures, all_summaries, all_chunks):
    """
    Gestisce il ciclo principale di interazione multi-documento e multi-compito.
    """
    selected_task_key = select_task(config)
    if not selected_task_key:
        return
    
    system_prompt = config["prompts"][selected_task_key]
    selected_model_key = select_model(config)
    
    print(f"\n✅ Modalità '{selected_task_key}' attivata con il modello '{selected_model_key}'.")
    print("Puoi iniziare a fare domande. Digita '/task' per cambiare compito/modello, o 'exit' per uscire.")

    last_interaction_info = {}
    session_log = []

    while True:
        user_input_original = input("\n\n💬 Inserisci la tua domanda: ").strip()
        
        if user_input_original.lower() == 'exit':
            if session_log:
                save_choice = input("Vuoi salvare il log di questa sessione in un file Word? (s/n): ").lower()
                if save_choice == 's':
                    export_to_word(session_log, proj_root)
            print("Uscita dal programma.")
            break
        
        if user_input_original.lower() == '/task':
            selected_task_key = select_task(config)
            system_prompt = config["prompts"][selected_task_key]
            selected_model_key = select_model(config)
            print(f"\n✅ Modalità '{selected_task_key}' attivata con il modello '{selected_model_key}'.")
            last_interaction_info = {}
            continue

        start_time = time.time()
        lower_input = user_input_original.lower()
        current_turn_data = {'question': user_input_original}
        
        is_follow_up = bool(re.search(r'\b(sintetico|dettagliato)\b', lower_input))
        
        if is_follow_up:
            if not last_interaction_info:
                print("⚠️ Nessun contesto precedente disponibile per il follow-up. Fai prima una domanda.")
                continue

            print("-> Riconosciuta come domanda di FOLLOW-UP.")
            current_turn_data['path_taken'] = 'follow_up'
            
            model_override_key = None
            model_aliases = {"@flash": "default_generator", "@gpt": "gpt", "@pro": "pro"}
            for alias, key in model_aliases.items():
                if alias in lower_input:
                    model_override_key = key
                    print(f"⚙️  Override modello per follow-up rilevato: {key.upper()}")
                    break
            
            stile = "sintetico" if "sintetico" in lower_input else "dettagliato"
            print(f"⚙️  Stile Follow-up: '{stile}'.")
            
            original_question = last_interaction_info.get("domanda", "")
            rag_context = last_interaction_info.get("contesto")
            metadata_answer = last_interaction_info.get("risposta")

            current_turn_data['analysis'] = {'style': stile}
            current_turn_data['original_question'] = original_question

            followup_prompt = ""
            context_for_generation = ""

            if metadata_answer:
                followup_prompt = f"Rielabora la seguente risposta in modo più {stile}:\n\nRisposta Originale: \"{metadata_answer}\"\n\nDomanda Originale: \"{original_question}\""
                context_for_generation = f"La domanda originale era: {original_question}"
            elif rag_context:
                followup_prompt = f"Rispondi in modo più {stile} e articolato alla seguente domanda:\n\n{original_question}"
                context_for_generation = rag_context
            else:
                 print("⚠️ Errore di memoria: stato dell'interazione non valido.")
                 continue

            final_model_to_use = model_override_key or selected_model_key
            response_text = generate_response(
                clients, config, context_for_generation, followup_prompt, 
                model_key=final_model_to_use, 
                system_prompt=system_prompt
            )
            
            model_full_name = config['models'].get(final_model_to_use, "Sconosciuto")
            print(f"\n✅ Risposta (Follow-up con Modello: {final_model_to_use.upper()} → {model_full_name}):\n" + "="*50)
            print(response_text)
            
            current_turn_data['final_answer'] = response_text
            session_log.append(current_turn_data)
            print("="*50 + f"\n⏱️ Tempo Totale Follow-up: {time.time() - start_time:.2f}s")
            continue

        print("-> Riconosciuta come domanda NUOVA.")
        last_interaction_info = {}
        
        domanda_pulita = user_input_original
        model_override_key = None
        model_aliases = {"@flash": "default_generator", "@gpt": "gpt", "@pro": "pro"}
        for alias, key in model_aliases.items():
            if alias in lower_input:
                model_override_key = key
                domanda_pulita = domanda_pulita.replace(alias, "").strip()
                print(f"⚙️  Override modello rilevato: userai '{key.upper()}' per questa domanda.")
                break
        
        final_model_to_use = model_override_key or selected_model_key

        preprocessed_query = preprocess_query_for_ordinals(domanda_pulita)
        analysis = analyze_query_for_rag(clients["gemini_models"]["router"], config["models"]["router"], preprocessed_query)
        current_turn_data['analysis'] = analysis

        final_answer = None
        path_taken = None

        if analysis.get('intent') == 'ricerca_strutturale':
            path_taken = 'structural_query'
            final_answer = handle_structural_query(analysis, all_structures)
            print(f"\n✅ Risposta (da Query Strutturale):")
        else:
            retrieved_hits = run_rag_search(clients, config, preprocessed_query, analysis)
            
            if not retrieved_hits:
                path_taken = 'fallback'
                final_answer = "🚫 NESSUNA INFORMAZIONE TROVATA."
            else:
                path_taken = 'rag'
                current_turn_data['context_chunks'] = retrieved_hits
                
                print("\n" + "*"*25 + " CONTESTO RECUPERATO (RAG) " + "*"*25)
                for i, hit in enumerate(retrieved_hits[:15]):
                    fonte_str = (
                        f"Fonte: [{hit.payload.get('document_title', 'N/D')}] "
                        f"Art. {hit.payload.get('articolo', 'N/A')}, "
                        f"Comma {hit.payload.get('comma', 'N/A')} "
                        f"(Score: {hit.score:.4f})"
                    )
                    print(f"--- [Chunk #{i+1}] {fonte_str}")
                print("*"*73 + "\n")
                
                contesto_riassunti_list = []
                unique_titles_in_order = []
                processed_titles = set()
                for hit in retrieved_hits:
                    for titolo in [hit.payload.get(f'livello_{i}_title') for i in range(3, 0, -1)]:
                        if titolo and titolo not in processed_titles:
                            unique_titles_in_order.append(titolo)
                            processed_titles.add(titolo)
                for titolo in unique_titles_in_order:
                    if all_summaries.get(titolo):
                        print(f"✅ Riassunto per '{titolo}' aggiunto al contesto.")
                        riassunto = f"**Contesto dalla Sezione ({titolo}):**\n{all_summaries[titolo]}"
                        contesto_riassunti_list.append(riassunto)
                
                contesto_riassunti_str = "\n\n---\n\n".join(contesto_riassunti_list) + ("\n\n---\n\n" if contesto_riassunti_list else "")
                contesto_chunks_str = "\n\n---\n\n".join([f"Fonte: [{hit.payload.get('document_title', 'N/D')}] Art. {hit.payload.get('articolo')}, Comma {hit.payload.get('comma')}.\nTesto: {hit.payload.get('testo_originale_comma', '')}" for hit in retrieved_hits])
                final_context_for_llm = f"{contesto_riassunti_str}**Estratti Rilevanti (Ordinati per Pertinenza):**\n{contesto_chunks_str}"

                final_answer = generate_response(
                    clients, config, final_context_for_llm, preprocessed_query, 
                    model_key=final_model_to_use, 
                    system_prompt=system_prompt
                )
                
                model_full_name = config['models'].get(final_model_to_use, "Sconosciuto")
                print(f"\n✅ Risposta (da RAG - Compito: '{selected_task_key}', Modello: '{model_full_name}'):")

        print("="*50)
        print(final_answer if final_answer is not None else "Nessuna risposta generata.")
        print("="*50)
        
        current_turn_data['path_taken'] = path_taken
        current_turn_data['final_answer'] = final_answer
        session_log.append(current_turn_data)
        last_interaction_info = {"domanda": preprocessed_query, "contesto": final_context_for_llm if path_taken == 'rag' else None, "risposta": final_answer if path_taken == 'structural_query' else None}
        
        print(f"⏱️ Tempo Totale: {time.time() - start_time:.2f}s")
        
if __name__ == "__main__":
    app_config, app_clients, all_docs_structures, all_docs_summaries, all_docs_chunks = load_config_and_clients()
    main_cycle(app_config, app_clients, all_docs_structures, all_docs_summaries, all_docs_chunks)