import json
from pathlib import Path

# Configura il percorso del file da controllare
BASE_DIR = Path(__file__).resolve().parents[2]
FILE_TO_CHECK = BASE_DIR / "c_outputs_embeddings" / "embeddings_v11.json"

def find_json_error():
    """
    Legge un file JSON di grandi dimensioni riga per riga per identificare
    il punto esatto di un errore di sintassi.
    """
    print(f"🕵️ Avvio diagnosi sintassi per il file: {FILE_TO_CHECK.name}")
    
    try:
        with open(FILE_TO_CHECK, 'r', encoding='utf-8') as f:
            # Tenta di caricare l'intero file per vedere se è già valido
            json.load(f)
            print("✅ SUCCESSO: Il file JSON è già valido. Nessun errore trovato.")
            return
    except json.JSONDecodeError as e:
        print(f"🔍 Errore di sintassi rilevato. Causa: {e.msg}")
        print(f"   L'errore si trova approssimativamente alla riga {e.lineno}, colonna {e.colno}.")
        print("   Procedo con un'analisi più dettagliata per isolare la riga esatta...")

    # Se il caricamento completo fallisce, analizza riga per riga
    with open(FILE_TO_CHECK, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            try:
                # Tenta di parsare solo la riga corrente (non funzionerà per le righe intermedie)
                # ma può fallire in modo specifico sulla riga che contiene l'errore.
                json.loads(line)
            except json.JSONDecodeError as e:
                # Controlla se la riga contiene un errore comune come una virgola alla fine di un oggetto
                if line.strip().endswith("},"):
                    continue # Probabilmente ok
                
                print("-" * 50)
                print(f"🚨 ERRORE DI SINTASSI PROBABILE IDENTIFICATO ALLA RIGA: {i + 1}")
                print(f"   CONTENUTO RIGA: {line.strip()}")
                print(f"   MOTIVO: {e}")
                print("-" * 50)
                print("   Azione consigliata: Apri il file, vai alla riga indicata e controlla la sintassi (virgole, parentesi).")
                return

    print("ℹ️ Diagnosi completata. Se non sono stati trovati errori specifici, il problema potrebbe essere legato a parentesi non corrispondenti all'inizio o alla fine del file.")


if __name__ == "__main__":
    find_json_error()