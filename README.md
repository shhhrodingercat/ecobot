# Configurazione dell'Architettura per il Bot Telegram

## Introduzione
Questo bot è un progetto sviluppato e mantenuto da una singola persona, senza un team dedicato e con un tempo limitato per la manutenzione. Il suo scopo è fornire notifiche automatiche sulla raccolta differenziata in specifici comuni, permettendo agli utenti di registrarsi e ricevere aggiornamenti giornalieri. La logica del bot si basa su due database MySQL distinti:

- **Database Utenti (dinamico):** registra le preferenze degli utenti, aggiornandosi ogni volta che qualcuno aggiunge o rimuove un'utenza.
- **Database Raccolte (statico):** contiene i dati delle raccolte differenziate dei vari comuni. Poiché questi dati non cambiano frequentemente, sono stati importati una volta e vengono aggiornati solo in caso di variazioni ufficiali nei calendari.

Questo approccio permette di mantenere l'operatività del bot separata dalla gestione dei dati fissi, ottimizzando le performance e riducendo il carico sul database.

## 1. Requisiti
Prima di avviare il bot, assicurati di avere:
- **Python 3.8+**
- **Flask** per gestire il webhook
- **Telepot** per interagire con l'API di Telegram
- **MySQL** come database
- **Un server accessibile via HTTPS** per ricevere gli aggiornamenti da Telegram
- **Un file `.env`** per le credenziali

## 2. Acquisizione dell'API di Telegram
Per ottenere le credenziali necessarie, segui questi passaggi:
1. Apri Telegram e cerca `@BotFather`.
2. Invia il comando `/newbot` e segui le istruzioni per creare un nuovo bot.
3. Dopo la creazione, riceverai un **token API** che dovrai aggiungere nel file `.env` come `TELEGRAM_BOT_TOKEN`.

## 3. Struttura del Bot

### Logica del Bot
Il core del chatbot è principalmente responsabile della gestione degli utenti e della popolazione del database dinamico. Il bot gestisce le interazioni con gli utenti, raccogliendo i comuni di interesse e memorizzandoli nel database utenti. Tuttavia, la vera azione di notifica avviene tramite uno script separato (`notify.py`), che esegue controlli giornalieri e invia promemoria agli utenti.

### Webhook e Secret
Il webhook è il meccanismo attraverso cui Telegram invia gli aggiornamenti al bot. Flask gestisce queste richieste e le elabora. Per sicurezza, il webhook è protetto da un `WEBHOOK_SECRET`, che assicura che solo richieste autorizzate possano raggiungere il bot. Nel codice, viene impostato così:
```python
webhook_url = f"{base_url}/{secret}"
bot.setWebhook(webhook_url, max_connections=1)
```
È importante che il server sia accessibile via HTTPS affinché Telegram possa inviare correttamente le richieste.

### Database Utenti
Una tabella che contiene le informazioni sugli utenti, inclusi i comuni (fino a 6 per utente) per cui desiderano ricevere notifiche. Questo database è dinamico, poiché gli utenti possono iscriversi o disiscriversi in qualsiasi momento. Il database contiene un'unica tabella dove a ogni riga corrisponde un utente del bot. Le colonne disponibili sono il boolean delle notifiche e le 6 colonne disponibili per registrare le proprie zone.

### Database Raccolte
Un database statico che memorizza i giorni di raccolta differenziata per tutti i 63 comuni. Dal momento che i dati sono fissi, probabilmente li hai importati una volta e li mantieni aggiornati solo in caso di variazioni nel calendario comunale.

Il database delle zone è basato sui dati estratti dagli ecocalendari di Seta S.p.a., recuperabili qui: [Seta S.p.a.](https://www.setaspa.com/comuni). All'interno della repository esiste uno script `estrattore.py` per estrarre automaticamente tutti i dati e inserirli in un foglio Excel. Il database deve essere strutturato con una tabella per ogni comune o zona per comune, alla quale corrisponde un codice univoco (consultare l'allegato `codici_comuni.txt` per sapere la corrispondenza). Ogni tabella ha una riga per giorno dell'anno in cui è associato un boolean in caso di ritiro di quel rifiuto:
- `i` = Indifferenziato
- `o` = Organico
- `c` = Carta e cartone
- `v` = Vetro
- `p` = Plastica
- `s` = Sfalci

### Script Giornaliero (`notify.py`)
Ogni giorno viene eseguito uno script (probabilmente tramite un cron job) che:
- Recupera i dati dal database statico per identificare quali rifiuti vengono raccolti in quel determinato giorno.
- Confronta queste informazioni con le zone di interesse degli utenti presenti nel database degli utenti.
- Determina chi deve essere notificato e invia il messaggio di promemoria alle **18:30**, ricordando agli utenti di mettere i bidoni sulla strada il giorno precedente.

### Script di Estrazione (`estrattore.py`)
Lo script `estrattore.py` analizza i file PDF dell'Ecocalendario di Seta S.p.a. ed estrae le informazioni sui ritiri della raccolta differenziata, trasformandole in un file Excel. Il processo prevede:
- L'analisi dei PDF per identificare i bollini colorati associati ai tipi di rifiuti.
- La conversione dei colori in valori booleani per ciascun giorno dell'anno.
- La generazione di un foglio Excel con le informazioni strutturate per ogni comune o zona.

L'inserimento in un foglio di calcolo serve a controllare manualmente la correttezza dei dati estratti. Successivamente, un altro script viene utilizzato per trasferire questi dati nel database MySQL. Questo passaggio non è incluso nella repository, poiché il metodo di importazione può variare a seconda delle esigenze e delle preferenze dell'utente.

## 4. Prova il Bot
Il bot è disponibile su Telegram e può essere provato qui: [DifferenziaBot](https://t.me/differenziabot).

## 5. Disclaimer
Questo bot è un progetto personale e non è affiliato ufficialmente con nessun ente locale o azienda responsabile della raccolta differenziata. I dati forniti possono variare rispetto alle informazioni ufficiali, quindi si consiglia di verificarli con il proprio comune di residenza. L'autore non si assume alcuna responsabilità per errori o informazioni non aggiornate.

