import google as genai
import concurrent.futures
import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  


# Google Gemini Ayarları
if not GOOGLE_API_KEY or "BURAYA" in GOOGLE_API_KEY:
    print(" HATA: Lütfen ai_agent.py dosyasını açıp GOOGLE_API_KEY kısmına şifreni yapıştır!")
else:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        

        model_name = 'gemini-2.5-flash' 
        
        # test
        test_model = genai.GenerativeModel(model_name)
    except Exception as e:
        print(f" Bağlantı Hatası: {e}")

# AŞ ATA (Yemek Uzmanı)
class AsAta:
    def __init__(self, model):
        self.model = model

    def suggest(self, destination, budget):
        prompt = f"""
        Sen Türk mitolojisindeki 'Aş Ata'sın.
        Kendini kısaca tanıt.
        Gidilecek Yer: {destination}, Bütçe: {budget} TL.
        GÖREVİN: Bu bütçeye uygun en iyi yerel restoranları ve yöresel yemekleri listele.
        Kısa ve öz ol.
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"Hata oluştu: {e}"

# YEL ANA (Aktivite Uzmanı) 
class YelAna:
    def __init__(self, model):
        self.model = model

    def suggest(self, destination, dates):
        prompt = f"""
        Sen 'Yel Ana'sın.
        Kendini kısaca tanıt.
        Gidilecek Yer: {destination}, Tarih: {dates}.
        GÖREVİN: Bu tarihlerde yapılabilecek en keyifli, tarihi ve kültürel aktiviteleri listele.
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"Hata oluştu: {e}"

# YURT İYESİ (Konaklama Uzmanı)
class YurtIyesi:
    def __init__(self, model):
        self.model = model

    def suggest(self, destination, budget):
        prompt = f"""
        Sen 'Yurt İyesi'sin.
        Kendini kısaca tanıt.
        Gidilecek Yer: {destination}, Bütçe: {budget} TL.
        GÖREVİN: Bu bütçeye uygun otel veya pansiyon öner.
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"Hata oluştu: {e}"

# OĞUZ KAAN (Optimizasyon Uzmanı) ---
class OguzKaan:
    def __init__(self, model):
        self.model = model

    def optimize(self, food_res, activity_res, stay_res):
        prompt = f"""
        Sen 'Oğuz Kaan'sın.
        Kendini kısaca tanıt.
        ELİNDEKİ RAPORLAR:
        1. Yemekler: {food_res}
        2. Aktiviteler: {activity_res}
        3. Konaklama: {stay_res}
        GÖREVİN: Bu bilgileri birleştir ve gün gün ayrılmış, mantıklı bir SEYAHAT ROTASI yaz.
        """
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"Hata oluştu: {e}"

# ANA KOORDİNATÖR: UMAY ANA 
class UmayAnaAgent:
    def __init__(self):
       
        try:
            self.main_model = genai.GenerativeModel('gemini-2.5-flash')
        except:
            self.main_model = None
            print("Model oluşturulamadı, API Key hatalı olabilir.")
        
        self.as_ata = AsAta(self.main_model)
        self.yel_ana = YelAna(self.main_model)
        self.yurt_iyesi = YurtIyesi(self.main_model)
        self.oguz_kaan = OguzKaan(self.main_model)

    def planla(self, destination, dates, budget):
        print(f" Umay Ana çalışıyor... Hedef: {destination}")
        
        if not self.main_model:
            return {
                "rota": "API Anahtarı Hatası! Lütfen kodu kontrol et.",
                "yemek": "Hata",
                "aktivite": "Hata",
                "konaklama": "Hata"
            }
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_food = executor.submit(self.as_ata.suggest, destination, budget)
            future_activities = executor.submit(self.yel_ana.suggest, destination, dates)
            future_stay = executor.submit(self.yurt_iyesi.suggest, destination, budget)

            food_res = future_food.result()
            activity_res = future_activities.result()
            stay_res = future_stay.result()

        route_res = self.oguz_kaan.optimize(food_res, activity_res, stay_res)

        final_plan = {
            "rota": route_res,
            "yemek": food_res,
            "aktivite": activity_res,
            "konaklama": stay_res
        }
        return final_plan