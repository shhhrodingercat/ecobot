from flask import Flask, request
import telepot
from telepot.namedtuple import InlineKeyboardButton, InlineKeyboardMarkup
import MySQLdb
from datetime import datetime, date, timedelta

# Carica le variabili d'ambiente dal file .env
load_dotenv()

# leggi le credenziali per le API di Telegram e l'accesso ai database
secret = os.getenv("WEBHOOK_SECRET")
base_url = os.getenv("WEBHOOK_URL")
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telepot.Bot(os.getenv("TELEGRAM_BOT_TOKEN"))

webhook_url = f"{base_url}/{secret}"
bot.setWebhook(webhook_url, max_connections=1)

connessione_utenti = {
    'host': os.getenv("DB_HOST"),
    'user': os.getenv("DB_USER"),
    'password': os.getenv("DB_PASSWORD"),
    'database': os.getenv("DB_NAME_UTENTI")
}

connessione_zone = {
    'host': os.getenv("DB_HOST"),
    'user': os.getenv("DB_USER"),
    'password': os.getenv("DB_PASSWORD"),
    'database': os.getenv("DB_NAME_ZONE")
}

app = Flask(__name__)

def start_message(chat_id):
    messaggio_benvenuto = "🤖 Ciao! Mi chiamo EcoBot e posso aiutarti a ricordare i giorni della *raccolta differenziata porta a porta* (al momento il servizio copre solo i Comuni della provincia di Torino serviti da Seta S.p.a.)"
    messaggio_benvenuto += "\n\n📍 Per iniziare, *aggiungi il tuo Comune* con il comando /aggiungiutenza. Poi potrai chiedermi le raccolte di domani, attivare le notifiche e molto altro. Se hai dubbi, consulta la /guida. Usa il Menu in basso a sinistra per interagire con me. Buon riciclo ♻️"

    bot.sendMessage(chat_id, messaggio_benvenuto, parse_mode= 'Markdown')

def help_message(chat_id):
    messaggio_guida = "🤖 Utilizza questi comandi per comunicare con il bot:"
    messaggio_guida += "\n\n/aggiungiutenza - *Selezione il Comune o la Zona di interesse*. Una volta aggiunta un'utenza, potrai attivare le notifiche che ti ricorderanno quale raccolta verrà eseguita il giorno successivo o consultare le prossime raccolte a seconda del rifiuto selezionato (massimo 6 utenze)."
    messaggio_guida += "\n\n/rimuoviutenza - Seleziona questo comando per *rimuovere un'utenza* precedentemente registrata."
    messaggio_guida += "\n\n/mieutenze - Seleziona questo comando per *elencare tutte le utenze da te registrate*."
    messaggio_guida += "\n\n/notificaon - Seleziona questo comando per *attivare le notifiche*. Ogni giorno, alle 18.30, riceverai un messaggio con indicate le raccolte del giorno successivo. Le notifiche si attivano per tutte le utenze."
    messaggio_guida += "\n\n/notificaoff - Seleziona questo comando per *disattivare le notifiche*. Non riceverai più il messaggio delle 18.30, ma le tue utenze rimarranno registrate. Le notifiche si disattivano per tutte le utenze."
    messaggio_guida += "\n\n/domani - Seleziona questo comando per conoscere *quali raccolte verranno eseguite domani*, per tutte le utenze che hai registrato."
    messaggio_guida += "\n\n/prossimaraccolta - Seleziona questo comando per conoscere *la data successiva di raccolta* in base al rifiuto selezionato (giorno corrente escluso), per tutte le utenze che hai registrato."
    messaggio_guida += "\n\n/eliminatutto - Seleziona questo comando per *eliminare tutti i tuoi dati* dal database del bot."
    messaggio_guida += "\n\n/sviluppatore - Seleziona questo comando per conoscere i dettagli di *chi ha sviluppato questo bot*."

    bot.sendMessage(chat_id, messaggio_guida, parse_mode= 'Markdown')

def on_callback_query(update):
    query_id, from_id, callback_data = telepot.glance(update, flavor='callback_query')
    print('Callback query:', query_id, from_id, callback_data)

