# c_processors/b_regcam/6a_delete_by_filter.py

"""
PASSO 6a (MANUTENZIONE): Cancellazione Mirata dei Dati in Qdrant.

Questo script è uno strumento di manutenzione per pulire la collezione Qdrant
prima di un nuovo ingest di una fonte di dati già esistente.

ATTENZIONE: Questo script esegue un'operazione DISTRUTTIVA e irreversibile
sui dati della collezione specificata. Usare con la massima cautela.

Logica di Funzionamento:
1. Si connette alla collezione Qdrant.
2. Esegue una scansione per trovare tutti i 'document_title' unici presenti.
3. Presenta all'utente un menu per scegliere quale documento cancellare.
4. Richiede una doppia conferma esplicita prima di procedere.
5. Se confermato, esegue l'operazione di cancellazione usando un filtro
   preciso sul 'document_title' selezionato.

INPUT:
- Connessione alla collezione Qdrant.
- Selezione interattiva dell'utente.

OUTPUT:
- Rimozione di tutti i punti (chunk) corrispondenti al filtro dalla collezione Qdrant.
"""

import os
import sys
from qdrant_client import QdrantClient, models
from dotenv import load_dotenv
from collections import defaultdict

# --- Setup del Percorso ---
script_dir = os.path.dirname(__file__)
project_root = os.path.abspath(os.path.join(script_dir, '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Caricamento Configurazione ---
env_path = os.path.join(project_root, "a_chiavi", ".env")
load_dotenv(dotenv_path=env_path)

# --- Configurazione ---
QDRANT_URL = os.getenv("QDRANT_HOST")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_COLLECTION_NAME = "regcam_v11"


def main():
    """Funzione principale che orchestra il processo di cancellazione."""
    print(f"--- PASSO 6a: Avvio Strumento di Manutenzione per la Collezione '{QDRANT_COLLECTION_NAME}' ---")
    print("ATTENZIONE: Stai per eseguire un'operazione di cancellazione dati irreversibile.")

    try:
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        print("✅ Connessione a Qdrant riuscita.")
    except Exception as e:
        print(f"❌ ERRORE CRITICO durante la connessione a Qdrant: {e}"); sys.exit(1)

    # --- Fase 1: Discovery dei documenti presenti ---
    print("\n🔎 Scansione dei documenti presenti nella collezione in corso...")
    try:
        # Usiamo un dizionario per contare i punti per ogni document_title
        doc_counts = defaultdict(int)
        
        # Facciamo uno scroll su tutti i punti per aggregare i titoli
        all_points, _ = client.scroll(
            collection_name=QDRANT_COLLECTION_NAME,
            limit=10000, # Limite alto per recuperare tutti i punti (da aumentare se necessario)
            with_payload=["document_title"],
            with_vectors=False
        )

        for point in all_points:
            title = point.payload.get("document_title")
            if title:
                doc_counts[title] += 1
        
        if not doc_counts:
            print("ℹ️  La collezione è vuota. Nessuna operazione da eseguire.")
            return

        documents = list(doc_counts.keys())
        print("✅ Scansione completata. Documenti trovati:")
        for i, doc_title in enumerate(documents):
            print(f"  [{i+1}] {doc_title} ({doc_counts[doc_title]} punti)")

    except Exception as e:
        print(f"❌ ERRORE durante la scansione della collezione: {e}"); return

    # --- Fase 2: Selezione Utente ---
    selected_doc_title = None
    while True:
        try:
            choice_str = input("\nInserisci il numero del documento da CANCELLARE (o 'exit' per uscire): ")
            if choice_str.lower() == 'exit':
                print("Operazione annullata."); return
            
            choice = int(choice_str)
            if 1 <= choice <= len(documents):
                selected_doc_title = documents[choice - 1]
                break
            else:
                print("Scelta non valida. Riprova.")
        except (ValueError, IndexError):
            print("Input non valido. Inserisci solo il numero corrispondente.")

    # --- Fase 3: Doppia Conferma ---
    print("\n" + "="*50)
    print(f"ATTENZIONE: Stai per cancellare DEFINITIVAMENTE tutti i {doc_counts[selected_doc_title]} punti relativi a:")
    print(f"  -> '{selected_doc_title}'")
    print("Questa operazione non può essere annullata.")
    print("="*50)
    
    confirm = input("Sei assolutamente sicuro? Digita 's' e premi Invio per confermare: ").lower()

    if confirm != 's':
        print("❌ Cancellazione annullata dall'utente.")
        return

    # --- Fase 4: Esecuzione della Cancellazione ---
    print(f"\nProcedo con la cancellazione per '{selected_doc_title}'...")
    try:
        response = client.delete(
            collection_name=QDRANT_COLLECTION_NAME,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_title",
                            match=models.MatchValue(value=selected_doc_title)
                        )
                    ]
                )
            ),
            wait=True # Attende che l'operazione sia completata
        )
        print("✅ Operazione di cancellazione completata con successo.")
        print(f"   - Stato dell'operazione: {response.status}")
    except Exception as e:
        print(f"❌ ERRORE durante l'operazione di delete in Qdrant: {e}")

if __name__ == "__main__":
    main()