import requests
import json
import datetime
from dotenv import load_dotenv
import os

# .env dosyasını yükle
load_dotenv()

# Şifreleri os.getenv ile çek
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# AYARLAR
# Internal Integration Secret

HEADERS = {
    "Authorization": "Bearer " + NOTION_TOKEN,
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def create_notion_page(plan_data):
    create_url = "https://api.notion.com/v1/pages"

    # TARİH DÜZELTME VE AYRIŞTIRMA MANTIĞI
    date_str = plan_data.get('dates', '')
    final_start = None
    final_end = None

    try:
        # 1. Tireye göre ayır
        parts = date_str.split("-")
        
        # 2. Parçaları temizle
        # Eğer format YYYY-MM-DD - YYYY-MM-DD ise (arada tire varsa).
        if " - " in date_str:
            # Kullanıcı "2025-06-10 - 2025-06-15" girdiyse
            split_dates = date_str.split(" - ")
            s_str = split_dates[0].strip()
            e_str = split_dates[1].strip()
        else:
            # Sadece tek tarih girildiyse veya format farklıysa
            s_str = date_str.strip()
            e_str = s_str

        # 3. Tarih objesine çevirip kontrol et (YYYY-MM-DD formatı)
        try:
            s_date = datetime.datetime.strptime(s_str, "%Y-%m-%d")
            e_date = datetime.datetime.strptime(e_str, "%Y-%m-%d")
            
            # HATA ÇÖZÜMÜ: Eğer başlangıç bitişten büyükse, yer değiştir!
            if s_date > e_date:
                s_date, e_date = e_date, s_date
            
            final_start = s_date.strftime("%Y-%m-%d")
            final_end = e_date.strftime("%Y-%m-%d")
            
        except ValueError:
            # Güvenli mod: Bugünü kullan.
            print("Tarih formatı algılanamadı, bugünün tarihi kullanılıyor.")
            final_start = datetime.date.today().isoformat()
            final_end = None

    except Exception as e:
        print(f"Tarih işleme hatası: {e}")
        final_start = datetime.date.today().isoformat()
        final_end = None

    # Tarih JSON objesi
    date_property = {"start": final_start}
    if final_end and final_end != final_start:
        date_property["end"] = final_end

    # SAYFA İÇERİĞİ
    children_blocks = [
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"text": {"content": "Seyahat Detayları"}}]}
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"text": {"content": f"📍 Rota: {plan_data.get('route', '-')}"}}]
            }
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"text": {"content": f"🍽️ Yemek: {plan_data.get('food', '-')}"}}]
            }
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"text": {"content": f"🏨 Konaklama: {plan_data.get('accommodation', '-')}"}}]
            }
        },
        {
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [{"text": {"content": f"💰 Bütçe: {plan_data.get('budget', '-')}"}}],
                "icon": {"emoji": "💸"}
            }
        }
    ]

    # NOTION PAYLOAD
    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "plan adı": { 
                "title": [
                    {"text": {"content": f"Seyahat: {plan_data.get('destination', 'Adsız')}"}}
                ]
            },
            "Tarih": { 
                "date": date_property
            }
        },
        "children": children_blocks
    }

    response = requests.post(create_url, headers=HEADERS, data=json.dumps(payload))

    if response.status_code == 200:
        return response.json()['url']
    else:
        # hata mesajını ekrana yazdır.
        error_text = response.text
        raise Exception(f"Notion Hatası: {response.status_code} - {error_text}")