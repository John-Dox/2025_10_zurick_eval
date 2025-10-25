import os
import sys
import json

# Logica per aggiungere il percorso radice al sys.path
script_dir = os.path.dirname(__file__)
proj_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

from g_src.g_general.config import load_config_and_clients
from g_src.g_general.utils import run_rag_search
from g_src.g_general.utils_exporter import export_diagnostics_to_word # Importa la nuova funzione

def run_keyword_diagnostics(config, clients):
    """
    Permette all'utente di inserire una query, visualizza i risultati
    e li salva in un report Word alla fine della sessione.
    """
    diagnostic_log = [] # Lista per raccogliere i dati della sessione

    while True:
        query = input("\n\n💬 Inserisci la query di test da analizzare (o 'exit' per uscire): ").strip()
        if query.lower() == 'exit':
            break

        print(f"\n--- Eseguo ricerca per la query: '{query}' ---")
        
        analysis_mock = {"intent": "ricerca_generale", "entities": {}}
        retrieved_hits = run_rag_search(clients, config, query, analysis_mock)

        # Salva i risultati del turno corrente nel log
        if retrieved_hits:
            diagnostic_log.append({"query": query, "hits": retrieved_hits})
        else:
            diagnostic_log.append({"query": query, "hits": []}) # Logga anche le query senza risultati

        if not retrieved_hits:
            print("\n🚫 NESSUN CHUNK RECUPERATO.")
            continue

        print("\n" + "="*30 + " RISULTATI RECUPERATI " + "="*30)
        for i, hit in enumerate(retrieved_hits):
            payload = hit.payload
            print(f"\n--- [Risultato #{i+1}] ---")
            print(f"  Score: {hit.score:.4f}")
            print(f"  Fonte: [{payload.get('document_title')}] Art. {payload.get('articolo')}, Comma {payload.get('comma')}")
            print(f"  Testo: \"{payload.get('testo_originale_comma')}\"")
            print(f"  Keywords: {json.dumps(payload.get('keywords', []), ensure_ascii=False, indent=4)}")
        
        print("\n" + "="*80)
    
    # Alla fine del ciclo, dopo che l'utente ha digitato 'exit'
    if diagnostic_log:
        print("\n--- Generazione Report di Diagnostica ---")
        export_diagnostics_to_word(diagnostic_log, proj_root)
    else:
        print("\nNessuna query eseguita, nessun report da generare.")

if __name__ == "__main__":
    print("🚀 Avvio Script di Diagnostica Keyword...")
    app_config, app_clients, _, _, _ = load_config_and_clients()
    run_keyword_diagnostics(app_config, app_clients)
    print("\n🏁 Sessione di diagnostica terminata.")