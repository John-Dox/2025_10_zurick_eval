import json
from pathlib import Path
from collections import defaultdict

# --- 1. CONFIGURAZIONE DEI PERCORSI ---
# Questo script deve essere eseguito dalla cartella che lo contiene
# (es. g_src/q_amplia_struttura/) per far funzionare i percorsi relativi.
BASE_DIR = Path(__file__).resolve().parents[2]
STRUCTURE_FILE = BASE_DIR / "d_structured_outputs" / "regolamento_camera_structure.json"
ENRICHED_DATA_FILE = BASE_DIR / "d_structured_outputs" / "enriched_data_v2.json"

def run_diagnostics():
    """
    Esegue una serie di controlli incrociati tra il file di struttura
    e il file di dati arricchiti per verificare la completezza e la coerenza.
    """
    print("🚀 Avvio dello script di Diagnostica Dati...")
    print("-" * 50)

    # --- CARICAMENTO DATI ---
    try:
        with open(STRUCTURE_FILE, 'r', encoding="utf-8") as f:
            structure_data = json.load(f)
        print(f"✅ File di struttura caricato: {STRUCTURE_FILE.name}")
        
        with open(ENRICHED_DATA_FILE, 'r', encoding="utf-8") as f:
            enriched_data = json.load(f)
        print(f"✅ File di dati arricchiti caricato: {ENRICHED_DATA_FILE.name}")

    except FileNotFoundError as e:
        print(f"❌ ERRORE CRITICO: File non trovato. Impossibile procedere.")
        print(f"   Dettaglio: {e}")
        return
    except json.JSONDecodeError as e:
        print(f"❌ ERRORE CRITICO: Errore nel formato JSON di un file.")
        print(f"   Dettaglio: {e}")
        return

    print("-" * 50)

    # --- FASE 1: CONTROLLO COMPLETEZZA ARTICOLI ---
    print("\n--- FASE 1: Verifica Completezza Articoli ---")
    
    # Estrae tutti gli ID degli articoli attesi dalla struttura
    articoli_attesi = set()
    for parte in structure_data.get("parti", []):
        for capo in parte.get("capi", []):
            for articolo_id in capo.get("articoli", []):
                articoli_attesi.add(str(articolo_id))
    
    # Estrae tutti gli ID degli articoli presenti nei dati arricchiti
    articoli_processati = set(str(record.get("articolo")) for record in enriched_data)

    print(f"  - Articoli attesi secondo la struttura: {len(articoli_attesi)}")
    print(f"  - Articoli unici trovati nei dati arricchiti: {len(articoli_processati)}")

    # Confronta i due set per trovare le differenze
    articoli_mancanti = articoli_attesi - articoli_processati
    articoli_in_piu = articoli_processati - articoli_attesi

    if not articoli_mancanti and not articoli_in_piu:
        print("✅ SUCCESSO: Tutti gli articoli della struttura sono presenti nei dati arricchiti.")
    else:
        if articoli_mancanti:
            print(f"⚠️ ATTENZIONE: {len(articoli_mancanti)} articoli MANCANTI nei dati arricchiti:")
            print(f"   {sorted(list(articoli_mancanti), key=lambda x: int(re.match(r'\d+', x).group()))}")
        if articoli_in_piu:
            print(f"⚠️ ATTENZIONE: {len(articoli_in_piu)} articoli IN ECCESSO trovati nei dati arricchiti:")
            print(f"   {sorted(list(articoli_in_piu), key=lambda x: int(re.match(r'\d+', x).group()))}")
    
    print("-" * 50)

    # --- FASE 2: CONTEGGIO E ANALISI DEI COMMI PER ARTICOLO ---
    print("\n--- FASE 2: Analisi Conteggio Commi ---")

    # Raggruppa i commi per articolo
    commi_per_articolo = defaultdict(list)
    for record in enriched_data:
        articolo_id = str(record.get("articolo"))
        comma_num = record.get("comma")
        if articolo_id and comma_num:
            commi_per_articolo[articolo_id].append(comma_num)
            
    conteggio_commi_per_articolo = {art: len(commi) for art, commi in commi_per_articolo.items()}
    
    totale_commi_processati = sum(conteggio_commi_per_articolo.values())

    print(f"  - Numero totale di commi (record) processati: {totale_commi_processati}")

    # Cerca articoli con un numero di commi anomalo (es. 0 o > 20)
    articoli_con_zero_commi = [art for art, count in conteggio_commi_per_articolo.items() if count == 0]
    articoli_con_molti_commi = {art: count for art, count in conteggio_commi_per_articolo.items() if count > 20}

    if not articoli_con_zero_commi and not articoli_con_molti_commi:
        print("✅ SUCCESSO: Nessuna anomalia evidente nel conteggio dei commi.")
    else:
        if articoli_con_zero_commi:
            print(f"⚠️ ATTENZIONE: Trovati {len(articoli_con_zero_commi)} articoli con zero commi.")
        if articoli_con_molti_commi:
            print(f"⚠️ ATTENZIONE: Trovati articoli con un numero di commi insolitamente alto:")
            for art, count in articoli_con_molti_commi.items():
                print(f"   - Art. {art}: {count} commi")

    print("-" * 50)
    print("\n🏁 Diagnostica completata.")

if __name__ == "__main__":
    run_diagnostics()