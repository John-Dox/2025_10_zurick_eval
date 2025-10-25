#1. Nel terminale Bash del tuo Codespaces, lancia questo comando una sola volta:
# bash chmod +x clone_to_new_repo2.sh

#2. Ora, lancia lo script:
# bash ./clone_to_new_repo2.sh


#!/bin/bash

# Script per duplicare una repository remota in un'altra usando un Personal Access Token (PAT).

# --- 1. Raccolta Interattiva dei Dati ---
echo "--- Configurazione Duplicazione Repository (con Token) ---"
echo ""

# Chiede il token
echo "Per favore, incolla il tuo Personal Access Token (PAT) di GitHub:"
read -s GITHUB_PAT  # L'opzione -s nasconde l'input mentre scrivi

if [ -z "$GITHUB_PAT" ]; then
    echo "❌ Errore: Token non inserito. Operazione annullata."
    exit 1
fi

# Chiede gli URL (già impostati con i tuoi default)
OLD_REPO_DEFAULT="https://github.com/John-Dox/20250622_structure.git"
NEW_REPO_DEFAULT="https://github.com/John-Dox/20250624_cost.git"

echo ""
read -p "URL repository di ORIGINE [${OLD_REPO_DEFAULT}]: " OLD_REPO_URL
OLD_REPO_URL=${OLD_REPO_URL:-$OLD_REPO_DEFAULT}

read -p "URL repository di DESTINAZIONE [${NEW_REPO_DEFAULT}]: " NEW_REPO_URL
NEW_REPO_URL=${NEW_REPO_URL:-$NEW_REPO_DEFAULT}

echo "--------------------------"
read -p "Procedere? (s/n): " CONFIRM
if [[ "$CONFIRM" != "s" && "$CONFIRM" != "S" ]]; then
    echo "Operazione annullata."
    exit 1
fi

# --- 2. Costruzione degli URL con Autenticazione ---
# Inseriamo il token nell'URL. Il formato è https://<token>@github.com/...
# Prima rimuoviamo "https://" dall'URL originale
OLD_REPO_URL_AUTH="https://${GITHUB_PAT}@${OLD_REPO_URL#https://}"
NEW_REPO_URL_AUTH="https://${GITHUB_PAT}@${NEW_REPO_URL#https://}"

# --- 3. Duplicazione della Repository ---
TEMP_DIR=$(mktemp -d)
echo ""
echo "🔄 Inizio duplicazione... (verrà usata una cartella temporanea)"
cd "$TEMP_DIR"

echo "1/2: Eseguo un clone 'nudo' della repository di origine (con autenticazione)..."
git clone --bare "$OLD_REPO_URL_AUTH" .
if [ $? -ne 0 ]; then 
    echo "❌ Errore nel clonare la repository di origine. Controlla l'URL e che il token abbia i permessi 'repo'."
    rm -rf "$TEMP_DIR"
    exit 1
fi

echo "2/2: Eseguo il push 'mirror' alla repository di destinazione (con autenticazione)..."
git push --mirror "$NEW_REPO_URL_AUTH"
if [ $? -ne 0 ]; then 
    echo "❌ Errore nel push alla repository di destinazione. Controlla l'URL e che il token abbia i permessi 'repo'."
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Pulizia
cd ..
rm -rf "$TEMP_DIR"

echo ""
echo "✔️ Processo completato con successo!"
echo "La repository è stata duplicata in: $NEW_REPO_URL"
