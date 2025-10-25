#!/bin/bash

# Script per sincronizzare la cartella locale con la repository remota.
# ./git_pull.sh

echo "🔄 Tentativo di scaricare gli aggiornamenti dal repository online (origin/main)..."

# Esegue il comando 'git pull' sul branch 'main' del repository remoto 'origin'
# Il comando fa due cose:
# 1. git fetch: Scarica le informazioni sui nuovi commit dal server.
# 2. git merge: Applica quei commit al tuo branch locale.
git pull origin main

# Controlla il codice di uscita del comando precedente
# $? contiene il codice di uscita dell'ultimo comando eseguito. 0 significa successo.
if [ $? -eq 0 ]; then
  echo "✅ Pull completato con successo. La tua cartella locale è ora sincronizzata."
else
  echo "❌ Errore durante l'operazione di pull. Controlla i messaggi di errore qui sopra."
  # Esce con un codice di errore per segnalare un problema
  exit 1
fi

# Mostra un breve log degli ultimi commit per vedere cosa è cambiato
echo ""
echo "📜 Log degli ultimi 3 commit:"
git log -3 --pretty=format:"%h - %an, %ar : %s"