def inserisci_zona(chat_id, codice_comune):
    # Mi connetto al database degli utenti
    db = MySQLdb.connect(**connessione_utenti)

    # Creo il cursore della query
    cursore_utente = db.cursor()
    cursore_utente.execute("SELECT * FROM utenti WHERE chat_id=%s", (chat_id,))
    utente = cursore_utente.fetchone()

    if utente is not None:
        # L'utente è già registrato, controllo gli altri casi
        cursore_zone = db.cursor()
        cursore_zone.execute("SELECT Zona1, Zona2, Zona3, Zona4, Zona5, Zona6 FROM utenti WHERE chat_id = %s", (chat_id,))
        zone = cursore_zone.fetchone()
        colonne_disponibili = [i for i, colonna in enumerate(zone) if colonna is None]

        # Controllo che l'utente abbia ancora disponibili
        if not colonne_disponibili:
            # L'utente ha già registrato tutte le zone disponibili
            cursore_utente.close()
            cursore_zone.close()
            db.close()
            return "pieno"

        # Controllo che l'utente non sia registrando nuovamente la stessa zona
        elif str(codice_comune) in zone:
            cursore_utente.close()
            cursore_zone.close()
            db.close()
            return "presente"

        else:
            # L'utente è presente e ha ancora zone disponibili
            prima_colonna_disponibile = colonne_disponibili[0] + 1
            cursore_zone.execute("UPDATE utenti SET Zona{} = '{}' WHERE chat_id = {}".format(prima_colonna_disponibile, codice_comune, chat_id))
            cursore_zone.close()
            db.commit()
            cursore_utente.close()
            db.close()
            return "successo"

    else:
        # Nuovo utente, registro il comune nella Zona1
        cursore_utente.execute(f"INSERT INTO utenti (chat_id, Zona1) VALUES ('{chat_id}', '{codice_comune}')")
        cursore_utente.close()
        db.commit()
        db.close()
        return "successo"

def rimuovi_zona(chat_id, codice_comune):
    # Mi connetto al database degli utenti
    db = MySQLdb.connect(**connessione_utenti)

    # Creo il cursore della query
    query = "UPDATE utenti SET Zona1=NULLIF(Zona1, %(codice_comune)s), Zona2=NULLIF(Zona2, %(codice_comune)s), Zona3=NULLIF(Zona3, %(codice_comune)s), Zona4=NULLIF(Zona4, %(codice_comune)s), Zona5=NULLIF(Zona5, %(codice_comune)s), Zona6=NULLIF(Zona6, %(codice_comune)s) WHERE chat_id=%(chat_id)s"
    cursore_zona = db.cursor()
    cursore_zona.execute(query, {'codice_comune': codice_comune, 'chat_id': chat_id})
    db.commit()
    db.close()
    return "successo"

def leggi_zone(chat_id):
    # Mi connetto al database degli utenti
    db = MySQLdb.connect(**connessione_utenti)

    # Creo il cursore della query
    cursore_utentezone = db.cursor()
    cursore_utentezone.execute("SELECT Zona1, Zona2, Zona3, Zona4, Zona5, Zona6 FROM utenti WHERE chat_id=%s", (chat_id,))
    zone = cursore_utentezone.fetchone()
    cursore_utentezone.close()
    db.close()

    # Se l'utente non ha registrato nessuna zona
    if zone is None or all(zone[i] is None for i in range(len(zone))):
        return "assente"

    return list(zone)

def attiva_notifica(chat_id):
    # Mi connetto al database degli utenti
    db = MySQLdb.connect(**connessione_utenti)
    cursore_notifica = db.cursor()

    # Query per modificare il valore di "notifica" a 1 nella riga specificata da "chat_id"
    sql = "UPDATE utenti SET notifica = 1 WHERE chat_id = %s"
    val = (chat_id,)

    # Esecuzione della query
    cursore_notifica.execute(sql, val)

    # Salvataggio delle modifiche e chiusura della connessione
    db.commit()
    cursore_notifica.close()
    db.close()

def disattiva_notifica(chat_id):
    # Mi connetto al database degli utenti
    db = MySQLdb.connect(**connessione_utenti)
    cursore_notifica = db.cursor()

    # Query per modificare il valore di "notifica" a 1 nella riga specificata da "chat_id"
    sql = "UPDATE utenti SET notifica = 0 WHERE chat_id = %s"
    val = (chat_id,)

    # Esecuzione della query
    cursore_notifica.execute(sql, val)

    # Salvataggio delle modifiche e chiusura della connessione
    db.commit()
    cursore_notifica.close()
    db.close()

