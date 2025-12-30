import sys
import base64
import re
import os

# PYQT5 IMPORTLARI 
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QTabWidget, QTableWidget, 
                             QTableWidgetItem, QMessageBox, QHeaderView, QFormLayout, 
                             QTextEdit, QProgressBar, QCheckBox, QFrame, QDialog, 
                             QFileDialog, QInputDialog, QListWidget, QListWidgetItem, QGroupBox)
from PyQt5.QtCore import Qt, QPoint, QThread, pyqtSignal, QByteArray, QBuffer, QIODevice, QUrl, QTimer, QRectF
from PyQt5.QtGui import QCursor, QPixmap, QImage, QPainter, QColor, QBitmap
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent

# PROJE IMPORTLARI 
# Eğer bu dosyalar yoksa hata verir, proje klasöründe olduklarından emin ol.
try:
    from db import DatabaseManager
    from agents import UmayAna
except ImportError as e:
    print(f"KRİTİK HATA: db.py veya agents.py bulunamadı! {e}")
    sys.exit(1)

# Helper dosyaları kontrolü 
try:
    from google_helper import GoogleCalendarManager
except ImportError:
    GoogleCalendarManager = None

try:
    from notion_helper import create_notion_page
except ImportError:
    create_notion_page = None

# Pygame Import 
try:
    import pygame
except ImportError:
    print("UYARI: pygame yüklü değil. 'pip install pygame' yazın.")
    pygame = None

# ARKA PLANDA ÇALIŞAN AGENT THREAD'İ 
class AgentWorker(QThread):
    finished = pyqtSignal(dict)
    
    def __init__(self, destination, dates, budget):
        super().__init__()
        self.destination = destination
        self.dates = dates
        self.budget = budget
        self.umay = UmayAna()

    def run(self):
        try:
            plan = self.umay.create_travel_plan(self.destination, self.dates, self.budget)
            self.finished.emit(plan)
        except Exception as e:
            print(f"Agent Hatası: {e}")
            self.finished.emit({})

