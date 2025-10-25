import os
import json

# --- 1. CONFIGURAZIONE DEI PERCORSI ---
def load_paths():
    """Definisce i percorsi per la migrazione una tantum dei riassunti del Regolamento."""
    proj_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # NOTA: Questo percorso punta alla vecchia cartella di output, come da screenshot.
    # Se hai spostato il file, aggiorna questo percorso.
    source_dir = os.path.join(proj_root, "d_outputs", "00_structured", "b_regcam")
    
    # Nuova cartella di output secondo la nuova architettura.
    destination_dir = os.path.join(proj_root, "d_outputs", "00_structured", "b_regcam")
    
    os.makedirs(destination_dir, exist_ok=True)
    
    paths = {
        "source_file": os.path.join(source_dir, "enrichment_progress_v2.json"),
        "destination_file": os.path.join(destination_dir, "regcam_summaries.json")
    }
    
    print("✅ Percorsi di input e output configurati per la migrazione.")
    return paths

# --- 2. LOGICA DI MIGRAZIONE ---
def migrate_summaries_once():
    """
    Legge i riassunti da un vecchio file di progresso e li salva nel nuovo
    file standardizzato. Esegue l'operazione una sola volta.
    """
    paths = load_paths()

    # Carica i dati dal vecchio file
    try:
        with open(paths["source_file"], 'r', encoding='utf-8') as f:
            source_data = json.load(f)
        print(f"📄 Dati sorgente letti da: {os.path.basename(paths['source_file'])}")
    except FileNotFoundError:
        print(f"❌ ERRORE: File sorgente dei riassunti non trovato: {paths['source_file']}")
        print("   Assicurati che il file 'enrichment_progress_v2.json' esista nella sua cartella originale.")
        return
    except json.JSONDecodeError:
        print(f"❌ ERRORE: Impossibile decodificare il JSON dal file sorgente.")
        return

    # Estrae solo la sezione dei riassunti
    summaries_to_migrate = source_data.get("summaries", {})
    if not summaries_to_migrate:
        print("⚠️ Nessun riassunto trovato nel file sorgente. Il file di output sarà vuoto.")

    # Crea la nuova struttura dati per il salvataggio
    final_output = {
        "summaries": summaries_to_migrate
    }

    # Salva nel nuovo file, sovrascrivendolo se esiste
    try:
        with open(paths["destination_file"], "w", encoding="utf-8") as f:
            json.dump(final_output, f, ensure_ascii=False, indent=2)
        print(f"\n🎉 Migrazione completata con successo!")
        print(f"✅ Migrati {len(summaries_to_migrate)} riassunti.")
        print(f"📁 Nuovo file salvato in: {paths['destination_file']}")
    except Exception as e:
        print(f"❌ ERRORE durante il salvataggio del nuovo file: {e}")

# --- 3. AVVIO ---
if __name__ == "__main__":
    print("--- Avvio Script Temporaneo di Migrazione Riassunti ---")
    migrate_summaries_once()
    print("\n--- Operazione terminata ---")