def elimina_riga(chat_id):
    # Mi connetto al database degli utenti
    db = MySQLdb.connect(**connessione_utenti)
    cursore_elimina= db.cursor()

    # Query per modificare il valore di "notifica" a 1 nella riga specificata da "chat_id"
    sql = "DELETE FROM utenti WHERE chat_id = %s"
    val = (chat_id,)

    # Esecuzione della query
    cursore_elimina.execute(sql, val)

    # Salvataggio delle modifiche e chiusura della connessione
    db.commit()
    cursore_elimina.close()
    db.close()

def utente_presente(chat_id):
    # Mi connetto al database degli utenti
    db = MySQLdb.connect(**connessione_utenti)
    cursore_utentepresente = db.cursor()

    # Query per controllare se il valore esiste nella colonna "chat_id"
    sql = "SELECT * FROM utenti WHERE chat_id = %s"
    val = (chat_id,)

    # Esecuzione della query
    cursore_utentepresente.execute(sql, val)

    # Controllo del risultato della query
    if cursore_utentepresente.fetchone() is not None:
        return "presente"
    else:
        return "assente"

    # Chiusura della connessione
    cursore_utentepresente.close()
    db.close()

def domani(chat_id):
    # Connessione al database degli utenti
    database_utenti = MySQLdb.connect(**connessione_utenti)
    cursore_zoneregistrate = database_utenti.cursor()

    # Ottieni i codici delle zone a cui l'utente è registrato
    cursore_zoneregistrate.execute("SELECT Zona1, Zona2, Zona3, Zona4, Zona5, Zona6 FROM utenti WHERE chat_id=%s", (chat_id,))
    result = cursore_zoneregistrate.fetchone()
    if result:
        zone_codici = [zona for zona in result if zona is not None]

    else:
        zone_codici = []

    # Chiudi la connessione al database 
    database_utenti.close()

    # Ottieni la data di domani
    domani = date.today() + timedelta(days=1)

    # Connessione al database delle zone
    database_zone = MySQLdb.connect(**connessione_zone)
    cursore_domani = database_zone.cursor()

    # Analizza le tabelle con i codici estratti 
    risultati = {}

    for codice in zone_codici:
        cursore_domani.execute(f"SELECT i, o, c, v, p, s FROM {codice} WHERE date=%s", (domani,))
        result = cursore_domani.fetchone()

        if result:
            colonne_attive = [rifiuti[colonna] for colonna, valore in zip(["i", "o", "c", "v", "p", "s"], result) if valore]
            risultati[codice] = colonne_attive

        else:
            risultati[codice] = "nessuno"

    # Chiudi la connessione al database
    database_zone.close()

    return risultati

def prossima_raccolta(chat_id, rifiuto):
    # Connessione al database degli utenti
    database_utenti = MySQLdb.connect(**connessione_utenti)
    cursore_zoneregistrate = database_utenti.cursor()

    # Ottieni i codici delle zone a cui l'utente è registrato
    cursore_zoneregistrate.execute("SELECT Zona1, Zona2, Zona3, Zona4, Zona5, Zona6 FROM utenti WHERE chat_id=%s", (chat_id,))
    result = cursore_zoneregistrate.fetchone()
    if result:
        zone_codici = [zona for zona in result if zona is not None]
    else:
            zone_codici = []

    # Chiudi la connessione al database degli utenti
    database_utenti.close()

    # Ottieni la data di domani
    domani = date.today() + timedelta(days=1)

    if rifiuto == "i":
        rifiuto = 1
    elif rifiuto == "o":
        rifiuto = 2
    elif rifiuto == "c":
        rifiuto = 3
    elif rifiuto == "v":
        rifiuto = 4
    elif rifiuto == "p":
        rifiuto = 5
    elif rifiuto == "s":
        rifiuto = 6

    # Connessione al database delle zone
    database_zone = MySQLdb.connect(**connessione_zone)
    cursore_prossima = database_zone.cursor()

    # per ogni zona estraggo la prima raccolta disponibile per il rifiuto scelto
    giorni = {}

    for codice in zone_codici:
        # esecuzione della query
        cursore_prossima.execute(f"SELECT * FROM {codice} WHERE date >= '{domani}' ORDER BY date")

        # Inizializzazione della lista per le date con value=1

        for row in cursore_prossima.fetchall():
            data = row[0]
            valore = row[rifiuto]

            if valore == 1:
                giorni[codice] = data
                break
            else:
                giorni[codice] = "nessuno"

    # Chiudi la connessione al database delle zone
    database_zone.close()

    return giorni


