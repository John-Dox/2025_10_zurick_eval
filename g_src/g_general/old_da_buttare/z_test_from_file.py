# g_src/g_general/8_test_from_file.py

import os
import sys
import time

# Logica per aggiungere il percorso radice al sys.path
script_dir = os.path.dirname(__file__)
proj_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

from g_src.g_general.config import load_config_and_clients
from g_src.g_general.utils import (
    preprocess_query_for_ordinals,
    analyze_query_for_rag,
    handle_structural_query,
    run_rag_search,
    generate_response
)
from g_src.g_general.utils_exporter import export_to_word

def load_questions(file_path):
    """Carica le domande da un file di testo, ignorando commenti e righe vuote."""
    questions = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            stripped_line = line.strip()
            if stripped_line and not stripped_line.startswith('#'):
                questions.append(stripped_line)
    return questions

def main():
    """
    Esegue un ciclo di test non interattivo leggendo le domande da un file,
    simulando il comportamento di un utente per ogni domanda.
    """
    print("*"*20 + " AVVIO TEST DA FILE " + "*"*20)
    
    try:
        config, clients, all_docs_structures, all_docs_summaries, _ = load_config_and_clients()
    except Exception as e:
        print(f"\n❌ ERRORE CRITICO: Impossibile inizializzare l'ambiente. {e}")
        return

    questions_file_path = os.path.join(proj_root, 'g_src', 'd_domande', 'domande.txt')
    if not os.path.exists(questions_file_path):
        print(f"❌ ERRORE: File domande non trovato a '{questions_file_path}'")
        return
    
    questions = load_questions(questions_file_path)
    print(f"\n✅ Trovate {len(questions)} domande da testare.")
    
    session_log = []
    
    for i, user_input_original in enumerate(questions):
        print("\n" + "="*80)
        print(f"▶️ ESEGUO DOMANDA #{i+1}/{len(questions)}: '{user_input_original}'")
        print("="*80)
        
        start_time = time.time()
        
        current_turn_data = {'question': user_input_original}
        
        model_aliases = {"@flash": "default_generator", "@gpt": "gpt", "@pro": "pro"}
        domanda_pulita = user_input_original
        model_override_key = None
        for alias, key in model_aliases.items():
            if alias in domanda_pulita.lower():
                model_override_key = key
                domanda_pulita = domanda_pulita.replace(alias, "").strip()
                print(f"⚙️  Override modello rilevato: {key.upper()}")
                break

        preprocessed_query = preprocess_query_for_ordinals(domanda_pulita)
        analysis = analyze_query_for_rag(clients["gemini_models"]["router"], config["models"]["router"], preprocessed_query)
        current_turn_data['analysis'] = analysis

        final_answer = None
        path_taken = None

        if analysis.get('intent') == 'ricerca_strutturale':
            path_taken = 'structural_query'
            print("-> Percorso scelto: Ricerca Strutturale")
            final_answer = handle_structural_query(analysis, all_docs_structures)
        else:
            path_taken = 'rag'
            print("-> Percorso scelto: Ricerca RAG")
            retrieved_hits = run_rag_search(clients, config, preprocessed_query, analysis)
            
            if not retrieved_hits:
                path_taken = 'fallback'
                final_answer = "🚫 NESSUNA INFORMAZIONE TROVATA."
            else:
                # --- CORREZIONE CHIAVE: SALVIAMO I CHUNK NEL LOG ---
                current_turn_data['context_chunks'] = retrieved_hits
                # ----------------------------------------------------
                
                contesto_chunks_str = "\n\n".join([f"Fonte: [{hit.payload.get('document_title', 'N/D')}] Art. {hit.payload.get('articolo')}, Comma {hit.payload.get('comma')}.\nTesto: {hit.payload.get('testo_originale_comma', '')}" for hit in retrieved_hits[:5]])
                
                model_to_use = model_override_key or 'default_generator'
                final_answer = generate_response(clients, config, contesto_chunks_str, preprocessed_query, model_to_use)

        current_turn_data['path_taken'] = path_taken
        current_turn_data['final_answer'] = final_answer
        session_log.append(current_turn_data)

        print("\n" + "-"*30 + " RISPOSTA GENERATA " + "-"*30)
        print(final_answer)
        print("-" * 80)
        print(f"⏱️ Tempo di esecuzione: {time.time() - start_time:.2f}s")

    print("\n" + "*"*20 + " TEST DA FILE COMPLETATO " + "*"*20)

    if session_log:
        save_choice = input("\nVuoi salvare il log completo di questa sessione di test in un file Word? (s/n): ").lower()
        if save_choice == 's':
            export_to_word(session_log, proj_root)
            print("✅ Report salvato con successo.")

if __name__ == "__main__":
    main()