import os
import MySQLdb
import telepot
import logging
from dotenv import load_dotenv

# Carica le variabili d'ambiente
load_dotenv()

# leggi le credenziali per le API di Telegram e l'accesso ai database
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telepot.Bot(os.getenv("TELEGRAM_BOT_TOKEN"))

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

# Impostazione del livello di debug
logging.basicConfig(level=logging.INFO)

# log - inizio codice
logging.info("Inizio dell'esecuzione del codice")

# log - database degli utenti
logging.info("Connessione al database degli utenti")

# Connessione al database degli utenti
database_utenti = MySQLdb.connect(db=db_utenti, **db_config)

# Esecuzione della query per selezionare chat_id e Zona1-6 dove notifica=1
cursore_utenti = database_utenti.cursor()
cursore_utenti.execute("SELECT chat_id, Zona1, Zona2, Zona3, Zona4, Zona5, Zona6 FROM utenti WHERE notifica=1")

# Recupero dei risultati della query
utenti = cursore_utenti.fetchall()

if not utenti:
    cursore_utenti.close()
    database_utenti.close()
    logging.info("Nessun utente registrato")
else:
    logging.info("Connessione al database delle zone")
    
    # Connessione al database delle zone
    database_zone = MySQLdb.connect(db=db_seta, **db_config)

    for utente in utenti:
        chat_id = utente[0]
        zone_list = utente[1:]

        for zona in zone_list:
            if zona is None:
                continue

            messaggio = ''
            comune_trovato = False

            cursore_zone = database_zone.cursor()
            cursore_zone.execute(f"SELECT * FROM {zona} WHERE date=DATE_ADD(CURDATE(), INTERVAL 1 DAY)")
            ritiri = cursore_zone.fetchone()

            if ritiri and 1 in ritiri[1:]:
                for comune in comuni.values():
                    if isinstance(comune, Zona) and zona in comune.zone_codici:
                        messaggio += f"🔔 Avviso raccolta! 📍 *{comune.zone_nomi[comune.zone_codici.index(zona)]}* di *{comune.nome}*\n\n"
                        comune_trovato = True
                        break
                    elif isinstance(comune, Comune) and comune.codice == zona:
                        messaggio += f"🔔 Avviso raccolta! 📍 *{comune.nome}*\n\n"
                        comune_trovato = True
                        break

                if ritiri[1]: messaggio += "🗑️ Indifferenziato\n"
                if ritiri[2]: messaggio += "🥕 Organico\n"
                if ritiri[3]: messaggio += "📦 Carta e cartone\n"
                if ritiri[4]: messaggio += "🫙 Vetro e Alluminio\n"
                if ritiri[5]: messaggio += "🥤 Plastica\n"
                if ritiri[6]: messaggio += "🌿 Sfalci\n"

                try:
                    logging.info(f"Invio notifica all'utente {chat_id} in corso")
                    messaggio += "\n🕕 Domani dalle 06.00 alle 18.30"
                    bot.sendMessage(chat_id, messaggio, parse_mode='Markdown')
                    logging.info(f"Messaggio inviato all'utente {chat_id}")
                except telepot.exception.BotWasBlockedError:
                    logging.warning(f"L'utente {chat_id} ha bloccato il bot")

    cursore_zone.close()
    database_zone.close()

# log- chiusura database
logging.info("Chiusa la connessione al database")
