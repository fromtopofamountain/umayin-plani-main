import os.path
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv  # YENİ EKLENDİ

# .env dosyasını yükle
load_dotenv()

# Dosya yolunu .env'den al
CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE")

# takvimi okuma ve yazma izni v
SCOPES = ['https://www.googleapis.com/auth/calendar']

class GoogleCalendarManager:
    def __init__(self):
        self.creds = None
        # Daha önce giriş yapıldıysa token.json'dan yükle
        if os.path.exists('token.json'):
            self.creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
        # Giriş yapılmadıysa veya token süresi dolduysa
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                # CREDENTIALS_FILE kontrolü
                if not CREDENTIALS_FILE:
                    raise ValueError("HATA: .env dosyasında 'GOOGLE_CREDENTIALS_FILE' değişkeni bulunamadı!")
                
                if not os.path.exists(CREDENTIALS_FILE):
                    raise FileNotFoundError(f"HATA: '{CREDENTIALS_FILE}' dosyası bulunamadı! Lütfen dosyayı proje klasörüne koyun ve .env dosyasını kontrol edin.")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES) # Değişkeni burada kullanıyoruz
                self.creds = flow.run_local_server(port=0)
            
            # Gelecekteki girişler için token'ı kaydet
            with open('token.json', 'w') as token:
                token.write(self.creds.to_json())

        self.service = build('calendar', 'v3', credentials=self.creds)

    def parse_dates(self, date_str):
        """
        Gelen tarih formatı (Örn: '2025-01-10 - 2025-01-15') ise ayrıştırır.
        Hata olursa bugünün tarihini döner.
        """
        try:
            parts = date_str.split("-")
            # YYYY-MM-DD formatında üretiyor.
            
            if len(parts) >= 6: "2025-06-10 - 2025-06-15"
            
            clean_str = date_str.replace(" ", "")
            if "to" in clean_str:
                dates = clean_str.split("to")
            elif "-" in date_str and len(date_str) > 12:
                start_date = date_str[:10].strip()
                end_date = date_str[-10:].strip()
                return start_date, end_date
            else:
                start_date = date_str.strip()
                end_date = start_date

            return start_date, end_date
        except:
            # Hata durumunda yarına plan ayarla
            tomorrow = datetime.date.today() + datetime.timedelta(days=1)
            return str(tomorrow), str(tomorrow)

    def add_event(self, plan_data):
        """
        Plan verisini alıp Google Takvim'e işler.
        """
        destination = plan_data.get('destination', 'Seyahat')
        dates = plan_data.get('dates', '')
        summary = f"Seyahat Planı: {destination}"
        
        description = (
            f"Rota: {plan_data.get('route', '')}\n\n"
            f"Yemek: {plan_data.get('food', '')}\n"
            f"Konaklama: {plan_data.get('accommodation', '')}"
        )

        start_date, end_date = self.parse_dates(dates)

        event = {
            'summary': summary,
            'location': destination,
            'description': description,
            'start': {
                'date': start_date, 
                'timeZone': 'Europe/Istanbul',
            },
            'end': {
                'date': end_date,
                'timeZone': 'Europe/Istanbul',
            },
        }

        event_result = self.service.events().insert(calendarId='primary', body=event).execute()
        return event_result.get('htmlLink')

