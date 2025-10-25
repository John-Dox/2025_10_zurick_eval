# b_ocr/scripts/image_utils/rinomina_e_ruota.py
import os
import sys
import shutil
from tkinter import Tk, filedialog
from PIL import Image

# --- CONFIGURAZIONE ---
try:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    if project_root not in sys.path:
        sys.path.append(project_root)
except Exception as e:
    print(f"ERRORE di configurazione percorsi: {e}")
    exit()
# --- FINE CONFIGURAZIONE ---

def processa_immagini(files, dest_dir, start_num, ruota, prefix="pag_"):
    """Copia, rinomina e, se richiesto, ruota i file selezionati."""
    numero = start_num
    passo = 2
    
    os.makedirs(dest_dir, exist_ok=True)
    files_ordinati = sorted(files, key=lambda x: os.path.basename(x).lower())

    print("\n--- INIZIO ELABORAZIONE ---")
    for source_path in files_ordinati:
        _, nome_orig = os.path.split(source_path)
        _, ext = os.path.splitext(nome_orig)

        nuovo_nome = f"{prefix}_{str(numero).zfill(3)}{ext.lower()}"
        dest_path = os.path.join(dest_dir, nuovo_nome)

        print(f"  - Copio e Rinomino: {nome_orig} → {nuovo_nome}")
        try:
            shutil.copy2(source_path, dest_path)
            
            # Se la rotazione è richiesta, la esegue sul NUOVO file
            if ruota:
                img = Image.open(dest_path)
                img_rotated = img.rotate(180, expand=True)
                img_rotated.save(dest_path) # Sovrascrive il file appena copiato con la versione ruotata
                print(f"    - Ruotato di 180°")

        except Exception as e:
            print(f"    ❌ ERRORE durante l'elaborazione di {nome_orig}: {e}")
            continue

        numero += passo

def main():
    default_book_name = "c_gianniti_lupo"
    default_target_folder = "cap_9" 
    
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    print("📂 Seleziona le immagini da processare:")
    files = filedialog.askopenfilenames(title="Seleziona immagini")
    
    if not files:
        print("❌ Nessun file selezionato."); root.destroy(); return

    try:
        book_input = input(f"Inserisci il nome del libro (default: {default_book_name}): ").strip()
        book_name = book_input if book_input else default_book_name

        target_input = input(f"Inserisci la cartella target (es. 0_indice, cap_1) (default: {default_target_folder}): ").strip()
        target_folder = target_input if target_input else default_target_folder

        start_num = int(input("🔢 Inserisci il numero di pagina da cui partire: ").strip())
        
        ruota_input = input("🔄 Ruotare le immagini di 180°? (s/n, default: n): ").strip().lower()
        ruota = True if ruota_input == 's' else False

    except (ValueError, KeyboardInterrupt):
        print("\n❌ Input non valido o operazione annullata."); root.destroy(); return
    
    root.destroy()

    dest_directory = os.path.join(project_root, "b_ocr", "input_images", book_name, target_folder)
    modalita = "pari" if start_num % 2 == 0 else "dispari"
    
    print("\n--- RIEPILOGO OPERAZIONE ---")
    print(f"File da processare: {len(files)}")
    print(f"Cartella di destinazione: {dest_directory}")
    print(f"Numero di partenza: {start_num} (modalità {modalita})")
    print(f"Rotazione 180°: {'Sì' if ruota else 'No'}")
    print("----------------------------")
    
    confirm = input("Procedere? (s/n): ").strip().lower()
    if confirm != 's':
        print("Operazione annullata.")
        return

    processa_immagini(files, dest_directory, start_num, ruota)
    
    print("\n✅ Elaborazione completata!")

if __name__ == "__main__":
    main()