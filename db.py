import pymongo
from bson.objectid import ObjectId
import os
import hashlib

class DatabaseManager:
    def __init__(self):
        #docker kullanılıyorsa MONGO_HOST kullanılmıyorsa localhost kullanılır.
        mongo_host = os.environ.get('MONGO_HOST', 'localhost')
        try:
            self.client = pymongo.MongoClient(f"mongodb://{mongo_host}:27017/")
            self.db = self.client["seyahat_planlayici"]
            self.users = self.db["users"] 
            self.plans = self.db["plans"]
            print(f"Veritabanı bağlantısı ({mongo_host}) başarılı.")
        except Exception as e:
            print(f"Veritabanı bağlantı hatası: {e}")

    # KULLANICI İŞLEMLERİ
    def register_user(self, username, email, password):
        if self.users.find_one({"username": username}):
            return False, "Kullanıcı adı zaten var."
        
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        self.users.insert_one({
            "username": username,
            "email": email,
            "password": hashed_password,
            "music_library": [] # Müzik listesi için boş alan
        })
        return True, "Kayıt başarılı."

    def login_user(self, username, password):
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        user = self.users.find_one({"username": username, "password": hashed_password})
        if user:
            return True, user
        return False, None

    # Kullanıcı Bilgilerini Güncelle
    def update_user_profile(self, user_id, new_username, new_email, new_password=None):
        update_data = {"username": new_username, "email": new_email}
        
        # Eğer şifre alanı doluysa şifreyi de güncelle
        if new_password:
            hashed_password = hashlib.sha256(new_password.encode()).hexdigest()
            update_data["password"] = hashed_password
            
        try:
            self.users.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
            # Güncel kullanıcı verisini geri döndür
            return self.users.find_one({"_id": ObjectId(user_id)})
        except Exception as e:
            print(f"Güncelleme hatası: {e}")
            return None

    #  Kullanıcıyı Sil
    def delete_user(self, user_id):
        try:
            # Önce kullanıcının planlarını sil
            self.plans.delete_many({"user_id": user_id})
            # Sonra kullanıcıyı sil
            self.users.delete_one({"_id": ObjectId(user_id)})
            return True
        except Exception as e:
            print(f"Silme hatası: {e}")
            return False

    # PLAN İŞLEMLERİ
    # Plan Kaydetme
    def save_plan(self, user_id, plan_data):
        plan_data["user_id"] = user_id
        # Eğer photos alanı yoksa boş liste olarak başlat
        if "photos" not in plan_data:
            plan_data["photos"] = []
        self.plans.insert_one(plan_data)

    # Planları Listeleme
    def get_plans(self, user_id):
        return list(self.plans.find({"user_id": user_id}).sort("_id", -1))

    # Plan Güncelleme
    def update_plan(self, plan_id, updated_data):
        self.plans.update_one({"_id": ObjectId(plan_id)}, {"$set": updated_data})
    # Plan Silme
    def delete_plan(self, plan_id):
        self.plans.delete_one({"_id": ObjectId(plan_id)})

    # Fotoğraf Ekleme
    def add_photo_to_plan(self, plan_id, photo_base64, frame_style="polaroid"):
        photo_data = {"image": photo_base64, "style": frame_style, "date": "2025"}
        self.plans.update_one({"_id": ObjectId(plan_id)}, {"$push": {"photos": photo_data}})

    # Fotoğraf Silme
    def delete_photo_from_plan(self, plan_id, photo_data):
        self.plans.update_one({"_id": ObjectId(plan_id)}, {"$pull": {"photos": photo_data}})

    # MÜZİK İŞLEMLERİ
    # --- MÜZİK KÜTÜPHANESİ (GÜVENLİ & GÖMÜLÜ MOD) ---

    def add_music_to_library(self, user_id, path, name, image_b64):
        try:
            # ID Güvenliği
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)
            
            # Yeni Şarkı ID'si
            new_song_id = str(ObjectId())
            
            song_doc = {
                "id": new_song_id,
                "path": str(path), # Yolu garanti string yap
                "name": str(name), # İsmi garanti string yap
                "image": image_b64
            }
            
            # Veritabanına Ekle ($push ile listeye atıyoruz)
            # self.db["users"] yapısı en garantisidir.
            result = self.db["users"].update_one(
                {"_id": user_id},
                {"$push": {"music_library": song_doc}}
            )
            
            # Eğer kayıt güncellendiyse True, yoksa False
            return result.modified_count > 0
            
        except Exception:
            # Hata olsa bile çökme, sessizce False dön
            return False

    def get_music_library(self, user_id):
        try:
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)
            
            user = self.db["users"].find_one({"_id": user_id})
            
            # Liste varsa döndür, yoksa boş liste ver
            if user and "music_library" in user:
                return user["music_library"]
            return []
            
        except Exception:
            return []

    def delete_music_from_library(self, user_id, song_id):
        try:
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)
                
            # Listeden çekip al ($pull)
            result = self.db["users"].update_one(
                {"_id": user_id},
                {"$pull": {"music_library": {"id": song_id}}}
            )
            return result.modified_count > 0
            
        except Exception:
            return False