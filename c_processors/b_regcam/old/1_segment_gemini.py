import json
import re
from pathlib import Path

# --- 1. CONFIGURAZIONE DEI PERCORSI ---
BASE_DIR = Path(__file__).resolve().parents[2]
INPUT_STRUCTURE = BASE_DIR / "d_structured_outputs" / "regolamento_camera_structure.json"
INPUT_ENRICHED = BASE_DIR / "d_structured_outputs" / "enriched_data_v2.json"
# Nuovo file di output per la versione corretta
OUTPUT_CHUNKS = BASE_DIR / "c_outputs_chunks" / "chunks_v11_final.json" 

# --- 2. FUNZIONI DI UTILITÀ ---

def extract_roman_numeral(titolo: str) -> str | None:
    match = re.search(r'CAPO\s+([IVXLCDM]+)', titolo.upper())
    return match.group(1) if match else None

def to_roman(n: int) -> str:
    roman_map = {1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V'}
    return roman_map.get(n, str(n))

# --- 3. LOGICA PRINCIPALE ---

def costruisci_mappa_strutturale() -> dict:
    with open(INPUT_STRUCTURE, 'r', encoding="utf-8") as f:
        struttura = json.load(f)

    mappa = {}
    print("🧠 Costruzione della mappa strutturale dagli articoli...")
    for idx_parte, parte in enumerate(struttura.get("parti", []), 1):
        parte_id_roman = to_roman(idx_parte)
        
        for capo in parte.get("capi", []):
            capo_id_roman = extract_roman_numeral(capo["capo_titolo"])
            
            # NUOVA GESTIONE CORRETTA: Se non c'è un numero romano, l'ID sarà None
            if not capo_id_roman:
                print(f"  -> Avviso: il capo '{capo['capo_titolo']}' non ha un numero romano. 'capo_id_roman' sarà nullo.")

            for articolo in capo.get("articoli", []):
                mappa[articolo] = {
                    "documento_titolo": struttura.get("documento_titolo", "N/D"),
                    # AGGIUNTA FONDAMENTALE: Tipo di documento
                    "document_type": "testo_normativo",
                    "parte_titolo": parte.get("parte_titolo", "N/D"),
                    "parte_id_roman": parte_id_roman,
                    "capo_titolo": capo.get("capo_titolo", "N/D"),
                    "capo_id_roman": capo_id_roman # Ora può essere None
                }
    print(f"✅ Mappa strutturale costruita per {len(mappa)} articoli.")
    return mappa

def segmenta_e_pulisci_chunk():
    try:
        with open(INPUT_ENRICHED, 'r', encoding="utf-8") as f:
            enriched_data = json.load(f)
        print(f"📄 Caricati {len(enriched_data)} record da: {INPUT_ENRICHED.name}")
    except FileNotFoundError:
        print(f"❌ ERRORE: File di dati arricchiti non trovato: {INPUT_ENRICHED}")
        return
    except json.JSONDecodeError:
        print(f"❌ ERRORE: Impossibile decodificare il JSON dal file: {INPUT_ENRICHED}")
        return

    mappa_struttura = costruisci_mappa_strutturale()
    chunks_finali = []

    print("\n--- Inizio Processo di Segmentazione e Pulizia ---")
    for record in enriched_data:
        articolo_id = record.get("articolo")
        
        if articolo_id not in mappa_struttura:
            print(f"  -> Avviso: Articolo '{articolo_id}' trovato nei dati arricchiti ma non nel file di struttura. Verrà saltato.")
            continue

        metadati_strutturali = mappa_struttura[articolo_id]
        comma_pulito = record.get("comma", "1").replace(".", "")

        chunk = {
            **metadati_strutturali, # Aggiunge tutti i metadati dalla mappa
            "articolo": articolo_id,
            "comma": comma_pulito,
            "testo_originale_comma": record.get("testo_originale_comma", ""),
            "keywords": record.get("keywords", [])
        }
        
        # Rimuove le chiavi con valore None prima di aggiungerle alla lista finale
        chunk_pulito = {k: v for k, v in chunk.items() if v is not None}
        chunks_finali.append(chunk_pulito)

    OUTPUT_CHUNKS.parent.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_CHUNKS, "w", encoding="utf-8") as f:
        json.dump(chunks_finali, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 Segmentazione e pulizia completate!")
    print(f"✅ Creati {len(chunks_finali)} chunk finali.")
    print(f"📁 File salvato in: {OUTPUT_CHUNKS}")

if __name__ == "__main__":
    segmenta_e_pulisci_chunk()