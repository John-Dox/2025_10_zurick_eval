#!/bin/bash

# Script per duplicare (mirror) la repository corrente in una nuova repository remota.

# --- 1. Chiede l'URL della nuova repository ---
echo "Inserisci l'URL HTTPS della nuova repository GitHub (vuota e privata):"
read NEW_REPO_URL

# Controlla se l'URL è stato inserito
if [ -z "$NEW_REPO_URL" ]; then
    echo "❌ Errore: URL non inserito. Operazione annullata."
    exit 1
fi

# --- 2. Aggiunge il nuovo remote temporaneamente ---
REMOTE_NAME="temp_mirror_remote"
echo ""
echo "🔄 Aggiungo un remote temporaneo chiamato '$REMOTE_NAME'..."

# Rimuove il remote se esiste già da un'esecuzione precedente fallita
git remote remove $REMOTE_NAME &> /dev/null

git remote add $REMOTE_NAME "$NEW_REPO_URL"

# Verifica che il remote sia stato aggiunto correttamente
if ! git remote -v | grep -q "$REMOTE_NAME"; then
    echo "❌ Errore: impossibile aggiungere il remote. Controlla l'URL e riprova."
    exit 1
fi

echo "✅ Remote aggiunto con successo."

# --- 3. Esegue il Push Mirror ---
echo ""
echo "🚀 Eseguo il push mirror verso la nuova repository..."
echo "Potrebbe essere richiesta l'autenticazione per GitHub."

git push $REMOTE_NAME --mirror

# Controlla l'esito del push
if [ $? -eq 0 ]; then
  echo ""
  echo "✔️ Operazione completata con successo!"
  echo "La repository è stata duplicata in: $NEW_REPO_URL"
else
  echo ""
  echo "❌ Errore durante il push. Controlla i messaggi di errore qui sopra."
  echo "Il problema potrebbe essere legato ai permessi o all'URL errato."
fi

# --- 4. Rimuove il remote temporaneo per pulizia ---
echo ""
echo "🧹 Rimuovo il remote temporaneo..."
git remote remove $REMOTE_NAME
echo "✅ Pulizia completata."