# g_src/g_general/cost_utils.py

import os
import google.generativeai as genai
from dotenv import load_dotenv
from PIL import Image

# ... (parte iniziale invariata) ...
try:
    dotenv_path = os.path.join(os.getcwd(), 'a_chiavi', '.env')
    if not os.path.exists(dotenv_path):
        dotenv_path = os.path.join(os.getcwd(), '..', '..', 'a_chiavi', '.env')
    load_dotenv(dotenv_path=dotenv_path)
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
except (KeyError, FileNotFoundError):
    print("ERRORE: Assicurati che 'a_chiavi/.env' esista e contenga la chiave 'GEMINI_API_KEY'.")
MODEL_PRICING = {
    "gemini-2.5-pro": {
        "input_per_million_tokens": 1.25,
        "output_per_million_tokens": 10.00
    },
    "gemini-2.5-flash": {
        "input_per_million_tokens": 0.30,
        "output_per_million_tokens": 2.50
    }
}
# --- FUNZIONI DI CALCOLO ---

def count_tokens(model_name: str, content) -> int:
    """
    Conta i token per un dato contenuto (testo o multimodale) usando un modello specifico.
    """
    try:
        model = genai.GenerativeModel(model_name)
        return model.count_tokens(content).total_tokens
    except Exception as e:
        print(f"AVVISO: Impossibile contare i token. Verifica la configurazione. Errore: {e}")
        return 0

def estimate_cost(model_name: str, num_tokens: int, direction: str) -> float:
    """Stima il costo basandosi sul numero di token."""
    if model_name not in MODEL_PRICING:
        print(f"AVVISO: Prezzi non disponibili per il modello '{model_name}'. Restituisco costo 0.")
        return 0.0
    price_key = f"{direction}_per_million_tokens"
    price_per_million = MODEL_PRICING[model_name].get(price_key)
    if price_per_million is None:
        print(f"AVVISO: Prezzo per '{direction}' non trovato per il modello '{model_name}'. Restituisco costo 0.")
        return 0.0
    cost = (num_tokens / 1_000_000) * price_per_million
    return cost

def display_cost_estimate(text_to_process: list, model_name: str):
    """Mostra una stima dei costi per una lista di testi."""
    if not text_to_process:
        print("Nessun testo da processare per la stima dei costi.")
        return
    print("\n--- STIMA DEI COSTI PER L'ESECUZIONE (TESTUALE) ---")
    full_input_text = " ".join(text_to_process)
    total_input_tokens = count_tokens(model_name, full_input_text)
    if total_input_tokens == 0:
        print("Stima dei costi annullata a causa di un errore nel conteggio dei token.")
        return
    
    total_output_tokens_estimate = total_input_tokens

    total_input_cost = estimate_cost(model_name, total_input_tokens, 'input')
    total_output_cost = estimate_cost(model_name, total_output_tokens_estimate, 'output')
    total_cost = total_input_cost + total_output_cost

    print(f"Modello: {model_name}")
    print(f"Token INPUT: {total_input_tokens:,}")
    print(f"Token OUTPUT (stima): {total_output_tokens_estimate:,}")
    print("-" * 45)
    print(f"Costo INPUT: ${total_input_cost:.6f}")
    print(f"Costo OUTPUT: ${total_output_cost:.6f}")
    print(f"COSTO TOTALE STIMATO: ${total_cost:.6f}")
    print("--- FINE STIMA DEI COSTI ---\n")

def display_multimodal_cost_estimate(image_paths: list, prompt_text: str, model_name: str):
    """
    Mostra una stima dei costi per un task multimodale (immagini + testo).
    """
    print("\n--- STIMA DEI COSTI PER L'ESECUZIONE (MULTIMODALE) ---")
    print("Calcolo dei token in corso per l'input multimodale...")
    
    total_input_tokens = 0
    for image_path in image_paths:
        try:
            img = Image.open(image_path)
            # --- CORREZIONE ---
            # Converte l'immagine in formato RGB standard per rimuovere formati non supportati come MPO.
            img = img.convert('RGB') 
            total_input_tokens += count_tokens(model_name, [prompt_text, img])
        except Exception as e:
            print(f"AVVISO: Impossibile processare l'immagine {os.path.basename(image_path)} per la stima: {e}")

    # ... (resto della funzione invariato) ...
    if total_input_tokens == 0:
        print("Stima dei costi annullata a causa di un errore nel conteggio dei token.")
        return

    total_output_tokens_estimate = 100 * len(image_paths)

    total_input_cost = estimate_cost(model_name, total_input_tokens, 'input')
    total_output_cost = estimate_cost(model_name, total_output_tokens_estimate, 'output')
    total_cost = total_input_cost + total_output_cost
    
    print(f"Modello: {model_name}")
    print(f"Numero di immagini: {len(image_paths)}")
    print("-" * 45)
    print(f"Token totali in INPUT (testo+immagini): {total_input_tokens:,}")
    print(f"Token totali in OUTPUT (stima): {total_output_tokens_estimate:,}")
    print("-" * 45)
    print(f"Costo stimato per l'INPUT: ${total_input_cost:.6f}")
    print(f"Costo stimato per l'OUTPUT: ${total_output_cost:.6f}")
    print("-" * 45)
    print(f"COSTO TOTALE STIMATO PER QUESTA ESECUZIONE: ${total_cost:.6f}")
    print("--- FINE STIMA DEI COSTI ---\n")

# ... (blocco if __name__ == '__main__' invariato) ...
if __name__ == '__main__':
    # Simula una lista di paragrafi da inviare
    paragrafi_di_esempio = [
        "Questo è il primo paragrafo, contiene un certo numero di caratteri.",
        "Questo è un secondo paragrafo, un po' più lungo del precedente per fare un test più realistico.",
        "Terzo e ultimo paragrafo di esempio."
    ]
    
    print("Esempio di stima per il modello 'gemini-2.5-flash':")
    display_cost_estimate(paragrafi_di_esempio, "gemini-2.5-flash")
    
    print("\nEsempio di stima per il modello 'gemini-2.5-pro':")
    display_cost_estimate(paragrafi_di_esempio, "gemini-2.5-pro")