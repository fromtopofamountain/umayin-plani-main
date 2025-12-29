import time
import concurrent.futures
from datetime import datetime

# Alt Ajanlar
class AsAta: # Yemek
    def suggest(self, destination, budget):
        time.sleep(2) # İşlem simülasyonu
        return f"{destination} bölgesinde {budget} bütçeye uygun: Yerel Han Restoranı, Gurme Sokak Lezzetleri."

class YelAna: # Aktiviteler
    def suggest(self, destination, dates):
        time.sleep(2)
        return f"{dates} tarihlerinde {destination}: Doğa yürüyüşü, Arkeoloji müzesi gezisi."

class YurtIyesi: # Konaklama
    def suggest(self, destination, budget):
        time.sleep(2)
        return f"{budget} bütçeye uygun: Butik Taş Otel, Şehir Pansiyonu."

class OguzKaan: # Rota Optimizasyonu
    def optimize(self, food_plan, activity_plan):
        time.sleep(1)
        return f"Rota (Oğuz Ata): Sabah Müze -> Öğle Yemeği (Han) -> Akşam Yürüyüşü."

# --- Ana Koordinatör ---
class UmayAna:
    def __init__(self):
        self.as_ata = AsAta()
        self.yel_ana = YelAna()
        self.yurt_iyesi = YurtIyesi()
        self.oguz_kaan = OguzKaan()

    def create_travel_plan(self, destination, dates, budget):
        # ThreadPoolExecutor ile paralel çalıştırma
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_food = executor.submit(self.as_ata.suggest, destination, budget)
            future_activities = executor.submit(self.yel_ana.suggest, destination, dates)
            future_stay = executor.submit(self.yurt_iyesi.suggest, destination, budget)

            # Sonuçları bekle
            food_res = future_food.result()
            activity_res = future_activities.result()
            stay_res = future_stay.result()

        # Rota optimizasyonu 
        route_res = self.oguz_kaan.optimize(food_res, activity_res)

        final_plan = {
            "destination": destination,
            "dates": dates,
            "budget": budget,
            "food": food_res,
            "activities": activity_res,
            "accommodation": stay_res,
            "route": route_res,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        return final_plan
