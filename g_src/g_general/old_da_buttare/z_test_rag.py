import os
import sys
import json # Importo json per un pretty-printing dell'output

# Logica per aggiungere il percorso radice al sys.path
script_dir = os.path.dirname(__file__)
proj_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

# Import delle funzioni e dei loader necessari
from g_src.g_general.config import load_config_and_clients
from g_src.g_general.utils import (
    preprocess_query_for_ordinals,
    analyze_query_for_rag,
    handle_structural_query
)

def run_test(test_function, *args):
    """Esegue una singola funzione di test e ne cattura il risultato."""
    test_name = test_function.__name__
    print(f"\n--- Eseguo Test: {test_name} ---") # Aggiunto newline per leggibilità
    try:
        test_function(*args)
        print(f"✅ PASS: {test_name}")
        return True
    except AssertionError as e:
        print(f"❌ FAIL: {test_name}")
        print(f"   Dettaglio Errore: {e}")
        return False

# ==============================================================================
# --- DEFINIZIONE DEI TEST CASE CON OUTPUT DIAGNOSTICO ---
# ==============================================================================

def test_find_article_in_regolamento(analyzer, structures):
    """Verifica la ricerca di un articolo specificando il Regolamento."""
    query = "A quale capo appartiene l'articolo 3 del Regolamento?"
    analysis = analyze_query_for_rag(analyzer['client'], analyzer['model'], query)
    
    # --- RIGA DIAGNOSTICA ---
    print(f"   [DIAGNOSTICA] Output AI Router: {json.dumps(analysis, indent=2)}")
    
    result = handle_structural_query(analysis, structures)
    
    assert result is not None, "La funzione non dovrebbe restituire None"
    assert "Regolamento della Camera" in result, "La risposta non contiene il nome corretto del documento"
    assert "CAPO I" in result, "La sezione corretta ('CAPO I') non è stata trovata"

def test_find_article_in_costituzione(analyzer, structures):
    """Verifica la ricerca di un articolo specificando la Costituzione."""
    query = "In che parte si trova l'articolo 13 della Costituzione?"
    analysis = analyze_query_for_rag(analyzer['client'], analyzer['model'], query)

    # --- RIGA DIAGNOSTICA ---
    print(f"   [DIAGNOSTICA] Output AI Router: {json.dumps(analysis, indent=2)}")

    result = handle_structural_query(analysis, structures)

    assert result is not None, "La funzione non dovrebbe restituire None"
    assert "Costituzione della Repubblica Italiana" in result, "La risposta non contiene il nome corretto del documento"
    assert "PARTE PRIMA" in result, "La sezione corretta ('PARTE PRIMA') non è stata trovata"
    assert "Titolo I" in result, "La sottosezione corretta ('Titolo I') non è stata trovata"

def test_find_section_title(analyzer, structures):
    """Verifica la ricerca del titolo di una sezione specifica."""
    query = "Come si intitola il primo capo del regolamento?"
    processed_query = preprocess_query_for_ordinals(query) 
    analysis = analyze_query_for_rag(analyzer['client'], analyzer['model'], processed_query)

    # --- RIGA DIAGNOSTICA ---
    print(f"   [DIAGNOSTICA] Output AI Router: {json.dumps(analysis, indent=2)}")

    result = handle_structural_query(analysis, structures)

    assert result is not None, "La funzione non dovrebbe restituire None"
    assert "Regolamento" in result, "Il documento corretto non è stato menzionato nella risposta"
    assert "DISPOSIZIONI PRELIMINARI" in result.upper(), "Il titolo corretto non è stato trovato"

def test_article_not_found(analyzer, structures):
    """Verifica che la ricerca di un articolo inesistente fallisca correttamente."""
    query = "Dove si trova l'articolo 999 della Costituzione?"
    analysis = analyze_query_for_rag(analyzer['client'], analyzer['model'], query)

    # --- RIGA DIAGNOSTICA ---
    print(f"   [DIAGNOSTICA] Output AI Router: {json.dumps(analysis, indent=2)}")

    result = handle_structural_query(analysis, structures)

    assert result is not None, "La funzione non dovrebbe restituire None"
    assert "Non è stato possibile trovare" in result, "Il messaggio di fallimento non è corretto"

# (Il resto dello script main() rimane invariato)
def main():
    print("*"*20 + " AVVIO SUITE DI TEST (MODALITÀ DIAGNOSTICA) " + "*"*20)
    try:
        config, clients, all_docs_structures, _, _ = load_config_and_clients()
    except Exception as e:
        print(f"\n❌ ERRORE CRITICO: Impossibile inizializzare l'ambiente di test. {e}")
        return
    analyzer_info = {
        "client": clients["gemini_models"]["router"],
        "model": config["models"]["router"]
    }
    tests_to_run = [
        test_find_article_in_regolamento,
        test_find_article_in_costituzione,
        test_find_section_title,
        test_article_not_found,
    ]
    results = []
    for test_func in tests_to_run:
        passed = run_test(test_func, analyzer_info, all_docs_structures)
        results.append(passed)
    success_count = sum(results)
    total_count = len(results)
    print("\n" + "*"*20 + " RIEPILOGO TEST " + "*"*20)
    print(f"Risultato: {success_count} / {total_count} test superati.")
    print("*"*58)
    if success_count != total_count:
        print("\n⚠️ Alcuni test non sono stati superati. Controllare i log sopra.")
        sys.exit(1)
    else:
        print("\n🎉 Tutti i test sono stati superati con successo!")

if __name__ == "__main__":
    main()