class Comune:
    def __init__(self, codice, nome):
        self.codice = codice
        self.nome = nome

class Zona(Comune):
    def __init__(self, codice, nome, zone_codici, zone_nomi):
        super().__init__(codice, nome)
        self.zone_codici = zone_codici
        self.zone_nomi = zone_nomi

# Definisco il dizionario dei codici dei comuni e delle loro zone, al quale devono corrispondere i nomi delle tabelle nel database
comuni = {

'borgaro': Zona("", "Borgaro Torinese", ["x001", "x002"], ["Zona A", "Zona B"]),
'brandizzo':  Zona("", "Brandizzo", ["x005", "x006", "x007"], ["Zona 1", "Zona 2", "Zona 3"]),
'brozolo': Comune("x008", "Brozolo"),
'brusasco': Comune("x064", "Brusasco"),
'casalborgone': Comune("x009", "Casalborgone"),
'caselle': Zona("", "Caselle Torinese", ["x010", "x011", "x012", "x013", "x014"], ["Zona 1", "Zona 2", "Zona 3", "Zona 4", "Zona 5"]),
'castagneto': Comune("x015", "Castagneto Po"),
'castiglione': Zona("", "Castiglione Torinese", ["x016", "x017"], ["Zona 1", "Zona 2"]),
'cavagnolo': Comune("x018", "Cavagnolo"),
'chivasso': Zona("", "Chivasso", ["x019", "x020", "x021", "x022", "x023", "x024"], ["Zona 1", "Zona 2", "Zona 3", "Zona 4", "Zona 5", "Zona 6"]),
'cinzano': Comune("x025", "Cinzano"),
'foglizzo': Comune("x026", "Foglizzo"),
'gassino': Zona("", "Gassino Torinese", ["x027", "x028", "x029"], ["Zona 3", "Zona 4", "Zona 4 BIS"]),
'lauriano': Comune("x030", "Lauriano"),
'leini': Zona("", "Leinì", ["x031", "x032", "x033", "x034", "x035", "x036"], ["Zona 1", "Zona 2", "Zona 3", "Zona 4", "Zona 5", "Zona 6"]),
'lombardore': Comune("x037", "Lombardore"),
'mappano': Comune("x038", "Mappano"),
'montanaro': Zona("", "Montanaro", ["x039", "x040"], ["Zona 1", "Zona 2"]),
'monteu': Comune("x041", "Monteu da Po"),
'rivalba': Comune("x042", "Rivalba"),
'rondissone': Comune("x043", "Rondissone"),
'sanbenigno': Zona("", "San Benigno", ["x044", "x045"], ["Zona Nord", "Zona Sud"]),
'sanmauro': Zona("", "San Mauro Torinese", ["x046", "x047"], ["Zona Capoluogo", "Zona Oltrepo"]),
'sanraffaele': Comune("x048", "San Raffaele Cimena"),
'sansebastiano': Comune("x049", "San Sebastiano da Po"),
'sciolze': Comune("x050", "Sciolze"),
'settimo': Zona("", "Settimo Torinese", ["x051", "x052", "x053", "x054", "x055", "x056"], ["Zona 1", "Zona 2", "Zona 3", "Zona 4", "Zona 5", "Zona 6"]),
'torrazza': Comune("x057", "Torrazza Piemonte"),
'verolengo': Zona("", "Verolengo", ["x058", "x059"], ["Zona 1", "Zona 2"]),
'verrua': Comune("x060", "Verrua Savoia"),
'volpiano': Zona("", "Volpiano", ["x061", "x062", "x063"], ["Zona Centro", "Zona Est", "Zona Ovest"]),

}

