#!/bin/bash
# incolla questo -> bash v_gits/git_push.sh

# Spostati nella root del progetto se lo script è eseguito da altrove
cd "$(dirname "$0")"

echo "🔍 Verifico lo stato del repository..."
git status

echo
echo "✍️  Inserisci un messaggio per il commit:"
read COMMIT_MSG

echo
echo "📦 Aggiungo tutti i file modificati..."
git add .

echo "📝 Eseguo il commit..."
git commit -m "$COMMIT_MSG"

echo "⬆️  Faccio il push su 'main'..."
git push origin main

echo "✅ Push completato!"