# BAŞLIK ÇUBUĞU
class CustomTitleBar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(35)
        self.setStyleSheet("""
            background-color: #8e99f3; 
            border-bottom: 2px solid #6c78d3;
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        
        self.title_label = QLabel("☁️ Umay'ın Planı.exe")
        self.title_label.setStyleSheet("color: white; font-weight: bold; font-family: 'Courier New'; border: none;")
        
        btn_style = """
            QPushButton {
                background-color: #ffb7b2;
                border: 1px solid #fff;
                color: white;
                font-weight: bold;
                width: 20px;
                height: 20px;
            }
            QPushButton:hover { background-color: #ff9aa2; }
        """
        
        self.btn_minimize = QPushButton("_")
        self.btn_minimize.setStyleSheet(btn_style)
        self.btn_minimize.setCursor(Qt.PointingHandCursor) # Varsayılan el
        self.btn_minimize.clicked.connect(self.parent.showMinimized)
        
        self.btn_maximize = QPushButton("⬜")
        self.btn_maximize.setStyleSheet(btn_style)
        self.btn_maximize.setCursor(Qt.PointingHandCursor)
        self.btn_maximize.clicked.connect(self.toggle_maximize)

        self.btn_close = QPushButton("X")
        self.btn_close.setStyleSheet(btn_style)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.clicked.connect(self.parent.close)

        layout.addWidget(self.title_label)
        layout.addStretch()
        layout.addWidget(self.btn_minimize)
        layout.addWidget(self.btn_maximize)
        layout.addWidget(self.btn_close)
        
        self.start = QPoint(0, 0)
        self.pressing = False

        # Eğer global el cursor varsa onu kullan
        if 'HAND_CURSOR' in globals() and globals()['HAND_CURSOR']:
            self.btn_minimize.setCursor(globals()['HAND_CURSOR'])
            self.btn_maximize.setCursor(globals()['HAND_CURSOR'])
            self.btn_close.setCursor(globals()['HAND_CURSOR'])

    def toggle_maximize(self):
        window = self.window()
        if window.isMaximized():
            window.showNormal()
        else:
            window.showMaximized()

    def mousePressEvent(self, event):
        self.start = self.mapToGlobal(event.pos())
        self.pressing = True

    def mouseMoveEvent(self, event):
        if self.pressing:
            end = self.mapToGlobal(event.pos())
            movement = end - self.start
            self.parent.setGeometry(self.parent.x() + movement.x(),
                                    self.parent.y() + movement.y(),
                                    self.parent.width(),
                                    self.parent.height())
            self.start = end

    def mouseReleaseEvent(self, event):
        self.pressing = False

#  PIXELART KAMERA WİDGET 
class CameraWidget(QWidget):
    def __init__(self, plan_data, db, parent=None):
        super().__init__(parent)
        self.plan_data = plan_data
        self.db = db
        self.current_index = 0
        self.photos = plan_data.get("photos", [])

        self.setFixedSize(600, 350)

        self.lbl_bg = QLabel(self)
        self.lbl_bg.setGeometry(0, 0, 600, 350)

        pixmap = QPixmap("pixil-frame-main.png") 
        if pixmap.isNull():
            pixmap = QPixmap("assets/pixil-frame-main.png")

        if pixmap.isNull():
            self.lbl_bg.setText("GÖRSEL YOK")
            self.lbl_bg.setStyleSheet("background: pink; color: white;")
        else:
            self.lbl_bg.setPixmap(pixmap.scaled(600, 350, Qt.IgnoreAspectRatio, Qt.SmoothTransformation))

        self.screen_area = QLabel(self)
        self.screen_area.setGeometry(155, 87, 225, 165) 
        self.screen_area.setStyleSheet("background-color: #222; border-radius: 4px;")
        self.screen_area.setAlignment(Qt.AlignCenter)

        self.btn_add = QPushButton(self)
        self.btn_add.setGeometry(430, 60, 100, 50) 
        self.btn_add.setStyleSheet("background-color: transparent; border: none;") 
        self.btn_add.clicked.connect(self.upload_photo)

        self.btn_delete = QPushButton(self)
        self.btn_delete.setGeometry(430, 130, 100, 50)
        self.btn_delete.setStyleSheet("background-color: transparent; border: none;")
        self.btn_delete.clicked.connect(self.delete_current_photo)

        self.btn_prev = QPushButton(self)
        self.btn_prev.setGeometry(450, 210, 50, 100)
        self.btn_prev.setStyleSheet("background-color: transparent; border: none;")
        self.btn_prev.clicked.connect(self.prev_photo)

        self.btn_next = QPushButton(self)
        self.btn_next.setGeometry(510, 210, 50, 100)
        self.btn_next.setStyleSheet("background-color: transparent; border: none;")
        self.btn_next.clicked.connect(self.next_photo)

        # Cursor ayarı
        if 'HAND_CURSOR' in globals() and globals()['HAND_CURSOR']:
            self.btn_add.setCursor(globals()['HAND_CURSOR'])
            self.btn_delete.setCursor(globals()['HAND_CURSOR'])
            self.btn_prev.setCursor(globals()['HAND_CURSOR'])
            self.btn_next.setCursor(globals()['HAND_CURSOR'])
        else:
            self.btn_add.setCursor(Qt.PointingHandCursor)
            self.btn_delete.setCursor(Qt.PointingHandCursor)
            self.btn_prev.setCursor(Qt.PointingHandCursor)
            self.btn_next.setCursor(Qt.PointingHandCursor)

        self.update_screen()

    def update_screen(self):
        if not self.photos:
            self.screen_area.setText("Görsel Ekleyin.")
            self.screen_area.setStyleSheet("background-color: #ddd; color: #d3968c; font-family: 'Courier New'; font-size: 10px;")
            self.screen_area.clearMask()
            return
        
        photo_data = self.photos[self.current_index]

        if isinstance(photo_data, dict):
            b64_str = photo_data["image"]
        else:
            b64_str = photo_data

        try:
            byte_data = base64.b64decode(b64_str)
            image = QImage.fromData(byte_data)
            original_pixmap = QPixmap.fromImage(image)

            target_w = 360 
            target_h = 220 

            scaled_pixmap = original_pixmap.scaled(
                target_w, target_h,
                Qt.KeepAspectRatioByExpanding, 
                Qt.SmoothTransformation
            )

            x = (scaled_pixmap.width() - target_w) // 2
            y = (scaled_pixmap.height() - target_h) // 2
            
            rectangular_pixmap = scaled_pixmap.copy(x, y, target_w, target_h)
            
            # Maskeleme
            mask_path = "assets/camera_mask.png" # Asset klasörünü kontrol et
            if not os.path.exists(mask_path): mask_path = "camera_mask.png"

            mask_bitmap = QBitmap(mask_path)
            if not mask_bitmap.isNull():
                scaled_mask = mask_bitmap.scaled(target_w, target_h, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                rectangular_pixmap.setMask(scaled_mask)
            
            self.screen_area.setPixmap(rectangular_pixmap)
            
        except Exception as e:
            print(f"Resim hatası: {e}")
            self.screen_area.setText("Hata")

    def next_photo(self):
        if self.photos:
            self.current_index = (self.current_index + 1) % len(self.photos)
            self.update_screen()

    def prev_photo(self):
        if self.photos:
            self.current_index = (self.current_index - 1) % len(self.photos)
            self.update_screen()

    def upload_photo(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Fotoğraf Seç", "", "Resim Dosyaları (*.png *.jpg *.jpeg)")
        if file_name:
            pixmap = QPixmap(file_name)
            if pixmap.isNull(): return

            byte_array = QByteArray()
            buffer = QBuffer(byte_array)
            buffer.open(QIODevice.WriteOnly)
            pixmap.save(buffer, "JPG")
            base64_data = base64.b64encode(byte_array.data()).decode('utf-8')

            self.db.add_photo_to_plan(self.plan_data["_id"], base64_data, "camera")

            self.photos.append({"image": base64_data, "style": "camera"})
            self.current_index = len(self.photos) - 1
            self.update_screen()
            QMessageBox.information(self, "Başarılı", "Fotoğraf albüme eklendi!")

    def delete_current_photo(self):
        if not self.photos: return
        
        reply = QMessageBox.question(self, "Onay", "Bu fotoğrafı silmek istediğinize emin misiniz?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            photo_to_delete = self.photos[self.current_index]
            self.db.delete_photo_from_plan(self.plan_data["_id"], photo_to_delete)
            self.photos.pop(self.current_index)
            if self.current_index >= len(self.photos):
                self.current_index = max(0, len(self.photos) - 1) 
            self.update_screen()

# MÜZİK ÇALAR 
class MusicPlayerWidget(QWidget):
    cd_double_clicked = pyqtSignal() 

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 120) 
        
        if pygame:
            pygame.mixer.init()

        self.angle = 0
        self.is_playing = False
        self.custom_cd_pixmap = None
        
        self.cd_pixmap = QPixmap(100, 100)
        self.cd_pixmap.fill(Qt.transparent)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate_cd)
        self.timer.setInterval(50) 

        self.setAttribute(Qt.WA_TranslucentBackground)
        
        if 'HAND_CURSOR' in globals() and globals()['HAND_CURSOR']:
            self.setCursor(globals()['HAND_CURSOR'])
        else:
            self.setCursor(Qt.PointingHandCursor)

        self.show()

    def load_music(self, file_path):
        if not pygame: return
        try:
            import os
            full_path = os.path.abspath(file_path)
            if not os.path.exists(full_path):
                print("Dosya yok!")
                return
            pygame.mixer.music.load(full_path)
            print(f"Müzik Hazır: {full_path}")
        except Exception as e:
            print(f"Müzik yükleme hatası: {e}")

    def play(self):
        if not pygame: return
        try:
            pygame.mixer.music.play()
            self.timer.start()
            self.is_playing = True
        except Exception as e:
            print(f"Çalma hatası: {e}")

    def pause(self):
        if not pygame: return
        pygame.mixer.music.pause()
        self.timer.stop()
        self.is_playing = False

    def toggle(self):
        if not pygame: return
        if self.is_playing:
            self.pause()
        else:
            if pygame.mixer.music.get_pos() > 0: 
                pygame.mixer.music.unpause()
                self.timer.start()
                self.is_playing = True
            else:
                self.play()

    def rotate_cd(self):
        self.angle = (self.angle + 2) % 360
        self.update()
        if pygame and not pygame.mixer.music.get_busy() and self.is_playing:
             pygame.mixer.music.play()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        center_x = self.width() / 2
        center_y = self.height() / 2
        painter.translate(center_x, center_y)
        painter.rotate(self.angle)
        painter.translate(-center_x, -center_y)

        if self.custom_cd_pixmap and not self.custom_cd_pixmap.isNull():
            offset_x = (self.width() - self.custom_cd_pixmap.width()) / 2
            offset_y = (self.height() - self.custom_cd_pixmap.height()) / 2
            painter.drawPixmap(int(offset_x), int(offset_y), self.custom_cd_pixmap)
        else:
            painter.setBrush(Qt.lightGray)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(10, 10, 100, 100)
            
            painter.setBrush(QColor("#ffb7b2")) 
            painter.drawEllipse(25, 25, 70, 70)
            
            painter.setPen(QColor("#555555"))
            font = painter.font()
            font.setPointSize(20)
            font.setBold(True)
            painter.setFont(font)

        painter.setCompositionMode(QPainter.CompositionMode_Clear)
        painter.setBrush(Qt.transparent)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(55, 55, 10, 10)

    def mousePressEvent(self, event):
        self.toggle()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.cd_double_clicked.emit()
        super().mouseDoubleClickEvent(event)
        
    def set_cd_image(self, base64_data):
        if base64_data:
            try:
                byte_data = base64.b64decode(base64_data)
                image = QImage.fromData(byte_data)
                self.custom_cd_pixmap = QPixmap.fromImage(image).scaled(120,120, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)

                mask = QBitmap(120, 120)
                mask.fill(Qt.color0) 
                painter = QPainter(mask)
                painter.setBrush(Qt.color1)
                painter.drawEllipse(0, 0, 120, 120)
                painter.end()
                self.custom_cd_pixmap.setMask(mask)
            except Exception as e:
                print(f"CD resmi yüklenemedi: {e}")
                self.custom_cd_pixmap = None
        else:
            self.custom_cd_pixmap = None
        self.update()

# MÜZİK LİSTESİ PENCERESİ 
class MusicFolderDialog(QDialog):
    def __init__(self, db, user_id, music_player):
        super().__init__()
        self.setWindowTitle("CD' lerim")
        self.setFixedSize(400, 500)
        self.setStyleSheet("background-color: #fff0f5;")
        
        self.db = db
        self.user_id = user_id
        self.player = music_player 
        
        layout = QVBoxLayout(self)
        
        lbl = QLabel("Müzik Listesi")
        lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #6c78d3; margin: 10px;")
        layout.addWidget(lbl)
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget { background: white; border: 2px dashed #8e99f3; border-radius: 10px; font-size: 14px; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #eee; }
            QListWidget::item:selected { background: #ffb7b2; color: white; }
        """)
        self.list_widget.itemDoubleClicked.connect(self.play_selected_song)
        layout.addWidget(self.list_widget)
        
        btn_layout = QHBoxLayout()
        
        self.btn_play = QPushButton("▶ ÇAL")
        self.btn_play.clicked.connect(self.play_selected_song)
        self.btn_play.setStyleSheet("background: #b5ead7; padding: 10px; font-weight: bold;")

        self.btn_add = QPushButton("➕ EKLE")
        self.btn_add.clicked.connect(self.add_new_song)
        self.btn_add.setStyleSheet("background: #8e99f3; color: white; padding: 10px; font-weight: bold;")
        
        self.btn_del = QPushButton("🗑️ SİL")
        self.btn_del.clicked.connect(self.delete_song)
        self.btn_del.setStyleSheet("background: #ffb7b2; color: white; padding: 10px; font-weight: bold;")

        # Cursorlar
        if 'HAND_CURSOR' in globals() and globals()['HAND_CURSOR']:
            self.btn_play.setCursor(globals()['HAND_CURSOR'])
            self.btn_add.setCursor(globals()['HAND_CURSOR'])
            self.btn_del.setCursor(globals()['HAND_CURSOR'])
        
        btn_layout.addWidget(self.btn_play)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_del)
        layout.addLayout(btn_layout)
        
        self.refresh_list()
        
    def refresh_list(self):
        self.list_widget.clear()
        library = self.db.get_music_library(self.user_id)
        for song in library:
            item = QListWidgetItem(f"🎵 {song['name']}")
            item.setData(Qt.UserRole, song)
            self.list_widget.addItem(item)
            
    def add_new_song(self):
        path, _ = QFileDialog.getOpenFileName(self, "Müzik Seç", "", "Ses (*.mp3 *.wav)")
        if not path: return
        
        name, ok = QInputDialog.getText(self, "İsim", "Şarkı Adı:")
        if not ok or not name: return
        
        img_b64 = None
        reply = QMessageBox.question(self, "Resim", "CD resmi eklemek ister misin?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            img_path, _ = QFileDialog.getOpenFileName(self, "Resim Seç", "", "Resim (*.png *.jpg)")
            if img_path:
                with open(img_path, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode('utf-8')
                    
        self.db.add_music_to_library(self.user_id, path, name, img_b64)
        self.refresh_list()
        
    def delete_song(self):
        row = self.list_widget.currentRow()
        if row < 0: return
        song = self.list_widget.item(row).data(Qt.UserRole)
        self.db.delete_music_from_library(self.user_id, song['id'])
        self.refresh_list()
        
    def play_selected_song(self, item=None):
        # Butonla çağrıldığında item False (bool) gelir, onu engelle.
        if item is None or not isinstance(item, QListWidgetItem):
            row = self.list_widget.currentRow()
            if row < 0: return
            item = self.list_widget.item(row)
            
        song = item.data(Qt.UserRole)
        
        self.player.load_music(song['path'])
        self.player.set_cd_image(song['image'])
        self.player.play()
        self.player.show() 

# PLAN DÜZENLEME PENCERESİ 
class PlanEditDialog(QDialog):
    def __init__(self, db, plan_data, parent=None):
        super().__init__(parent)
        self.db = db
        self.plan_data = plan_data
        self.setWindowTitle("Planı Düzenle")
        self.setFixedSize(400, 600)
        self.setStyleSheet("background-color: #fff0f5;")
        
        layout = QFormLayout(self)
        
        # Veri güvenliği: .get() or "" (None gelirse çökmeyi engelle)
        self.edit_dest = QLineEdit(plan_data.get("destination") or "")
        self.edit_dates = QLineEdit(plan_data.get("dates") or "")
        self.edit_budget = QLineEdit(plan_data.get("budget") or "")
        self.edit_hotel = QLineEdit(plan_data.get("hotel") or "")
        
        self.edit_rest = QTextEdit()
        self.edit_rest.setText(plan_data.get("restaurants") or "")
        
        self.edit_act = QTextEdit()
        self.edit_act.setText(plan_data.get("activities") or "")
        
        btn_save = QPushButton("DEĞİŞİKLİKLERİ KAYDET")
        btn_save.setStyleSheet("background: #8e99f3; color: white; padding: 10px; font-weight: bold;")
        if 'HAND_CURSOR' in globals() and globals()['HAND_CURSOR']:
            btn_save.setCursor(globals()['HAND_CURSOR'])

        btn_save.clicked.connect(self.save_changes)
        
        layout.addRow("Gidilecek Yer:", self.edit_dest)
        layout.addRow("Tarih Aralığı:", self.edit_dates)
        layout.addRow("Bütçe:", self.edit_budget)
        layout.addRow("Otel/Konaklama:", self.edit_hotel)
        layout.addRow("Yeme-İçme:", self.edit_rest)
        layout.addRow("Aktiviteler:", self.edit_act)
        layout.addWidget(btn_save)
        
    def save_changes(self):
        updated_data = {
            "destination": self.edit_dest.text(),
            "dates": self.edit_dates.text(),
            "budget": self.edit_budget.text(),
            "hotel": self.edit_hotel.text(),
            "restaurants": self.edit_rest.toPlainText(),
            "activities": self.edit_act.toPlainText()
        }
        
        self.db.update_plan(self.plan_data["_id"], updated_data)
        QMessageBox.information(self, "Başarılı", "Plan başarıyla güncellendi!")
        self.accept()

# PROFİL SEKMESİ
class ProfileTab(QWidget):
    def __init__(self, db, user, main_window):
        super().__init__()
        self.db = db
        self.user = user
        self.main_window = main_window 
        
        layout = QVBoxLayout(self)
        
        grp_box = QGroupBox("Kullanıcı Bilgilerim")
        grp_layout = QFormLayout()
        
        self.edit_user = QLineEdit(user.get("username", ""))
        self.edit_email = QLineEdit(user.get("email", ""))
        self.edit_pass = QLineEdit()
        self.edit_pass.setPlaceholderText("Değiştirmek istemiyorsanız boş bırakın")
        self.edit_pass.setEchoMode(QLineEdit.Password)
        
        btn_update = QPushButton("🔄 BİLGİLERİMİ GÜNCELLE")
        btn_update.setStyleSheet("background: #b5ead7; padding: 10px; font-weight: bold;")
        if 'HAND_CURSOR' in globals() and globals()['HAND_CURSOR']:
            btn_update.setCursor(globals()['HAND_CURSOR'])
        btn_update.clicked.connect(self.update_profile)
        
        grp_layout.addRow("Kullanıcı Adı:", self.edit_user)
        grp_layout.addRow("E-Posta:", self.edit_email)
        grp_layout.addRow("Yeni Şifre:", self.edit_pass)
        grp_layout.addWidget(btn_update)
        grp_box.setLayout(grp_layout)
        
        grp_danger = QGroupBox("⚠️ Tehlikeli Bölge")
        grp_danger.setStyleSheet("QGroupBox { border: 2px solid red; }")
        danger_layout = QVBoxLayout()
        
        btn_delete_acc = QPushButton("HESABIMI KALICI OLARAK SİL")
        btn_delete_acc.setStyleSheet("background: red; color: white; padding: 10px; font-weight: bold;")
        if 'HAND_CURSOR' in globals() and globals()['HAND_CURSOR']:
            btn_delete_acc.setCursor(globals()['HAND_CURSOR'])
        btn_delete_acc.clicked.connect(self.delete_account)
        
        danger_layout.addWidget(QLabel("Dikkat: Bu işlem geri alınamaz. Tüm planlarınız ve fotoğraflarınız silinir."))
        danger_layout.addWidget(btn_delete_acc)
        grp_danger.setLayout(danger_layout)
        
        layout.addWidget(grp_box)
        layout.addStretch()
        layout.addWidget(grp_danger)
        
    def update_profile(self):
        new_user = self.edit_user.text()
        new_mail = self.edit_email.text()
        new_pass = self.edit_pass.text()
        
        if not new_user:
            QMessageBox.warning(self, "Hata", "Kullanıcı adı boş olamaz.")
            return
            
        updated_user = self.db.update_user_profile(self.user["_id"], new_user, new_mail, new_pass if new_pass else None)
        
        if updated_user:
            self.user = updated_user
            QMessageBox.information(self, "Başarılı", "Profil bilgileriniz güncellendi.")
            self.edit_pass.clear()
        else:
            QMessageBox.critical(self, "Hata", "Güncelleme sırasında bir sorun oluştu.")

    def delete_account(self):
        reply = QMessageBox.question(self, "HESAP SİLME", 
                                     "Emin misiniz? Tüm verileriniz silinecek ve uygulama kapanacak!",
                                     QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            if self.db.delete_user(self.user["_id"]):
                QMessageBox.information(self, "Hoşçakal", "Hesabınız silindi. Kayıt ekranına dönülüyor.")
                self.main_window.return_to_login() 
            else:
                QMessageBox.critical(self, "Hata", "Silme işlemi başarısız oldu.")

# PLAN DETAYLARI
class PlanDetailWindow(QDialog):
    def __init__(self, plan_data, db):
        super().__init__()
        self.plan_data = plan_data
        self.db = db

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(650, 750)

        layout = QVBoxLayout(self)
        self.container = QFrame()
        self.container.setObjectName("DetailFrame")
        self.container.setStyleSheet("""
            QFrame#DetailFrame {
                background-color: #fff0f5;
                border: 2px solid #8e99f3;
            }
            QTextEdit {
                background-color: #ffffff;
                border: 2px dashed #ffb7b2;
                font-family: 'Courier New';
                font-size: 13px;
                color: #555;
            }                        
            QLabel {
                font-weight: bold;
                font-size: 14px;
                color: #6c78d3;
            } 
        """)  

        inner_layout = QVBoxLayout(self.container)
        inner_layout.setContentsMargins(0,0,0,0)

        self.title_bar = CustomTitleBar(self)
        self.title_bar.title_label.setText(f"📂 {plan_data.get('destination', 'Plan')} Dosyası")
        self.title_bar.btn_minimize.hide()

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: none; }
            QTabBar::tab { background: #e3e1ea; color: #555; border-radius: 4px; padding: 6px; margin: 2px; }
            QTabBar::tab:selected { background: #ffb7b2; color: white; }
        """)   

        # 1. SEKME : PLAN DETAYLARI
        self.tab_text = QWidget()
        text_layout = QVBoxLayout(self.tab_text)

        lbl_title = QLabel(f"✨ {plan_data.get('destination', '-').upper()} SEYAHATİ ")
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setStyleSheet("font-size: 18px; color: #ff9e99; margin: 10px;")

        details = QTextEdit()
        details.setReadOnly(True)
        
        full_text = f"""
📍 GİDİLECEK YER: {plan_data.get('destination', '-')}
📅 TARİH: {plan_data.get('dates', '-')}
💰 BÜTÇE: {plan_data.get('budget', '-')}

------------------------------------------
🍽️ YEME - İÇME:
{plan_data.get('food', '-')}
{plan_data.get('restaurants', '')}

------------------------------------------
🎡 AKTİVİTELER:
{plan_data.get('activities', '-')}

------------------------------------------
🏨 KONAKLAMA:
{plan_data.get('accommodation', '-')}
{plan_data.get('hotel', '')}

------------------------------------------
🗺️ ROTA:
{plan_data.get('route', '-')}
        """
        details.setText(full_text)
        
        text_layout.addWidget(lbl_title)
        text_layout.addWidget(details)

        # 2. SEKME: FOTOĞRAF EKLEME
        self.tab_photos = QWidget()
        photo_layout = QVBoxLayout(self.tab_photos)
        
        self.camera_widget = CameraWidget(self.plan_data, self.db)

        h_layout = QHBoxLayout()
        h_layout.addStretch()
        h_layout.addWidget(self.camera_widget)
        h_layout.addStretch()

        lbl_info = QLabel("Kontroller: 🟢 Ekle | 🔴 Sil | ◀ ▶ Gezin")
        lbl_info.setAlignment(Qt.AlignCenter)
        lbl_info.setStyleSheet("color: #888; font-size: 11px; margin-top: 10px;")

        photo_layout.addStretch()
        photo_layout.addLayout(h_layout)
        photo_layout.addWidget(lbl_info)
        photo_layout.addStretch()

        self.tabs.addTab(self.tab_text, "📝 NOTLAR")
        self.tabs.addTab(self.tab_photos, "📷 KAMERA")

        btn_close = QPushButton("KAPAT ❌")
        if 'HAND_CURSOR' in globals() and globals()['HAND_CURSOR']:
            btn_close.setCursor(globals()['HAND_CURSOR'])
        btn_close.clicked.connect(self.close)
        btn_close.setStyleSheet("background-color: #ffb7b2; color: white; margin: 10px; padding: 5px; font-weight: bold;")

        inner_layout.addWidget(self.title_bar)
        inner_layout.addWidget(self.tabs)
        inner_layout.addWidget(btn_close)
        layout.addWidget(self.container)

    def mousePressEvent(self, event):
        self.title_bar.mousePressEvent(event)
    def mouseMoveEvent(self, event):
        self.title_bar.mouseMoveEvent(event)
    def mouseReleaseEvent(self, event):
        self.title_bar.mouseReleaseEvent(event)

# ANA PENCERE 
class MainWindow(QMainWindow):
    def __init__(self, db, user, open_login_callback):
        super().__init__()
        self.db = db
        self.user = user
        self.open_login_callback = open_login_callback 
        
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(1100, 750)
        
        self.main_container = QWidget()
        self.main_container.setObjectName("MainContainer")
        self.main_container.setStyleSheet("""
            QWidget#MainContainer {
                border: 2px solid #8e99f3;
                background-color: #e3e1ea;
            }
        """)
        self.setCentralWidget(self.main_container)
        
        self.layout = QVBoxLayout(self.main_container)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        self.title_bar = CustomTitleBar(self)
        self.layout.addWidget(self.title_bar)
        
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        
        self.tabs = QTabWidget()
        
        self.setup_my_plans_tab()
        self.setup_manual_plan_tab()
        self.setup_agent_tab()
        self.setup_profile_tab()
        
        self.content_layout.addWidget(self.tabs)
        self.layout.addWidget(self.content_area)
        
        # CD Çalar Widget'ı
        self.music_widget = MusicPlayerWidget(self.main_container)
        self.music_widget.cd_double_clicked.connect(self.open_music_folder)
        
        self.load_plans()

    def resizeEvent(self, event):
        if hasattr(self, 'music_widget'):
            self.music_widget.move(self.width() - 140, self.height() - 140)
        super().resizeEvent(event)

    def return_to_login(self):
        self.login_win = LoginWindow(self.db, self.open_login_callback, start_index=1)
        self.login_win.show()
        self.close()

    def open_music_folder(self):
        if hasattr(self, 'music_dialog') and self.music_dialog.isVisible():
            self.music_dialog.raise_()
            self.music_dialog.activateWindow()
            return

        self.music_dialog = MusicFolderDialog(self.db, self.user["_id"], self.music_widget)
        self.music_dialog.show()

    def setup_my_plans_tab(self):
        self.tab_plans = QWidget()
        layout = QVBoxLayout()
        
        # ARAMA ÇUBUĞU
        search_layout = QHBoxLayout()
        lbl_search = QLabel("🔍 Plan Ara:")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Şehir veya bütçe ara...")
        self.search_input.textChanged.connect(self.filter_plans) 
        
        search_layout.addWidget(lbl_search)
        search_layout.addWidget(self.search_input)
        
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "Yer", "Tarih", "Bütçe", "Detay", "Düzenle", "Sil"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        btn_refresh = QPushButton("LİSTEYİ YENİLE")
        if 'HAND_CURSOR' in globals() and globals()['HAND_CURSOR']: btn_refresh.setCursor(globals()['HAND_CURSOR'])
        btn_refresh.clicked.connect(self.load_plans)
        
        layout.addLayout(search_layout)
        layout.addWidget(self.table)
        layout.addWidget(btn_refresh)
        self.tab_plans.setLayout(layout)
        self.tabs.addTab(self.tab_plans, "MEVCUT PLANLAR")

    def filter_plans(self):
        search_text = self.search_input.text().lower()
        for row in range(self.table.rowCount()):
            item_dest = self.table.item(row, 1)
            item_budget = self.table.item(row, 3)
            
            match = False
            if item_dest and search_text in item_dest.text().lower():
                match = True
            if item_budget and search_text in item_budget.text().lower():
                match = True
                
            self.table.setRowHidden(row, not match)

    def setup_manual_plan_tab(self):
        self.tab_manual = QWidget()
        layout = QFormLayout()
        
        self.m_dest = QLineEdit()
        self.m_date = QLineEdit()
        self.m_date.setPlaceholderText("YYYY-AA-GG")
        self.m_budget = QLineEdit()
        self.m_rest = QTextEdit()
        self.m_act = QTextEdit()
        self.m_route = QTextEdit()
        self.m_route.setPlaceholderText("Örn: İstanbul -> Bursa -> İzmir")
        self.m_route.setFixedHeight(80)
  
        self.m_hotel = QLineEdit()
        self.m_hotel.setPlaceholderText("Günübirlik ise boş bırakın")
        
        btn_save = QPushButton("PLANI KAYDET")
        if 'HAND_CURSOR' in globals() and globals()['HAND_CURSOR']: btn_save.setCursor(globals()['HAND_CURSOR'])
        btn_save.clicked.connect(self.save_manual_plan)
        
        layout.addRow("GİDİLECEK YER:", self.m_dest)
        layout.addRow("TARİH ARALIĞI:", self.m_date)
        layout.addRow("ROTA:", self.m_route)
        layout.addRow("RESTORANLAR:", self.m_rest)
        layout.addRow("AKTİVİTELER:", self.m_act)
        layout.addRow("BÜTÇE:", self.m_budget)
        layout.addRow("OTEL:", self.m_hotel)
        layout.addWidget(btn_save)
        
        self.tab_manual.setLayout(layout)
        self.tabs.addTab(self.tab_manual, "MANUEL PLANLA")

    def setup_agent_tab(self):
        self.tab_agents = QWidget()
        layout = QVBoxLayout()
        
        form_layout = QFormLayout()
        
        lbl_dest = QLabel("📁 Gidilecek Yer:")
        lbl_date = QLabel("📅 Tarih Aralığı:")
        lbl_budg = QLabel("💰 Bütçe:")
        
        self.a_dest = QLineEdit()
        self.a_dates = QLineEdit()
        self.a_dates.setPlaceholderText("2025-06-10 - 2025-06-15")
        self.a_budget = QLineEdit()
        
        form_layout.addRow(lbl_dest, self.a_dest)
        form_layout.addRow(lbl_date, self.a_dates)
        form_layout.addRow(lbl_budg, self.a_budget)
        
        self.btn_ask_umay = QPushButton("UMAY ANA'YI ÇAĞIR")
        if 'HAND_CURSOR' in globals() and globals()['HAND_CURSOR']: self.btn_ask_umay.setCursor(globals()['HAND_CURSOR'])
        self.btn_ask_umay.clicked.connect(self.run_agents)
        
        self.progress = QProgressBar()
        self.progress.setValue(0)
        
        self.agent_output = QTextEdit()
        self.agent_output.setReadOnly(True)
        self.agent_output.setStyleSheet("background-color: #fff0f5; color: #555;")
        
        self.chk_google = QCheckBox("Google Takvim'e Ekle")
        self.chk_notion = QCheckBox("Notion Calendar'a Ekle")
        
        btn_save_agent = QPushButton("PLANI KAYDET")
        if 'HAND_CURSOR' in globals() and globals()['HAND_CURSOR']: btn_save_agent.setCursor(globals()['HAND_CURSOR'])
        btn_save_agent.clicked.connect(self.save_agent_plan_to_db)
        
        layout.addLayout(form_layout)
        layout.addWidget(self.btn_ask_umay)
        layout.addWidget(self.progress)
        layout.addWidget(self.agent_output)
        layout.addWidget(self.chk_google)
        layout.addWidget(self.chk_notion)
        layout.addWidget(btn_save_agent)
        
        self.tab_agents.setLayout(layout)
        self.tabs.addTab(self.tab_agents, "AGENTLARLA PLANLA")

    def setup_profile_tab(self):
        self.tab_profile = ProfileTab(self.db, self.user, self)
        self.tabs.addTab(self.tab_profile, "👤 PROFİL")

    def load_plans(self):
        try:
            plans = self.db.get_plans(self.user["_id"])
            self.table.setRowCount(len(plans))
            
            for row, plan in enumerate(plans):
                self.table.setItem(row, 0, QTableWidgetItem(str(plan["_id"])))
                self.table.setItem(row, 1, QTableWidgetItem(plan["destination"]))
                self.table.setItem(row, 2, QTableWidgetItem(plan.get("dates", "-")))
                self.table.setItem(row, 3, QTableWidgetItem(plan.get("budget", "-")))
                
                btn_detail = QPushButton("GÖZ AT")
                btn_detail.setStyleSheet("background-color: #b5ead7; color: #555; border: 2px solid #95dcc6;")
                if 'HAND_CURSOR' in globals() and globals()['HAND_CURSOR']: btn_detail.setCursor(globals()['HAND_CURSOR'])
                btn_detail.clicked.connect(lambda _, p=plan: self.show_plan_details(p))
                self.table.setCellWidget(row, 4, btn_detail)
                
                btn_edit = QPushButton("DÜZENLE")
                btn_edit.setStyleSheet("background-color: #ffccbc; color: #555; border: 2px solid #ffab91;")
                if 'HAND_CURSOR' in globals() and globals()['HAND_CURSOR']: btn_edit.setCursor(globals()['HAND_CURSOR'])
                btn_edit.clicked.connect(lambda _, p=plan: self.open_edit_dialog(p))
                self.table.setCellWidget(row, 5, btn_edit)

                btn_del = QPushButton("🗑️ SİL")
                btn_del.setStyleSheet("background-color: #ef9a9a; color: white; border: 2px solid #e57373;")
                if 'HAND_CURSOR' in globals() and globals()['HAND_CURSOR']: btn_del.setCursor(globals()['HAND_CURSOR'])
                btn_del.clicked.connect(lambda _, r=row: self.delete_plan_row(r))
                self.table.setCellWidget(row, 6, btn_del)
        except Exception as e:
            print(f"Plan yükleme hatası: {e}")

    def show_plan_details(self, plan_data):
        self.detail_window = PlanDetailWindow(plan_data, self.db)
        self.detail_window.exec_() 

    def open_edit_dialog(self, plan_data):
        dialog = PlanEditDialog(self.db, plan_data, self)
        if dialog.exec_(): 
            self.load_plans() 

    def delete_plan_row(self, row):
        plan_id = self.table.item(row, 0).text()
        self.db.delete_plan(plan_id)
        self.load_plans()

    def save_manual_plan(self):
        if not self.m_dest.text():
            QMessageBox.warning(self, "Eksik Bilgi", "Lütfen gidilecek yeri yazın.")
            return

        data = {
            "destination": self.m_dest.text(),
            "dates": self.m_date.text(),
            "route": self.m_route.toPlainText(), 
            "restaurants": self.m_rest.toPlainText(),
            "activities": self.m_act.toPlainText(),
            "budget": self.m_budget.text(),
            "hotel": self.m_hotel.text(),
            "source": "manual"
        }
        
        self.db.save_plan(self.user["_id"], data)
        QMessageBox.information(self, "BAŞARILI", "Manuel plan kaydedildi.")
        
        self.m_dest.clear()
        self.m_date.clear()
        self.m_route.clear() 
        self.m_rest.clear()
        self.m_act.clear()
        self.m_budget.clear()
        self.m_hotel.clear()
        
        self.load_plans()

    def run_agents(self):
        dest = self.a_dest.text()
        dates = self.a_dates.text()
        budget = self.a_budget.text()
        
        if not dest or not dates:
            QMessageBox.warning(self, "EKSİK", "Lütfen yer ve tarih girin.")
            return

        self.btn_ask_umay.setEnabled(False)
        self.progress.setValue(10)
        self.agent_output.setText("Umay Ana diğer agentları çağırıyor...\n")
        
        self.worker = AgentWorker(dest, dates, budget)
        self.worker.finished.connect(self.on_agent_finished)
        self.worker.start()

    def on_agent_finished(self, plan):
        self.progress.setValue(100)
        self.last_agent_plan = plan
        
        text = f"=== UMAY ANA'NIN PLANI ===\n\n"
        text += f"Rota: {plan.get('route', '-')}\n"
        text += f"Yemek (Aş Ata): {plan.get('food', '-')}\n"
        text += f"Aktivite (Yel Ana): {plan.get('activities', '-')}\n"
        text += f"Konaklama (Yurt İyesi): {plan.get('accommodation', '-')}\n"
        
        self.agent_output.setText(text)
        self.btn_ask_umay.setEnabled(True)
        
        if self.chk_google.isChecked() and GoogleCalendarManager:
            try:
                self.agent_output.append("\n>> Google Takvim'e bağlanılıyor...")
                gcal = GoogleCalendarManager()
                link = gcal.add_event(plan)
                self.agent_output.append(f">> BAŞARILI: Google Link: {link}")
            except Exception as e:
                self.agent_output.append(f">> HATA (Google): {str(e)}")

        if self.chk_notion.isChecked() and create_notion_page:
            try:
                self.agent_output.append("\n>> Notion'a bağlanılıyor...")
                link = create_notion_page(plan)
                self.agent_output.append(f">> EKLEME BAŞARILI!\n>> Notion Link: {link}")
            except Exception as e:
                self.agent_output.append(f">> HATA (Notion): {str(e)}")

    def save_agent_plan_to_db(self):
        if self.last_agent_plan:
            self.db.save_plan(self.user["_id"], self.last_agent_plan)
            QMessageBox.information(self, "KAYIT", "Agent planı veritabanına işlendi.")
            self.load_plans()
        else:
            QMessageBox.warning(self, "HATA", "Henüz bir plan üretilmedi.")

# LOGIN PENCERESİ
class LoginWindow(QWidget):
    def __init__(self, db, open_main_callback, start_index=0):
        super().__init__()
        self.db = db
        self.open_main_callback = open_main_callback
        
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(400, 600)
        
        main_layout = QVBoxLayout(self)
        self.frame = QFrame()
        self.frame.setObjectName("LoginFrame")
        self.frame.setStyleSheet("""
            QFrame#LoginFrame {
                background-color: #e3e1ea;
                border: 2px solid #8e99f3;
            }
        """)
        
        self.title_bar = CustomTitleBar(self)
        
        content_layout = QVBoxLayout(self.frame)
        content_layout.setContentsMargins(0,0,0,0)
        content_layout.addWidget(self.title_bar)
        
        self.tabs = QTabWidget()
        self.tabs.setFixedSize(360, 500) 
        self.create_login_ui()
        
        self.tabs.setCurrentIndex(start_index)
        
        container_layout = QVBoxLayout()
        container_layout.addWidget(self.tabs, alignment=Qt.AlignCenter)
        content_layout.addLayout(container_layout)
        
        main_layout.addWidget(self.frame)

    def create_login_ui(self):
        # GİRİŞ SEKMESİ
        self.login_tab = QWidget()
        l_layout = QFormLayout()
        self.l_user = QLineEdit()
        self.l_pass = QLineEdit()
        self.l_pass.setEchoMode(QLineEdit.Password)
        
        btn_login = QPushButton("GİRİŞ YAP")
        if 'HAND_CURSOR' in globals() and globals()['HAND_CURSOR']: 
            btn_login.setCursor(globals()['HAND_CURSOR'])
            
        btn_login.clicked.connect(self.handle_login)
        
        l_layout.addRow("KULLANICI:", self.l_user)
        l_layout.addRow("ŞİFRE:", self.l_pass)
        l_layout.addWidget(btn_login)
        self.login_tab.setLayout(l_layout)

        # KAYIT SEKMESİ
        self.reg_tab = QWidget()
        r_layout = QFormLayout()
        
        self.r_user = QLineEdit()
        self.r_mail = QLineEdit()
        
        self.r_pass = QLineEdit()
        self.r_pass.setEchoMode(QLineEdit.Password)
        self.r_pass.setPlaceholderText("Şifrenizi oluşturun")
        
        self.r_pass_confirm = QLineEdit()
        self.r_pass_confirm.setEchoMode(QLineEdit.Password)
        self.r_pass_confirm.setPlaceholderText("Şifreyi tekrar girin")

        # Sinyalleri widgetlar oluştuktan SONRA bağla ki hata oluşmasın
        self.r_pass.textChanged.connect(self.check_password_rules)
        self.r_pass_confirm.textChanged.connect(self.check_password_rules)
        
        # Kural Etiketleri
        self.lbl_rule_len = QLabel("❌ En az 8 karakter")
        self.lbl_rule_upper = QLabel("❌ En az 1 büyük harf")
        self.lbl_rule_lower = QLabel("❌ En az 1 küçük harf")
        self.lbl_rule_digit = QLabel("❌ En az 1 rakam")
        self.lbl_rule_punct = QLabel("❌ En az 1 noktalama işareti")
        self.lbl_rule_match = QLabel("❌ Şifreler uyuşuyor")

        rules = [self.lbl_rule_len, self.lbl_rule_upper, self.lbl_rule_lower, 
                 self.lbl_rule_digit, self.lbl_rule_punct, self.lbl_rule_match]
        
        for lbl in rules:
            lbl.setStyleSheet("color: red; font-size: 11px; margin-left: 10px;")

        btn_reg = QPushButton("KAYIT OL")
        if 'HAND_CURSOR' in globals() and globals()['HAND_CURSOR']: 
            btn_reg.setCursor(globals()['HAND_CURSOR'])
        btn_reg.clicked.connect(self.handle_register)
        
        r_layout.addRow("KULLANICI:", self.r_user)
        r_layout.addRow("E-POSTA:", self.r_mail)
        r_layout.addRow("ŞİFRE:", self.r_pass)
        r_layout.addRow("ŞİFRE ONAY:", self.r_pass_confirm)
        
        r_layout.addRow("", self.lbl_rule_len)
        r_layout.addRow("", self.lbl_rule_upper)
        r_layout.addRow("", self.lbl_rule_lower)
        r_layout.addRow("", self.lbl_rule_digit)
        r_layout.addRow("", self.lbl_rule_punct)
        r_layout.addRow("", self.lbl_rule_match)
        
        r_layout.addWidget(btn_reg)
        self.reg_tab.setLayout(r_layout)

        self.tabs.addTab(self.login_tab, "GİRİŞ")
        self.tabs.addTab(self.reg_tab, "KAYIT")

    def check_password_rules(self):
        pwd = self.r_pass.text()
        pwd_conf = self.r_pass_confirm.text()
        
        def update_label(label, condition):
            if condition:
                label.setText(label.text().replace("❌", "✅"))
                label.setStyleSheet("color: green; font-size: 11px; margin-left: 10px; font-weight: bold;")
                return True
            else:
                label.setText(label.text().replace("✅", "❌"))
                label.setStyleSheet("color: red; font-size: 11px; margin-left: 10px;")
                return False

        c1 = update_label(self.lbl_rule_len, len(pwd) >= 8)
        c2 = update_label(self.lbl_rule_upper, re.search(r"[A-Z]", pwd))
        c3 = update_label(self.lbl_rule_lower, re.search(r"[a-z]", pwd))
        c4 = update_label(self.lbl_rule_digit, re.search(r"\d", pwd))
        c5 = update_label(self.lbl_rule_punct, re.search(r"[!@#$%^&*(),.?\":{}|<>]", pwd))
        c6 = update_label(self.lbl_rule_match, pwd == pwd_conf and len(pwd) > 0)

        return c1 and c2 and c3 and c4 and c5 and c6

    def handle_login(self):
        success, user = self.db.login_user(self.l_user.text(), self.l_pass.text())
        if success:
            self.open_main_callback(user)
            self.close()
        else:
            QMessageBox.warning(self, "HATA", "Giriş başarısız! Kullanıcı adı veya şifre yanlış.")

    def handle_register(self):
        if not self.check_password_rules():
            QMessageBox.warning(self, "GÜVENLİK UYARISI", "Lütfen şifre kurallarının hepsini sağlayın.")
            return

        success, msg = self.db.register_user(self.r_user.text(), self.r_mail.text(), self.r_pass.text())
        
        if success:
            QMessageBox.information(self, "BAŞARILI", msg)
            self.tabs.setCurrentIndex(0)
            self.l_user.setText(self.r_user.text())
        else:
            QMessageBox.warning(self, "HATA", msg)

    def mousePressEvent(self, event):
        self.title_bar.mousePressEvent(event)
    def mouseMoveEvent(self, event):
        self.title_bar.mouseMoveEvent(event)
    def mouseReleaseEvent(self, event):
        self.title_bar.mouseReleaseEvent(event)

# --- GÜVENLİ BAŞLATMA ---
def main():
    app = QApplication(sys.argv)
    
    # Cursor'ı burada tanımlıyoruz ki diğer sınıflar erişebilsin
    global HAND_CURSOR
    HAND_CURSOR = None # Varsayılan olarak boş

    # Custom Cursor Yükleme
    try:
        # Normal Cursor
        cursor_path = "assets/pixel-cursor.png" 
        if not os.path.exists(cursor_path): cursor_path = "pixel-cursor.png"

        cursor_pix = QPixmap(cursor_path)
        if not cursor_pix.isNull():
            custom_cursor = QCursor(cursor_pix, 0, 0)
            app.setOverrideCursor(custom_cursor)
        
        # El Cursor (Global Değişkene Ata)
        hand_path = "assets/pixel-handpoint.png"
        if not os.path.exists(hand_path): hand_path = "assets/pixel-handpoint"
        
        hand_pix = QPixmap(hand_path)
        if not hand_pix.isNull():
            # El cursor'ı global değişkene atıyoruz
            HAND_CURSOR = QCursor(hand_pix, 10, 0) # Hotspot ayarı (10,0)
            globals()['HAND_CURSOR'] = HAND_CURSOR
            print("El cursor yüklendi.")
    except Exception as e:
        print(f"Cursor hatası: {e}")

    # Stil Yükleme
    try:
        from style import PASTEL_THEME
        app.setStyleSheet(PASTEL_THEME)
    except ImportError:
        print("UYARI: style.py bulunamadı.")

    # Veritabanı
    try:
        db = DatabaseManager()
    except Exception as e:
        QMessageBox.critical(None, "Veritabanı Hatası", f"Veritabanına bağlanılamadı!\n{str(e)}")
        return
    
    # Pencere Açma Callback'i
    def open_main_window(user):
        global main_win
        try:
            main_win = MainWindow(db, user, open_main_window)
            main_win.show()
        except Exception as e:
            import traceback
            QMessageBox.critical(None, "Kritik Hata", f"Ana pencere hatası:\n{traceback.format_exc()}")

    try:
        login_win = LoginWindow(db, open_main_window)
        login_win.show()
    except Exception as e:
        import traceback
        QMessageBox.critical(None, "Başlatma Hatası", f"Hata:\n{traceback.format_exc()}")
        return
    
    sys.exit(app.exec_()) 

if __name__ == "__main__":
    main()