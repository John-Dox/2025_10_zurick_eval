# git_push.ps1

# Potresti dover prima abilitare l'esecuzione di script con il comando
#(da eseguire una volta come amministratore): Set-ExecutionPolicy RemoteSigned.
#Poi, dal terminale PowerShell, lancia lo script con: .\git_push.ps1

# Chiede il messaggio di commit all'utente
$COMMIT_MSG = Read-Host -Prompt "Inserisci un messaggio per il commit"

# Controlla se il messaggio è vuoto
if (-not $COMMIT_MSG) {
    Write-Output "Errore: Il messaggio di commit non può essere vuoto."
    exit 1
}

Write-Output "✅ Verifico lo stato del repository..."
git status

Write-Output "✅ Aggiungo tutti i file modificati..."
git add .

Write-Output "✅ Eseguo il commit..."
git commit -m "$COMMIT_MSG"

Write-Output "⬆️ Faccio il push su 'main'..."
git push origin main

Write-Output "✔️ Push completato!"