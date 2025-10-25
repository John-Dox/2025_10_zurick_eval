import os
import json

# --- 1. CONFIGURAZIONE DEI PERCORSI ---
def load_paths():
    """Definisce i percorsi per la migrazione una tantum dei dati con keyword del Regolamento."""
    proj_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Cartella di input (vecchia struttura)
    source_dir = os.path.join(proj_root, "d_outputs", "00_structured", "b_regcam")
    
    # Cartella di output (nuova struttura)
    destination_dir = os.path.join(proj_root, "d_outputs", "00_structured", "b_regcam")
    
    os.makedirs(destination_dir, exist_ok=True)
    
    paths = {
        "source_file": os.path.join(source_dir, "enriched_data_v2.json"),
        "destination_file": os.path.join(destination_dir, "regcam_keywords_data.json")
    }
    
    print("✅ Percorsi di input e output configurati per la migrazione.")
    return paths

# --- 2. LOGICA DI MIGRAZIONE ---
def migrate_keywords_data():
    """
    Legge i dati arricchiti con keyword da un vecchio file e li salva in un nuovo
    file standardizzato.
    """
    paths = load_paths()

    try:
        with open(paths["source_file"], 'r', encoding='utf-8') as f:
            source_data = json.load(f)
        print(f"📄 Dati sorgente letti da: {os.path.basename(paths['source_file'])}")
    except FileNotFoundError:
        print(f"❌ ERRORE: File sorgente dei dati non trovato: {paths['source_file']}")
        return
    except json.JSONDecodeError:
        print(f"❌ ERRORE: Impossibile decodificare il JSON dal file sorgente.")
        return

    # In questo caso, la struttura dati è già quella che ci serve, quindi copiamo direttamente
    final_output = source_data

    try:
        with open(paths["destination_file"], "w", encoding="utf-8") as f:
            json.dump(final_output, f, ensure_ascii=False, indent=2)
        print(f"\n🎉 Migrazione completata con successo!")
        print(f"✅ Migrati {len(final_output)} record.")
        print(f"📁 Nuovo file salvato in: {paths['destination_file']}")
    except Exception as e:
        print(f"❌ ERRORE durante il salvataggio del nuovo file: {e}")


# --- 3. AVVIO ---
if __name__ == "__main__":
    print("--- Avvio Script Temporaneo di Migrazione Dati Keyword ---")
    migrate_keywords_data()
    print("\n--- Operazione terminata ---")