rifiuti = {

"i": "🗑️ *Indifferenziato*",
"o": "🥕 *Organico*",
"c": "📦 *Carta e cartone*",
"v": "🫙 *Vetro e Alluminio*",
"p": "🥤 *Plastica*",
"s": "🌿 *Sfalci*"

}

#Funzione principale di Webhook
@app.route('/{}'.format(secret), methods=["POST"])
def telegram_webhook():
    update = request.get_json()

    chat_id = None
    text = None
    callback_data = None
    codici = None
    codice = None
    comune = None
    codice_comune = None
    rimuovi_codice = None
    utenze_trovate = None
    keyboard = None

    # Innanzitutto, devo distinguere se si tratta di un comando o di una callback, e ignorare foto, video, documenti e ogni genere di allegato
    # Update di una callback
    if "callback_query" in update:
            query = update["callback_query"]
            chat_id = query["message"]["chat"]["id"]
            callback_data = query["data"]

            if callback_data.startswith('x'):

                # La callback inizia con una "x", quindi è un codice di un Comune senza zone o di una zona di un Comune
                codice_comune = callback_data
                str(codice_comune)

                # Provo a inserirla nel database
                result = inserisci_zona(chat_id, codice_comune)

                if result == "pieno":
                    bot.sendMessage(chat_id, "❌ Hai raggiunto il massimo di utenze!\n\nPer aggiungerne una nuova, devi prima eliminarne una premendo sull'opzione /rimuoviutenza dal Menu del bot")
                    return "OK"

                elif result == "presente":
                    bot.sendMessage(chat_id, "❌ Utenza già registrata")
                    return "OK"

                elif result == "successo":

                    # Identifico il nome del comune di riferimento e comunico all'utente il corretto inserimento
                    for comune in comuni.values():

                        if isinstance(comune, Zona) and callback_data in comune.zone_codici:
                            bot.sendMessage(chat_id, f"✅ Ok, ho aggiunto la {comune.zone_nomi[comune.zone_codici.index(callback_data)]} di {comune.nome} alle tue utenze!\n\nRicordati che se vuoi ricevere la notifica delle 18.30, la devi attivare del Menu")
                            return "OK"
                            break

                        elif comune.codice == callback_data:
                            bot.sendMessage(chat_id, f"✅ Ok, ho aggiunto {comune.nome} alle tue utenze!\n\nRicordati che se vuoi ricevere la notifica delle 18.30, la devi attivare del Menu")
                            return "OK"
                            break

            elif callback_data.startswith('w'):

                # La callback inizia con una "w", quindi è una richiesta di rimozione dal database
                rimuovi_utenza = callback_data
                str(rimuovi_utenza)
                codice_comune = 'x' + rimuovi_utenza[1:]
                str(codice_comune)
                result = rimuovi_zona(chat_id, codice_comune)

                if result == "successo":
                    bot.sendMessage(chat_id, "✅ Fatto! Utenza eliminata!")
                    return "OK"
                else:
                    bot.sendMessage(chat_id, "❌ Errore")
                    return "OK"

            elif callback_data in comuni and isinstance(comuni[callback_data], Zona):
                # Recupero la lista di codici zone e nomi zone
                zona_codice = comuni[callback_data].zone_codici
                zona_nome = comuni[callback_data].zone_nomi

                # Creo una tastiera inline con i bottoni corrispondenti alle zone
                keyboard = []

                for codice, nome in zip(zona_codice, zona_nome):
                    keyboard.append([InlineKeyboardButton(text=nome, callback_data=codice)])

                # Invio la tastiera inline al chat_id corrente
                bot.sendMessage(chat_id, text=f"🏠 Ok, *{comuni[callback_data].nome}*! Ora scegli la Zona che ti interessa. Se non sai a che zona appartiene la tua utenza, consulta l'Ecocalendario sul sito di Seta: https://www.setaspa.com/comuni 👇", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode= 'Markdown')
                return "OK"

            elif callback_data == "cancella":
                elimina_riga(chat_id)
                result = utente_presente(chat_id)
                if result == "assente":
                    bot.sendMessage(chat_id, "✅ Ok, ho eliminato tutti i dati registrati")
                    return "OK"
                else:
                    bot.sendMessage(chat_id, "⚠️ C'è stato un problema nell'eliminazione dei tuoi dati. Se hai problemi con questo bot contatta lo /sviluppatore")
                    return "OK"

            elif callback_data in ["i", "o", "c", "v", "p", "s"]:
                rifiuto = callback_data
                raccolte = prossima_raccolta(chat_id, rifiuto)

                prossime_raccolte = []

                if rifiuto == "i":
                    prossime_raccolte.append("🗑️ *Indifferenziato*. Ecco le prossime date di raccolte per le utenze registrate:\n")
                elif rifiuto == "o":
                    prossime_raccolte.append("🥕 *Organico*. Ecco le prossime date di raccolte per le utenze registrate:\n")
                elif rifiuto == "c":
                    prossime_raccolte.append("📦 *Carta e cartone*. Ecco le prossime date di raccolte per le utenze registrate:\n")
                elif rifiuto == "v":
                    prossime_raccolte.append("🫙 *Vetro e alluminio*. Ecco le prossime date di raccolte per le utenze registrate:\n")
                elif rifiuto == "p":
                    prossime_raccolte.append("🥤 *Plastica*. Ecco le prossime date di raccolte per le utenze registrate:\n")
                elif rifiuto == "s":
                    prossime_raccolte.append("🌿 *Sfalci*. Attenzione, il servizio di raccolta sfalci viene effettuato in modo differente. Per maggiori informazioni, visita il sito web di Seta (https://www.setaspa.com/contatti/156-servizi/845-servizio-raccolta-sfalci) o telefona al 800401692. Ecco le prossime date di raccolte per le utenze registrate:\n")


                for utenza, data in raccolte.items():
                    comune_trovato = False

                    for comune in comuni.values():
                        if isinstance(comune, Zona) and utenza in comune.zone_codici:
                            prossime_raccolte.append(f"📍 *{comune.zone_nomi[comune.zone_codici.index(utenza)]}* di *{comune.nome}*")
                            comune_trovato = True
                            break

                        elif isinstance(comune, Comune) and comune.codice == utenza:
                            prossime_raccolte.append(f"📍 *{comune.nome}*")
                            comune_trovato = True
                            break

                        if not comune_trovato:
                            continue

                    if data == "nessuno":
                        prossime_raccolte.append("❌  Nessun ritiro previsto")
                        prossime_raccolte.append("")

                    else:
                        data_stringa = data.strftime('%Y-%m-%d')
                        data_datetime = datetime.strptime(data_stringa, '%Y-%m-%d')

                        # genera la stringa nel formato desiderato in italiano
                        giorni_settimana = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
                        mesi_anno = ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno', 'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre']

                        data_formattata = data_datetime.strftime('%A %d %B %Y').replace(data_datetime.strftime('%A'), giorni_settimana[data_datetime.weekday()]).replace(data_datetime.strftime('%B'), mesi_anno[data_datetime.month-1])
                        data_formattata = " ".join([word.capitalize() for word in data_formattata.split()])

                        prossime_raccolte.append(f"📅 {data_formattata}")
                        prossime_raccolte.append("")

                bot.sendMessage(chat_id, "\n".join(prossime_raccolte),parse_mode= 'Markdown')
                return "OK"


    # Update di un messaggio
    elif "message" in update:
        chat_id = update["message"]["chat"]["id"]

        if "text" in update["message"]:
            text = update["message"]["text"]
        else:
            # Ignora il messaggio se contiene un allegato
            bot.sendMessage(chat_id, "Mi dispiace, il bot non supporta l'invio di allegati.")
            return "OK"

        if text.startswith('/'):
            # il messaggio inizia con una barra "/", quindi è un comando
            command = text.split()[0][1:]  # rimuovi la barra e dividi il testo


            if command == 'aggiungiutenza':

                keyboard = []

                for comune in comuni.values():

                    if isinstance(comune, Zona):
                        keyboard.append([InlineKeyboardButton(text=f"📍 {comune.nome}", callback_data=list(comuni.keys())[list(comuni.values()).index(comune)])])

                    else:
                        keyboard.append([InlineKeyboardButton(text=f"📍 {comune.nome}", callback_data=comune.codice)])

                bot.sendMessage(chat_id, text="Scegli il comune che ti interessa:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
                return "OK"

            elif command == 'rimuoviutenza':

                # Rimuovi un'utenza
                codici = leggi_zone(chat_id)
                if codici == "assente":
                    bot.sendMessage(chat_id, "❌ Non hai ancora registrato utenze")
                    return "OK"

                else:
                    utenze_trovate = []

                    for codice in codici:

                        for comune in comuni.values():

                            if isinstance(comune, Zona) and codice in comune.zone_codici:
                                rimuovi_codice = 'w' + codice[1:]
                                utenze_trovate = utenze_trovate + [InlineKeyboardButton(text=comune.zone_nomi[comune.zone_codici.index(codice)] + ' di ' + comune.nome, callback_data=rimuovi_codice)]

                            elif isinstance(comune, Comune) and comune.codice == codice:
                                rimuovi_codice = 'w' + codice[1:]
                                utenze_trovate = utenze_trovate + [InlineKeyboardButton(text=comune.nome, callback_data=rimuovi_codice)]

                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [comune] for comune in utenze_trovate
                    ])

                    bot.sendMessage(chat_id, 'Scegli l\'utenza che vuoi eliminare:', reply_markup=keyboard)
                    return "OK"


            elif command == 'mieutenze':

                # Elenca le utenze registrate
                codici = leggi_zone(chat_id)

                if codici == "assente":
                    bot.sendMessage(chat_id, "❌ Non hai ancora registrato utenze")
                    return "OK"

                else:
                    utenze_trovate = []

                    for codice in codici:

                        for comune in comuni.values():
                            if isinstance(comune, Zona) and codice in comune.zone_codici:
                                utenze_trovate.append(f"📍 *{comune.zone_nomi[comune.zone_codici.index(codice)]}* di *{comune.nome}*\n")

                            elif isinstance(comune, Comune) and comune.codice == codice:
                                utenze_trovate.append(f"📍 *{comune.nome}*\n")

                    bot.sendMessage(chat_id, "Ecco le utenze che hai registrato 👇\n\n" + "\n".join(utenze_trovate), parse_mode= 'Markdown')
                    return "OK"


            elif command == 'notificaon':

                codici = leggi_zone(chat_id)
                if codici == "assente":
                    bot.sendMessage(chat_id, "❌ Non hai ancora registrato utenze. Se vuoi ricevere ogni giorno alle 18.30 il messaggio che ti ricorda le raccolte di domani, devi prima registrare la tua utenza con il comando /aggiungiutenza")
                    return "OK"

                else:
                    # Attiva o disattiva le notifiche
                    attiva_notifica(chat_id)
                    bot.sendMessage(chat_id, "🔔 *Notifiche attivate!*\n\nDa questo momento, riceverai ogni giorno alle 18.30 un messaggio che ti ricorderà quale raccolta verrà effettuata il giorno successivo, per tutte le utenze che hai registrato.", parse_mode= 'Markdown')
                    return "OK"

            elif command == 'notificaoff':

                codici = leggi_zone(chat_id)
                if codici == "assente":
                    bot.sendMessage(chat_id, "❌ Non hai ancora registrato utenze. Non riceverai nessuna notifica finchè non aggiungi almeno un'utenza con il comando /aggiunginutenza e non attivi le notifiche con il comando /notificaon")
                    return "OK"

                else:
                    # Attiva o disattiva le notifiche
                    disattiva_notifica(chat_id)
                    bot.sendMessage(chat_id, "🔕 *Notifiche disattivate!*\n\nDa questo momento, non riceverai più nessun avviso riguardo la raccolta prevista per il giorno successivo, per nessuna utenza. Se invece vuoi eliminare un'utenza, lo puoi fare con il comando /rimuoviutenza", parse_mode= 'Markdown')
                    return "OK"

            # Indica le raccolte di domani
            elif command == 'domani':

                codici = leggi_zone(chat_id)
                if codici == "assente":
                    bot.sendMessage(chat_id, "❌ Non hai ancora registrato utenze")
                    return "OK"
                else:
                    ritiri_domani = []
                    ritiri_domani.append("📅 Ecco i ritiri di domani per le utenze che hai registrato:\n")
                    ritiri = domani(chat_id)

                    if ritiri == "nessuno":
                        ritiri_domani.append("❌ Nessun ritiro previsto")
                    else:
                        for codice, colonne in ritiri.items():
                            comune_trovato = False
                            for comune in comuni.values():
                                if isinstance(comune, Zona) and codice in comune.zone_codici:
                                    ritiri_domani.append(f"📍 *{comune.zone_nomi[comune.zone_codici.index(codice)]}* di *{comune.nome}*")
                                    comune_trovato = True
                                    break

                                elif isinstance(comune, Comune) and comune.codice == codice:
                                    ritiri_domani.append(f"📍 *{comune.nome}*")
                                    comune_trovato = True
                                    break

                            if not comune_trovato:
                                continue

                            colonne_str = "\n".join(map(str, colonne))
                            if colonne_str:
                                ritiri_domani.append(colonne_str)
                                ritiri_domani.append("")
                            else:
                                ritiri_domani.append("❌ Nessun ritiro previsto per domani\n")

                    bot.sendMessage(chat_id, "\n".join(ritiri_domani), parse_mode= 'Markdown')
                    return "OK"

            # Indica la prossima raccolta in base al rifiuto selezionato
            elif command == 'prossimaraccolta':
                
                codici = leggi_zone(chat_id)

                if codici == "assente":
                    bot.sendMessage(chat_id, "❌ Non hai ancora registrato utenze")
                    return "OK"

                else:
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text='🗑️ Indifferenziato', callback_data='i')],
                        [InlineKeyboardButton(text='🥕 Organico', callback_data='o')],
                        [InlineKeyboardButton(text='📦 Carta e cartone', callback_data='c')],
                        [InlineKeyboardButton(text='🫙 Vetro e Alluminio', callback_data='v')],
                        [InlineKeyboardButton(text='🥤 Plastica', callback_data='p')],
                        [InlineKeyboardButton(text='🌿 Sfalci', callback_data='s')]
                    ])

                    bot.sendMessage(chat_id, 'Scegli il tipo di rifiuto per il quale vuoi conoscere il prossimo giorno di raccolta:\n', reply_markup=keyboard)
                    return "OK"

            elif command == 'eliminatutto':
                # Richiede la conferma di eliminazione completa dal database

                result = utente_presente(chat_id)

                if result == "assente":
                    bot.sendMessage(chat_id, "❌ Non hai ancora registrato utenze, non ci sono dati registrati")
                    return "OK"

                elif result == "presente":
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text='Confermo', callback_data='cancella')]
                    ])

                    bot.sendMessage(chat_id, '⚠️ Attenzione! Questo comando elimina tutti i dati di registrazione. Verranno eliminate tutte le tue utenze e il bot non sarà più in grado di contattarti. Potrai sempre registrarti nuovamente in seguito. Premi "Confermo" per cancellare tutti i tuoi dati', reply_markup=keyboard)
                    return "OK"

            # Indica le informazioni sullo sviluppatore
            elif command == 'sviluppatore':
                messaggio = ''
                messaggio += "🙋🏻‍♂ Questo bot è stato sviluppato da me, *Matteo Miccichè*. Sono un professionista della Comunicazione e appassionato di tecnologia."
                messaggio += "\n\n🤖 Questo bot è stato sviluppato unicamente come progetto personale e *senza nessuna affiliazione con Seta S.p.a.*"
                messaggio += "\n\n🤝 Se vuoi metterti in contatto con me, puoi aggiungermi su *LinkedIn*: https://www.linkedin.com/in/miccichematteo/."
                messaggio += "\n\n🪲 Se vuoi segnalarmi *bug o malfunzionamenti*, puoi inviarli qui: https://forms.gle/5ZyTZnKHu3tYF4dz6"
                messaggio += "\n\n✌️ Se ti piace il progetto e vuoi aiutarmi a sostenere i costi di hosting, puoi farlo qui: https://www.buymeacoffee.com/ecobot"


                bot.sendMessage(chat_id, messaggio, parse_mode= 'Markdown')
                return "OK"

            elif command == 'start':
                # Stampa il messaggio di benvenuto
                start_message(chat_id)
                return "OK"

            elif command == 'guida':
                # Stampa il messaggio di benvenuto
                help_message(chat_id)
                return "OK"

        else:
            bot.sendMessage(chat_id, "Comando sconosciuto, utilizza il Menu a sinistra per interagire con il bot")
            return "OK"

