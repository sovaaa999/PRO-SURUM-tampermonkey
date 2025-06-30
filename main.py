import sys
import os
import json
import time
import random
import threading
import traceback
from datetime import datetime
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                           QTextEdit, QComboBox, QMessageBox, QFileDialog,
                           QScrollArea, QFrame, QSizePolicy, QSpacerItem,
                           QListWidget, QListWidgetItem)
from PyQt5.QtGui import QFont, QIcon, QColor, QPalette
from PyQt5.QtMultimedia import QSound
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException
import pygame
from keyword_sound_group_panel import KeywordSoundGroupPanel
from settings_dialog import SettingsDialog  # Ayarlar penceresi için import
from webdriver_manager.chrome import ChromeDriverManager
import logging
from selenium.webdriver.chrome.service import Service
import queue
from flask import Flask, request, jsonify
from flask_cors import CORS
from collections import deque

logging.basicConfig(
    filename='uygulama.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)

# Platform ve selector önerileri
PLATFORM_ICONS = {
    "YouTube": "🟥",
    "Twitch": "🟪",
    "Kick": "🟩",
    "BigoLive": "🟦",
    "Tango": "🟧",
    "TikTok": "⬛",
    "Diğer": "🔘"
}
def get_default_platforms():
    return {
        "YouTube": {"chat": "#chat #items > *", "status": [{"type": "css", "selector": ".ytp-error"}]} ,
        "Twitch": {"chat": ".chat-scrollable-area__message-container", "status": [{"type": "css", "selector": ".tw-offline"}]},
        "Kick": {"chat": ".chat-messages-container .chat-message", "status": []},
        "BigoLive": {"chat": "div.chat-item-inner", "status": [
            {"type": "text", "selector": "body", "text": "Yayıncı geliyor"},
            {"type": "css", "selector": ".room-end"},
            {"type": "css", "selector": ".end-tip"}
        ]},
        "Tango": {"chat": ".chat-messages .message", "status": []},
        "TikTok": {"chat": ".chat-item", "status": [{"type": "css", "selector": ".webcast-player-ended"}]},
        "Diğer": {"chat": "", "status": []}
    }

class SettingsManager:
    DEFAULTS = {
        "last_link": "", 
        "last_selector": "", 
        "last_platform": "YouTube", 
        "platforms": get_default_platforms(), 
        "status_retry_interval": 30, 
        "chat_method": "DOM",
        "spam_prevention_time": 5  # Varsayılan 5 saniye
    }

    def __init__(self, path="ayarlarfarida.json"):
        self.path = path
        self.data = dict(self.DEFAULTS)
        self.load()
    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except Exception:
            # Eksik ayarları tamamla
            for k, v in self.DEFAULTS.items():
                if k not in self.data:
                    self.data[k] = v
    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)


# Platform ve selector önerileri
PLATFORM_ICONS = {
    "YouTube": "🟥",
    "Twitch": "🟪",
    "Kick": "🟩",
    "BigoLive": "🟦",
    "Tango": "🟧",
    "TikTok": "⬛",
    "Diğer": "🔘"
}
def get_default_platforms():
    return {
        "YouTube": {"chat": "#chat #items > *", "status": [{"type": "css", "selector": ".ytp-error"}]} ,
        "Twitch": {"chat": ".chat-scrollable-area__message-container", "status": [{"type": "css", "selector": ".tw-offline"}]},
        "Kick": {"chat": ".chat-messages-container .chat-message", "status": []},
        "BigoLive": {"chat": "div.chat-item-inner", "status": [
            {"type": "text", "selector": "body", "text": "Yayıncı geliyor"},
            {"type": "css", "selector": ".room-end"},
            {"type": "css", "selector": ".end-tip"}
        ]},
        "Tango": {"chat": ".chat-messages .message", "status": []},
        "TikTok": {"chat": ".chat-item", "status": [{"type": "css", "selector": ".webcast-player-ended"}]},
        "Diğer": {"chat": "", "status": []}
    }

def get_platform_selectors():
    try:
        with open("ayarlarfarida.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("platforms", get_default_platforms())
    except Exception:
        return get_default_platforms()

def get_platform_status_selectors(platform):
    selectors = get_platform_selectors()
    if platform in selectors:
        v = selectors[platform]
        if isinstance(v, dict) and "status" in v:
            return v["status"]
    return []

def get_platform_chat_selector(platform):
    selectors = get_platform_selectors()
    if platform in selectors:
        v = selectors[platform]
        if isinstance(v, dict) and "chat" in v:
            return v["chat"]
        elif isinstance(v, str):
            return v
    return ""

class SettingsManager:
    DEFAULTS = {"last_link": "", "last_selector": "", "last_platform": "YouTube", "platforms": get_default_platforms(), "status_retry_interval": 30, "chat_method": "DOM"}

    def __init__(self, path="ayarlarfarida.json"):
        self.path = path
        self.data = dict(self.DEFAULTS)
        self.load()
    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except Exception:
            # Eksik ayarları tamamla
            for k, v in self.DEFAULTS.items():
                if k not in self.data:
                    self.data[k] = v
    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    def update(self, link, selector, platform, status_retry_interval=None, chat_method=None):
        self.data["last_link"] = link
        self.data["last_selector"] = selector
        self.data["last_platform"] = platform
        if status_retry_interval is not None:
            self.data["status_retry_interval"] = status_retry_interval
        if chat_method is not None:
            self.data["chat_method"] = chat_method
        self.save()
    def get_platforms(self):
        return self.data.get("platforms", get_default_platforms())
    def set_platforms(self, platforms):
        self.data["platforms"] = platforms
        self.save()

class Toast(QtWidgets.QWidget):
    def __init__(self, parent, text, color):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.ToolTip)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.label = QtWidgets.QLabel(text, self)
        self.label.setStyleSheet(f"background: {color}; color: #fff; padding: 12px 24px; border-radius: 16px; font-size: 18px;")
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.label)
        self.resize(self.label.sizeHint())
        QtCore.QTimer.singleShot(2200, self.close)
    def showEvent(self, event):
        g = self.parent().geometry()
        self.move(g.center().x()-self.width()//2, g.top()+60)

# Flask mesaj kuyruğu ve sunucu
flask_message_queue = queue.Queue()
flask_app = Flask(__name__)
CORS(flask_app)

@flask_app.route('/message', methods=['POST'])
def receive_message():
    data = request.get_json(force=True)
    msg = data.get('message', '').strip()
    if msg:
        flask_message_queue.put(msg)
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'empty'}), 400

# Flask sunucusunu ayrı thread'de başlat
class FlaskServerThread(threading.Thread):
    def __init__(self, port=5001):
        super().__init__(daemon=True)
        self.port = port
    def run(self):
        flask_app.run(port=self.port, threaded=True, use_reloader=False)

# ChatFetcher thread'i: Sadece mesaj alma kısmı Flask kuyruğundan olacak
class ChatFetcher(QtCore.QThread):
    new_message = QtCore.pyqtSignal(str)
    status_update = QtCore.pyqtSignal(str, str)
    toast = QtCore.pyqtSignal(str, str)

    def __init__(self, link, selector, max_wait_minutes, retry_interval, platform=None):
        super().__init__()
        self.link = link
        self.selector = selector
        self.max_wait_minutes = max_wait_minutes
        self.retry_interval = retry_interval
        self.platform = platform
        self.running = True
        self._connected = False
        self._is_stream_offline = False
        self._last_cleanup_time = time.time()
        self._cleanup_interval = 60  # DOM temizliği artık 1 dakikada bir

    def _is_driver_alive(self):
        try:
            if hasattr(self, 'driver') and self.driver is not None:
                _ = self.driver.window_handles
                return True
            return False
        except Exception:
            return False

    def _cleanup_dom(self):
        try:
            if self.platform == "Bigo":
                self.driver.execute_script("""
                    var chatContainer = document.querySelector('.chat-container');
                    if (chatContainer) {
                        var messages = chatContainer.children;
                        var maxMessages = 100;
                        if (messages.length > maxMessages) {
                            for (var i = 0; i < messages.length - maxMessages; i++) {
                                messages[i].remove();
                            }
                        }
                    }
                """)
            self._last_cleanup_time = time.time()
        except Exception as e:
            print(f"DOM temizleme hatası: {e}")

    def run(self):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument(r"--user-data-dir=C:\\Users\\muham\\AppData\\Local\\NEW1_Chrome\\User Data\\selenium_profile")
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        try:
            print("[ADIM 1/4] Tarayıcı sürücüsü başlatılıyor...")
            chromedriver_path = ChromeDriverManager().install()
            print("Kullanılan chromedriver yolu:", chromedriver_path)
            service = Service(chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            print("[ADIM 2/4] Tarayıcı sürücüsü başarıyla başlatıldı.")
            print(f"[ADIM 3/4] Sayfa yükleniyor: {self.link}")
            self.driver.get(self.link)
            print("[ADIM 4/4] Sayfa başarıyla yüklendi.")
        except Exception as e:
            logging.error("Hata oluştu: %s", e, exc_info=True)
            print(f"[HATA] Tarayıcı işleminde bir sorun oluştu. Hata Detayı: {traceback.format_exc()}")
            self.status_update.emit("Bağlantı Hatası", "#e74c3c")
            if hasattr(self, 'driver') and self.driver:
                self.driver.quit()
                self.driver = None
            return
        self.status_update.emit("Bağlandı", "#27ae60")
        self.toast.emit("Bağlantı başarılı! Tampermonkey scripti çalışıyor...", "#27ae60")
        self._connected = True
        last_message_count = 0
        last_message_time = time.time()
        max_wait_minutes = self.max_wait_minutes
        offline_selectors = get_platform_status_selectors(self.platform) if self.platform else []
        is_offline = False
        while self.running:
            if not self._is_driver_alive():
                self.status_update.emit("Tarayıcı kapatıldı veya bağlantı koptu.", "#e74c3c")
                self.toast.emit("Tarayıcı kapatıldı veya bağlantı koptu.", "#e74c3c")
                break
            try:
                is_offline = False
                for sel in offline_selectors:
                    try:
                        if sel.get("type") == "css" and self.driver.find_element(By.CSS_SELECTOR, sel["selector"]).is_displayed():
                            is_offline = True
                            break
                        elif sel.get("type") == "text" and sel.get("text") in self.driver.find_element(By.CSS_SELECTOR, sel["selector"]).text:
                            is_offline = True
                            break
                    except Exception:
                        continue
                if getattr(self, '_is_stream_offline', False) and not is_offline:
                    self.status_update.emit("Bağlandı", "#27ae60")
                    self.toast.emit("Yayın tekrar açıldı, bağlandı!", "#27ae60")
                self._is_stream_offline = is_offline
                timed_out = (time.time() - last_message_time) > (max_wait_minutes * 60)
                if is_offline or timed_out:
                    if is_offline:
                        status_msg = "Yayın kapalı, yeniden deneniyor..."
                    else:
                        status_msg = f"{max_wait_minutes} dakika mesaj alınamadı, yeniden deneniyor..."
                    self.status_update.emit(status_msg, "#e67e22")
                    self.toast.emit(status_msg, "#e67e22")
                    try:
                        # Yayın kapalı durumlarında da tarayıcı kontrolü yap
                        if not self._is_driver_alive():
                            self.status_update.emit("Tarayıcı kapatıldı veya bağlantı koptu.", "#e74c3c")
                            self.toast.emit("Tarayıcı kapatıldı veya bağlantı koptu.", "#e74c3c")
                            break
                        self.driver.get(self.link)
                        time.sleep(3)
                        last_message_count = 0
                        last_message_time = time.time()
                        self.driver.execute_script('if(window.restartChatReader){window.restartChatReader();}')
                        print("Sayfa yenilendi ve Tampermonkey yeniden başlatıldı.")
                    except Exception as e:
                        print(f"Sayfa yenileme hatası: {e}")
                        time.sleep(self.retry_interval)
                    if is_offline:
                        # Yayın kapalı durumlarında da tarayıcı kontrolü yap
                        for _ in range(self.status_retry_interval):  # 5 saniye = 5 x 1s
                            if not self._is_driver_alive():
                                self.status_update.emit("Tarayıcı kapatıldı veya bağlantı koptu.", "#e74c3c")
                                self.toast.emit("Tarayıcı kapatıldı veya bağlantı koptu.", "#e74c3c")
                                break
                            self.msleep(1000)  # 1 saniye bekle
                        else:
                            continue  # Sadece tarayıcı açıksa continue
                        break  # Tarayıcı kapalıysa ana döngüden de çık
                    continue
                # SADECE BURASI DEĞİŞTİ: Mesajlar Flask kuyruğundan alınacak
                try:
                    new_messages = []
                    # Mesaj alma süresini sabitle (maksimum 100ms)
                    start_time = time.time()
                    while time.time() - start_time < 0.1:  # 100ms maksimum
                        try:
                            msg = flask_message_queue.get_nowait()
                            if msg.strip():
                                new_messages.append(msg.strip())
                        except queue.Empty:
                            break
                    if new_messages:
                        last_message_time = time.time()
                        for msg in new_messages:
                            self.new_message.emit(msg)
                        if not self._connected:
                            self.status_update.emit("Bağlandı", "#27ae60")
                            self.toast.emit("Yeni mesajlar alınıyor!", "#27ae60")
                            self._connected = True
                except Exception as e:
                    print(f"Flask mesaj okuma hatası: {e}")
                self.msleep(100)  # 50ms yerine 100ms yap
            except StaleElementReferenceException:
                print("DOM değişti (StaleElementReferenceException), döngü devam ediyor.")
                continue
            except Exception as e:
                print(f"Ana döngü hatası: {e}")
                time.sleep(2)
                continue
        if self.driver:
            print('[ChatFetcher] Thread sonlanıyor, tarayıcı kapatılıyor (driver.quit çağrılacak)')
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None
        self.status_update.emit("Durduruldu", "#7f8c8d")

    def stop(self):
        self.running = False
        if hasattr(self, 'driver') and self.driver is not None:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def refresh_page(self):
        if self.driver:
            try:
                self.driver.get(self.link)
                time.sleep(2)
                try:
                    self.driver.execute_script('if(window.restartChatReader){window.restartChatReader();}')
                except Exception as e:
                    print(f"Tampermonkey restartChatReader çağrısı hatası: {e}")
            except Exception as e:
                print(f"Sayfa yenileme hatası: {e}")

class PlatformEditDialog(QtWidgets.QDialog):
    def __init__(self, parent, platforms):
        super().__init__(parent)
        self.setWindowTitle("Platformları Düzenle")
        self.setModal(True)
        self.resize(420, 350)
        self.platforms = dict(platforms)
        main_layout = QtWidgets.QVBoxLayout(self)
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.addItems(self.platforms.keys())
        # Koyu tema stil
        self.list_widget.setStyleSheet('''
            QListWidget {
                background: #23243a;
                color: #e0e0e0;
                border-radius: 10px;
                padding: 8px;
                font-size: 19px;
                font-family: 'Montserrat', 'Segoe UI', Arial, sans-serif;
            }
            QListWidget::item {
                background: #23243a;
                color: #e0e0e0;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QListWidget::item:selected {
                background: #31344b;
                color: #fff;
            }
        ''')
        main_layout.addWidget(self.list_widget)
        form = QtWidgets.QFormLayout()
        self.name_input = QtWidgets.QLineEdit()
        self.selector_input = QtWidgets.QLineEdit()
        form.addRow("Platform Adı:", self.name_input)
        form.addRow("Selector:", self.selector_input)
        main_layout.addLayout(form)
        btn_layout = QtWidgets.QHBoxLayout()
        add_btn = QtWidgets.QPushButton("Ekle / Güncelle")
        del_btn = QtWidgets.QPushButton("Sil")
        close_btn = QtWidgets.QPushButton("Kapat")
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addWidget(close_btn)
        main_layout.addLayout(btn_layout)
        self.list_widget.currentTextChanged.connect(self.load_selected)
        add_btn.clicked.connect(self.add_or_update)
        del_btn.clicked.connect(self.delete_platform)
        close_btn.clicked.connect(self.accept)
    def load_selected(self, name):
        self.name_input.setText(name)
        val = self.platforms.get(name, "")
        if isinstance(val, dict):
            self.selector_input.setText(val.get("chat", ""))
        else:
            self.selector_input.setText(val)
    def add_or_update(self):
        name = self.name_input.text().strip().replace('"', '').replace("'", "")
        selector = self.selector_input.text().strip().replace('"', '').replace("'", "")
        if not name or len(name) < 2:
            QtWidgets.QMessageBox.warning(self, "Uyarı", "Platform adı en az 2 karakter olmalı ve tırnak işareti içermemelidir!")
            return
        # Dict formatı ile kaydet, eski status korunsun
        prev = self.platforms.get(name, {})
        status = prev.get("status", []) if isinstance(prev, dict) else []
        self.platforms[name] = {"chat": selector, "status": status}
        self.refresh()
        self.name_input.setText("")
        self.selector_input.setText("")
    def delete_platform(self):
        name = self.name_input.text().strip()
        if name in self.platforms:
            del self.platforms[name]
            self.refresh()
    def refresh(self):
        self.list_widget.clear()
        self.list_widget.addItems(self.platforms.keys())
    def get_platforms(self):
        return self.platforms

class MessageWorker(QThread):
    message_processed = pyqtSignal(str, str)  # mesaj, tip (yasakli/keyword/normal)
    sound_request = pyqtSignal(str)  # ses dosyası yolu
    def __init__(self, message_queue, yasakli_kelimeler, keyword_groups, spam_prevention_time):
        super().__init__()
        self.message_queue = message_queue
        self.yasakli_kelimeler = yasakli_kelimeler
        self.keyword_groups = keyword_groups
        self.spam_prevention_time = spam_prevention_time
        self.running = True
        self.keyword_last_triggered = {}
        self.group_last_sound = {}
        self.group_sound_queues = {}
    def run(self):
        while self.running:
            try:
                msg = self.message_queue.get(timeout=1)
                if msg:
                    normalized_msg = msg.lower()
                    message_words = normalized_msg.split()
                    yasakli_bulundu = False
                    # Yasaklı kelime kontrolü
                    for kelime in self.yasakli_kelimeler:
                        if not kelime:
                            continue
                        if ',' in kelime:
                            alt_kelimeler = [k.strip().lower() for k in kelime.split(',') if k.strip()]
                            if all(alt in normalized_msg for alt in alt_kelimeler):
                                yasakli_bulundu = True
                                break
                        elif ' ' in kelime:
                            if kelime.lower() in normalized_msg:
                                yasakli_bulundu = True
                                break
                        else:
                            if kelime.lower() in message_words:
                                yasakli_bulundu = True
                                break
                    if yasakli_bulundu:
                        self.message_processed.emit(msg, "yasakli")
                        continue
                    # Anahtar kelime kontrolü
                    matched_entries = []
                    for group in self.keyword_groups:
                        for kw in group.get('words', []):
                            if kw.lower() in normalized_msg:
                                matched_entries.append((group, kw))
                    if not matched_entries:
                        self.message_processed.emit(msg, "normal")
                        continue
                    # Spam önleme
                    import time
                    sound_groups_to_play = []
                    current_time = time.time()
                    played_keywords = set()
                    for group, kw_entry in matched_entries:
                        group_id = tuple(sorted(group.get('words', [])))
                        last_triggered_group = self.keyword_last_triggered.get(group_id, 0)
                        if self.spam_prevention_time > 0 and current_time - last_triggered_group < self.spam_prevention_time:
                            continue
                        self.keyword_last_triggered[group_id] = current_time
                        sound_groups_to_play.append(group)
                        played_keywords.add(kw_entry)
                    # Ses dosyası
                    sound_paths = []
                    for group in sound_groups_to_play:
                        sounds = group.get('sounds', [])
                        if not sounds:
                            continue
                        group_id = tuple(sorted(group.get('words', [])))
                        if group_id not in self.group_sound_queues or not self.group_sound_queues[group_id]:
                            import random
                            self.group_sound_queues[group_id] = sounds.copy()
                            random.shuffle(self.group_sound_queues[group_id])
                            last = self.group_last_sound.get(group_id)
                            if last and len(self.group_sound_queues[group_id]) > 1 and self.group_sound_queues[group_id][0] == last:
                                self.group_sound_queues[group_id].append(self.group_sound_queues[group_id].pop(0))
                        chosen_sound = self.group_sound_queues[group_id].pop(0)
                        sound_paths.append(chosen_sound)
                        self.group_last_sound[group_id] = chosen_sound
                    self.message_processed.emit(msg, "keyword")
                    if sound_paths:
                        self.sound_request.emit(sound_paths[0])
            except queue.Empty:
                continue
    def stop(self):
        self.running = False

class SoundPlayerThread(QThread):
    sound_finished = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.sound_path = None
        self._play_request = threading.Event()
        self._stop_request = threading.Event()
        self._pygame_initialized = False

    def play(self, sound_path):
        self.sound_path = sound_path
        self._play_request.set()

    def run(self):
        while not self._stop_request.is_set():
            self._play_request.wait()
            if self.sound_path:
                try:
                    import pygame
                    if not self._pygame_initialized:
                        pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
                        self._pygame_initialized = True
                    pygame.mixer.music.load(self.sound_path)
                    pygame.mixer.music.play()
                    # Ses süresini hesapla
                    duration_ms = self._get_wav_duration_ms(self.sound_path)
                    time.sleep(duration_ms / 1000)
                    pygame.mixer.music.stop()
                except Exception as e:
                    print(f'[SoundPlayerThread] Ses çalınamadı: {e}')
                self.sound_path = None
                self._play_request.clear()
                self.sound_finished.emit()

    def _get_wav_duration_ms(self, path):
        try:
            import wave
            with wave.open(path, 'rb') as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                duration = frames / float(rate)
                return int(duration * 1000)
        except Exception as e:
            print(f'[SoundPlayerThread] WAV süresi okunamadı, default 2500 ms: {e}')
            return 2500

    def stop(self):
        self._stop_request.set()
        self._play_request.set()

class MainWindow(QtWidgets.QFrame):
    def __init__(self):
        super().__init__()
        self.settings = SettingsManager()  # Kalıcı ayar yönetimi için eklendi
        self.setWindowTitle("FARIDA")
        self.setGeometry(300, 120, 650, 780)
        self.setObjectName("mainFrame")
        self.setStyleSheet(self.stylesheet())
        self.setFont(QtGui.QFont("Segoe UI", 11))
        self.settings = SettingsManager()
        self.platform_selectors = self.settings.get_platforms()
        self.chat_fetcher = None
        self.toast_widget = None
        self.seen_messages = set()  # Yeni: İşlenen mesajlar
        self.sound_queue = []
        self.sound_playing = False
        self.current_sound = None
        self.keyword_last_triggered = {}  # Her anahtar kelimenin son tetiklenme zamanını tutacak sözlük
        self.group_last_sound = {} # YENİ: Her grup için son çalınan sesi hatırla
        self.group_sound_queues = {} # YENİ: Her grup için shuffle edilmiş ses kuyruğu
        self._is_stream_offline = False # YENİ: Yayın durumu
        self.flask_thread = None
        self.sound_thread = SoundPlayerThread()
        self.sound_thread.sound_finished.connect(self._on_sound_finished)
        self.sound_thread.start()
        self.init_ui()
        # Yeni: Mesaj timeout kontrolü için
        self._last_message_time = None  # Son mesajın geldiği zaman, başlangıçta None
        self._message_retry_timer = QtCore.QTimer(self)
        self._message_retry_timer.timeout.connect(self._check_message_timeout)
        self._message_retry_timer.start(1000)  # Her 1 saniyede bir kontrol et

        # Ayarlardaki grupları panelde göster
        if hasattr(self, 'keyword_sound_panel') and hasattr(self.settings, 'data'):
            groups = self.settings.data.get('groups', [])
            print('Grup verisi yükleniyor:', groups)
            print('Ayar dosyası:', self.settings.path)
            print('Tüm settings:', self.settings.data)
            self.keyword_sound_panel.load_groups_from_settings(groups)
            print('load_groups_from_settings ÇAĞRILDI')
        self.load_settings()

        # MainWindow içinde:
        # self.message_queue = queue.Queue()
        # self.message_worker = MessageWorker(self.message_queue, yasakli_kelimeler, keyword_groups, spam_prevention_time)
        # self.message_worker.message_processed.connect(self.on_message_processed)
        # self.message_worker.sound_request.connect(self.play_sound_queued)
        # self.message_worker.start()

        self.messages = deque(maxlen=30)  # Son 30 mesajı tutacak deque

    def _check_message_timeout(self):
        """Belirli süre mesaj gelmezse yayını dener ve yeni bekleme süresi başlatır"""
        # YENİ: Yayın kapalıysa timeout kontrolü yapma
        if self._is_stream_offline:
            return  # Yayın kapalıysa mesaj timeout sayacı çalışmasın
        if self.chat_fetcher and self.chat_fetcher.isRunning():
            if self._last_message_time is None:  # Henüz hiç mesaj alınmadıysa deneme yapma
                return
            current_time = time.time()
            message_retry_interval = self.settings.data.get("message_retry_interval", 30) # Ayarlardan al

            if (current_time - self._last_message_time > message_retry_interval):
                self.set_status("Uzun süredir mesaj alınamadı, sayfa yenileniyor...", "warning")
                self.show_toast("Uzun süredir mesaj alınamadı, sayfa yenileniyor...", "#e67e22")
                self.chat_fetcher.refresh_page() # ChatFetcher'dan sayfayı yenilemesini iste
                self._last_message_time = current_time  # Deneme yapıldıktan sonra yeni bekleme süresi başlat

    def play_sound_queued(self, sound_path):
        import os
        if not os.path.exists(sound_path):
            print(f'[play_sound_queued] Ses dosyası bulunamadı: {sound_path}')
            return
        if sound_path in self.sound_queue:
            print(f'[play_sound_queued] Ses zaten kuyrukta: {os.path.basename(sound_path)}')
            return
        self.sound_queue.append(sound_path)
        if not self.sound_playing:
            self._play_next_sound_async()
        else:
            print(f'[play_sound_queued] Ses çalıyor, kuyruğa eklendi: {os.path.basename(sound_path)}')

    def _play_next_sound_async(self):
        if self.sound_playing:
            print('[SOUND] Ses zaten çalıyor, bekle...')
            return
        if self.sound_queue:
            sound_path = self.sound_queue.pop(0)
            self.sound_playing = True
            try:
                self.sound_thread.play(sound_path)
                print(f'[SOUND] Ses thread ile başlatıldı: {os.path.basename(sound_path)}')
            except Exception as e:
                print(f'[SOUND] Thread ile ses başlatma hatası: {e}')
                self.sound_playing = False
                self._play_next_sound_async()
        else:
            self.sound_playing = False

    def _on_sound_finished(self):
        print('[SOUND] Ses bitti, sıradaki sesi kontrol et...')
        self.sound_playing = False
        QTimer.singleShot(100, self._play_next_sound_async)

    def stylesheet(self):
        return """
        #mainFrame {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #23243a, stop:1 #1a1b2b);
            border-radius: 28px;
            border: 2.5px solid #23272F;
            font-family: 'Montserrat', 'Segoe UI', 'Arial Black', Arial, sans-serif;
        }
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4e9fff, stop:1 #3086f0);
            color: #fff;
            font-size: 17px;
            font-family: 'Segoe UI', 'Arial', sans-serif;
            font-weight: bold;
            border: none;
            border-radius: 14px;
            padding: 10px 0;
            min-width: 90px;
            min-height: 36px;
            box-shadow: 0 2px 12px #0002;
            transition: background 0.2s;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5baaff, stop:1 #3086f0);
            color: #fff;
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3575c6, stop:1 #2461a4);
            color: #e0e8ff;
        }
        QLabel#titleLbl {
            color: #fff;
            font-size: 38px;
            font-family: 'Montserrat', 'Arial Black', Arial, sans-serif;
            font-weight: 900;
            letter-spacing: 2px;
            padding: 30px 0 18px 0;
            text-shadow: 0 4px 24px #1b1b1b99;
        }
        QFrame#cardBox {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #262743, stop:1 #23243a);
            border-radius: 20px;
            padding: 28px 38px 22px 38px;
            margin-bottom: 22px;
            box-shadow: 0px 8px 36px #00000070, 0 1.5px 0 #4F8EF7;
            border: 2px solid #31344b;
        }
        QFormLayout > QLabel {
            color: #faffff;
            font-size: 22px;
            font-weight: 900;
            margin-bottom: 8px;
            letter-spacing: 1.2px;
            text-shadow: 0 0 8px #fff, 0 2px 12px #000;
        }
        QLineEdit, QComboBox {
            background: #181a24;
            color: #fff;
            border-radius: 12px;
            padding: 14px 16px;
            font-size: 21px;
            font-family: 'Montserrat', 'Segoe UI', Arial, sans-serif;
            font-weight: 600;
            border: 2px solid #31344b;
            margin-bottom: 8px;
        }
        QComboBox QAbstractItemView {
            background: #23243a;
            color: #e0e0e0;
            border-radius: 10px;
            font-size: 19px;
            font-family: 'Montserrat', 'Segoe UI', Arial, sans-serif;
            outline: none;
        }
        QComboBox QAbstractItemView::item {
            background: #23243a;
            color: #e0e0e0;
            border-radius: 6px;
            padding: 6px 12px;
        }
        QComboBox QAbstractItemView::item:selected {
            background: #31344b;
            color: #fff;
        }
        QLineEdit:focus, QComboBox:focus {
            border: 2px solid #4F8EF7;
            background: #21243a;
        }
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4e9fff, stop:1 #3086f0);
            color: #fff;
            font-size: 17px;
            font-family: 'Segoe UI', 'Arial', sans-serif;
            font-weight: bold;
            border: none;
            border-radius: 14px;
            padding: 10px 0;
            min-width: 90px;
            min-height: 36px;
            box-shadow: 0 2px 12px #0002;
            transition: background 0.2s;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5baaff, stop:1 #3086f0);
            color: #fff;
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3575c6, stop:1 #2461a4);
            color: #e0e8ff;
        }
        QLabel#statusLabel {
            font-size: 19px;
            font-family: 'Montserrat', 'Segoe UI', Arial, sans-serif;
            font-weight: 800;
            padding: 10px 24px;
            border-radius: 16px;
            min-width: 140px;
            color: #fff;
            margin-bottom: 12px;
            box-shadow: 0 2px 12px #00000033;
            letter-spacing: 0.5px;
        }
        QTextEdit#chatBox {
            background: #191B20;
            color: #fff;
            border-radius: 20px;
            font-size: 21px;
            font-family: 'Montserrat', 'Segoe UI', Arial, sans-serif;
            font-weight: 600;
            padding: 18px 16px;
            border: 2px solid #31344b;
            margin-top: 12px;
            margin-bottom: 6px;
        }
        QLabel#platformIcon {
            font-size: 33px;
            margin-right: 12px;
        }
        """
    def open_settings(self):
        dialog = SettingsDialog(self, self.settings.data.get("status_retry_interval", 30), self.platform_selectors)
        if dialog.exec_():
            # Ayarları kaydet
            self.settings.data["status_retry_interval"] = dialog.get_status_retry_interval()
            self.settings.data["message_retry_interval"] = dialog.get_message_retry_interval()
            self.settings.data["spam_prevention_time"] = dialog.get_spam_prevention_time()
            self.platform_selectors = dialog.get_platform_settings()
            self.settings.set_platforms(self.platform_selectors)
            self.settings.save()
            # Platform seçimini güncelle
            self.platform_combo.clear()
            self.platform_combo.addItems(list(self.platform_selectors.keys()))
            self.on_platform_change(self.platform_combo.currentText())
            # Toast mesajı göster
            self.show_toast("Ayarlar kaydedildi!", "#27ae60")
    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(24, 16, 24, 24)
        main_layout.setSpacing(10)
        # Sekmeli yapı
        self.tab_widget = QtWidgets.QTabWidget()
        # 1. sekme: Chat
        chat_tab = QtWidgets.QWidget()
        chat_tab.setStyleSheet("background: #23243a;")
        chat_layout = QtWidgets.QVBoxLayout(chat_tab)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(10)
        # Başlık ve logo
        title = QtWidgets.QLabel("FARIDA")
        title.setObjectName("titleLbl")
        title.setAlignment(QtCore.Qt.AlignCenter)
        chat_layout.addWidget(title)
        # Durum etiketi
        self.status_label = QtWidgets.QLabel("Hazır")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(QtCore.Qt.AlignCenter)
        chat_layout.addWidget(self.status_label)
        # Kart box
        card = QtWidgets.QFrame()
        card.setObjectName("cardBox")
        card_layout = QtWidgets.QFormLayout(card)
        card_layout.setLabelAlignment(QtCore.Qt.AlignRight)
        card_layout.setFormAlignment(QtCore.Qt.AlignLeft)
        # Chat Linki
        link_label = QtWidgets.QLabel("Chat Linki:")
        link_label.setStyleSheet("color: #fff; font-size: 22px; font-weight: 900; letter-spacing: 1.2px;")
        self.link_input = QtWidgets.QLineEdit()
        self.link_input.setPlaceholderText("Chat Linki Giriniz...")
        card_layout.addRow(link_label, self.link_input)
        # Platform seçici
        plat_label = QtWidgets.QLabel("Platform:")
        plat_label.setStyleSheet("color: #fff; font-size: 22px; font-weight: 900; letter-spacing: 1.2px;")
        plat_layout = QtWidgets.QHBoxLayout()
        self.platform_icon = QtWidgets.QLabel(PLATFORM_ICONS["YouTube"])
        self.platform_icon.setObjectName("platformIcon")
        plat_layout.addWidget(self.platform_icon)
        self.platform_combo = QtWidgets.QComboBox()
        self.platform_combo.addItems(list(self.platform_selectors.keys()))
        self.platform_combo.currentTextChanged.connect(self.on_platform_change)
        plat_layout.addWidget(self.platform_combo)
        plat_layout.setSpacing(6)
        plat_layout.setContentsMargins(0,0,0,0)
        plat_widget = QtWidgets.QWidget()
        plat_widget.setLayout(plat_layout)
        card_layout.addRow(plat_label, plat_widget)
        # Selector editörü
        selector_label = QtWidgets.QLabel("Selector:")
        selector_label.setStyleSheet("color: #fff; font-size: 22px; font-weight: 900; letter-spacing: 1.2px;")
        self.selector_input = QtWidgets.QLineEdit()
        self.selector_input.setPlaceholderText("CSS Selector...")
        card_layout.addRow(selector_label, self.selector_input)
        self.on_platform_change(self.platform_combo.currentText())
        chat_layout.addWidget(card)
        # Başlat/Durdur butonları
        btn_layout = QtWidgets.QHBoxLayout()
        MODERN_BUTTON_STYLE = '''
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4e9fff, stop:1 #3086f0);
            color: #fff;
            font-size: 17px;
            font-family: 'Segoe UI', 'Arial', sans-serif;
            font-weight: bold;
            border: none;
            border-radius: 14px;
            padding: 10px 0;
            min-width: 90px;
            min-height: 36px;
            box-shadow: 0 2px 12px #0002;
            transition: background 0.2s;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #5baaff, stop:1 #3086f0);
            color: #fff;
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3575c6, stop:1 #2461a4);
            color: #e0e8ff;
        }
        '''
        self.start_btn = QtWidgets.QPushButton("Başlat")
        self.start_btn.setStyleSheet(MODERN_BUTTON_STYLE)
        self.start_btn.clicked.connect(self.start_fetch)
        self.stop_btn = QtWidgets.QPushButton("Durdur")
        self.stop_btn.setStyleSheet(MODERN_BUTTON_STYLE)
        self.stop_btn.clicked.connect(self.stop_fetch)
        edit_platform_btn = QtWidgets.QPushButton("Platformları Düzenle")
        edit_platform_btn.setStyleSheet(MODERN_BUTTON_STYLE)
        edit_platform_btn.clicked.connect(self.edit_platforms)
        settings_btn = QtWidgets.QPushButton("Ayarlar")
        settings_btn.setStyleSheet(MODERN_BUTTON_STYLE)
        settings_btn.clicked.connect(self.open_settings)
        btn_layout.addWidget(self.start_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(edit_platform_btn)
        btn_layout.addWidget(settings_btn)
        btn_widget = QtWidgets.QWidget()
        btn_widget.setLayout(btn_layout)
        chat_layout.addWidget(btn_widget)
        # Chat kutusu
        self.chat_box = QtWidgets.QTextEdit()
        self.chat_box.setReadOnly(True)
        self.chat_box.setStyleSheet("background: #23243a; color: #fff; font-size: 18px; border-radius: 10px; padding: 12px;")
        chat_layout.addWidget(self.chat_box)
        self.set_status("Hazır", "#7f8c8d")
        self.tab_widget.addTab(chat_tab, "Chat")
        # 2. sekme: Özellikler
        features_tab = QtWidgets.QWidget()
        features_tab.setStyleSheet("background: #23243a;")
        features_layout = QtWidgets.QVBoxLayout(features_tab)
        features_layout.setContentsMargins(24, 24, 24, 24)
        features_layout.setSpacing(14)
        features_title = QtWidgets.QLabel("Anahtar Kelime & Ses Grupları")
        features_title.setAlignment(QtCore.Qt.AlignCenter)
        features_title.setStyleSheet("font-size: 25px; font-weight: bold; color: #fff; margin-bottom: 14px; background: transparent;")
        features_layout.addWidget(features_title)
        self.keyword_sound_panel = KeywordSoundGroupPanel(self)
        features_layout.addWidget(self.keyword_sound_panel)
        # --- YASAKLI KELİME PANELİ ---
        yasakli_title = QtWidgets.QLabel("Yasaklı Kelime")
        yasakli_title.setAlignment(QtCore.Qt.AlignLeft)
        yasakli_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #e74c3c; margin-top: 18px; margin-bottom: 6px;")
        features_layout.addWidget(yasakli_title)
        self.yasakli_input = QLineEdit()
        self.yasakli_input.setPlaceholderText("Yasaklı kelime ekle...")
        # Enter tuşu ile ekleme özelliği
        self.yasakli_input.returnPressed.connect(self.add_yasakli_kelime)
        self.yasakli_ekle_btn = QPushButton("Ekle")
        self.yasakli_ekle_btn.setStyleSheet("background:#e74c3c;color:#fff;font-weight:bold;border-radius:8px;padding:6px 18px;")
        self.yasakli_ekle_btn.clicked.connect(self.add_yasakli_kelime)
        yasakli_hbox = QHBoxLayout()
        yasakli_hbox.addWidget(self.yasakli_input)
        yasakli_hbox.addWidget(self.yasakli_ekle_btn)
        features_layout.addLayout(yasakli_hbox)
        self.yasakli_list = QListWidget()
        self.yasakli_list.setStyleSheet("background:#23243a;color:#fff;border:1px solid #e74c3c;border-radius:7px;font-size:16px;")
        features_layout.addWidget(self.yasakli_list)
        self.yasakli_sil_btn = QPushButton("Seçiliyi Sil")
        self.yasakli_sil_btn.setStyleSheet("background:#c0392b;color:#fff;font-weight:bold;border-radius:8px;padding:6px 18px;")
        self.yasakli_sil_btn.clicked.connect(self.remove_selected_yasakli)
        features_layout.addWidget(self.yasakli_sil_btn)
        features_layout.addStretch(1)
        self.tab_widget.addTab(features_tab, "Özellikler")
        main_layout.addWidget(self.tab_widget)
        # Yasaklı kelimeleri yükle
        self.load_yasakli_kelime()
    def edit_platforms(self):
        dialog = PlatformEditDialog(self, self.platform_selectors)
        if dialog.exec_():
            new_platforms = dialog.get_platforms()
            self.platform_selectors = new_platforms
            self.settings.set_platforms(new_platforms)
            self.platform_combo.clear()
            self.platform_combo.addItems(list(self.platform_selectors.keys()))
            self.on_platform_change(self.platform_combo.currentText())
    def set_status(self, text, color):
        # Selenium InvalidSessionIdException gibi uzun hata mesajlarını kısalt
        if "invalidsessionidexception" in text.lower() or "message: invalid" in text.lower() or "stacktrace" in text.lower():
            text = "Tarayıcı kapatıldı veya bağlantı koptu."
        # Hata ile başlayan status mesajlarını arayüzde gösterme (terminalde gösterilmeye devam)
        if text.strip().lower().startswith("hata:"):
            return
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"background: {color}; color: #fff; border-radius: 10px; padding: 8px 0; font-size: 22px;")
        # Yayın durumu güncelle
        prev_offline = getattr(self, '_is_stream_offline', False)
        if any(kw in text.lower() for kw in ["beklemede", "kapalı", "sona erdi", "yayıncı geliyor", "durduruldu"]):
            self._is_stream_offline = True
        elif "bağlandı" in text.lower() or "hazır" in text.lower() or "chat başlatıldı" in text.lower():
            self._is_stream_offline = False
            if prev_offline:
                self._last_message_time = time.time()
    def show_toast(self, text, color):
        # Selenium InvalidSessionIdException gibi uzun hata mesajlarını kısalt
        if "invalidsessionidexception" in text.lower() or "message: invalid" in text.lower() or "stacktrace" in text.lower():
            text = "Tarayıcı kapatıldı veya bağlantı koptu."
        # Hata ile başlayan toast mesajlarını arayüzde gösterme (terminalde gösterilmeye devam)
        if text.strip().lower().startswith("hata:"):
            return
        if self.toast_widget:
            self.toast_widget.close()
        self.toast_widget = Toast(self, text, color)
        self.toast_widget.show()
    def load_settings(self):
        self.link_input.setText(self.settings.data.get("last_link", ""))
        self.selector_input.setText(self.settings.data.get("last_selector", ""))
        self.platform_combo.setCurrentText(self.settings.data.get("last_platform", "YouTube"))
        self.platform_icon.setText(PLATFORM_ICONS.get(self.platform_combo.currentText(), ""))
    def save_settings(self):
        # Eğer link_input boşsa, eski last_link'i koru
        current_link = self.link_input.text().strip()
        if current_link:
            self.settings.data["last_link"] = current_link
        # Diğer ayarları her durumda güncelle
        self.settings.data["last_selector"] = self.selector_input.text()
        self.settings.data["last_platform"] = self.platform_combo.currentText()
        self.settings.save()
    def on_platform_change(self, platform):
        selector = self.platform_selectors.get(platform, "")
        # Eğer selector dict ise 'chat' anahtarını al
        if isinstance(selector, dict):
            selector = selector.get("chat", "")
        self.selector_input.setText(selector)
        self.platform_icon.setText(PLATFORM_ICONS.get(platform, ""))
        self.save_settings()
    def start_fetch(self):
        self.save_settings()
        try:
            link = self.link_input.text().strip()
            selector = self.selector_input.text().strip()
            platform = self.platform_combo.currentText()
            if not link or not selector:
                self.show_toast("Chat linki ve selector boş olamaz!", "#e74c3c")
                return
            if hasattr(self, 'chat_fetcher') and self.chat_fetcher and self.chat_fetcher.isRunning():
                return
            if hasattr(self, 'chat_fetcher') and (not self.chat_fetcher or self.chat_fetcher.isFinished()):
                print('[MainWindow] ChatFetcher thread sonlanmış, yeni başlatılıyor')
            if hasattr(self, 'chat_fetcher') and self.chat_fetcher and not self.chat_fetcher.isFinished():
                self.show_toast("Önce mevcut chat işlemini durdurun!", "#f39c12")
                return
            self._last_message_time = None
            max_wait = self.settings.data.get("max_wait_minutes", 5)
            retry_interval = self.settings.data.get("retry_interval", 30)
            status_retry_interval = self.settings.data.get("status_retry_interval", retry_interval)
            # Flask sunucu thread'i başlat (sadece bir kez)
            if not hasattr(self, 'flask_thread') or self.flask_thread is None:
                self.flask_thread = FlaskServerThread(port=5001)
                self.flask_thread.start()
                print('[MainWindow] Flask sunucu thread başlatıldı')
            self.chat_fetcher = ChatFetcher(link, selector, max_wait, retry_interval, platform=self.platform_combo.currentText())
            self.chat_fetcher.status_retry_interval = status_retry_interval
            self.chat_fetcher.new_message.connect(self.add_message)
            self.chat_fetcher.status_update.connect(self.set_status)
            self.chat_fetcher.finished.connect(self.on_fetcher_finished)
            self.chat_fetcher.start()
            self.set_status("Bağlandı", "#2ecc71")
            self.show_toast("Chat başlatıldı! (Tampermonkey)", "#27ae60")
            self.start_btn.setEnabled(True)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.show_toast(f"Hata: {str(e)}", "#e74c3c")
            self.start_btn.setEnabled(True)
            print(tb)

    def stop_fetch(self):
        if hasattr(self, 'chat_fetcher') and self.chat_fetcher:
            try:
                if self.chat_fetcher.isRunning():
                    self.chat_fetcher.stop()
                    self.set_status("Durduruldu", "#e67e22")
                    self.show_toast("Chat durduruldu!", "#e67e22")
                else:
                    self.set_status("Durduruldu", "#e67e22")
                    self.show_toast("Chat zaten durduruldu!", "#f39c12")
            except Exception as e:
                self.set_status("Durduruldu (Hata)", "#e74c3c")
                self.show_toast(f"Durdurma hatası: {str(e)}", "#e74c3c")
        else:
            self.set_status("Durduruldu", "#e67e22")
            self.show_toast("Chat zaten durduruldu!", "#f39c12")
        self.start_btn.setEnabled(True)

    def on_fetcher_finished(self):
        self.set_status("Durduruldu", "#e67e22")
        self.show_toast("Chat durduruldu!", "#e67e22")
        self.start_btn.setEnabled(True)

    def normalize(self, text):
        table = str.maketrans({
            'ş': 's', 'Ş': 's',
            'ı': 'i', 'I': 'i',
            'ç': 'c', 'Ç': 'c',
            'ö': 'o', 'Ö': 'o',
            'ü': 'u', 'Ü': 'u',
            'ğ': 'g', 'Ğ': 'g',
        })
        return text.translate(table).lower()

    def _find_matched_groups(self, message):
        """
        Mesajı anahtar kelime gruplarıyla eşleştirir.
        Anahtar kelime kutusunda virgül varsa: tüm kelimeler mesajda geçiyorsa eşleşir.
        Boşluk varsa: tüm kelimeler sıralı olarak geçiyorsa eşleşir.
        Tek kelime varsa: klasik şekilde herhangi biri geçiyorsa eşleşir.
        Returns:
            list[tuple[dict, str]]: A list of tuples, where each tuple contains
                                     the matched group and the specific keyword
                                     entry that caused the match (e.g., "helo,love" or "sent a").
        """
        matched = []
        normalized_message = self.normalize(message)
        message_words = normalized_message.split()

        for group in self.keyword_sound_panel.get_groups():
            keywords_raw = group.get('words', [])
            if not keywords_raw:
                continue

            for kw_entry in keywords_raw:  # e.g., kw_entry = "helo,love" or "sent a"
                # Normalize the entry
                normalized_entry = self.normalize(kw_entry.strip())
                
                if not normalized_entry:
                    continue

                # Check if entry contains comma (multiple separate keywords)
                if ',' in normalized_entry:
                    # Split by comma and check each keyword separately
                    keywords = [kw.strip() for kw in normalized_entry.split(',') if kw.strip()]
                    
                    if not keywords:
                        continue

                    # Check if all keywords from the entry are present in the message
                    all_found = True
                    for kw in keywords:  # e.g., kw = "helo"
                        # A keyword is considered "found" if it's a substring of any word in the message
                        if ' ' in kw:
                            # If keyword part contains a space, check against the whole message
                            is_found = kw in normalized_message
                        else:
                            # Otherwise, check within individual words
                            is_found = any(kw in word for word in message_words)

                        if not is_found:
                            all_found = False
                            break  # No need to check other kws for this entry
                    
                    if all_found:
                        matched.append((group, kw_entry))
                        # This group has matched with one of its entries,
                        # move to the next group
                        break
                
                # Check if entry contains space (phrase to be found in order)
                elif ' ' in normalized_entry:
                    # Check if the entire phrase exists in the message
                    if normalized_entry in normalized_message:
                        matched.append((group, kw_entry))
                        # This group has matched with one of its entries,
                        # move to the next group
                        break
                
                # Single word
                else:
                    # A single keyword is considered "found" if it's a substring of any word in the message
                    is_found = any(normalized_entry in word for word in message_words)
                    if is_found:
                        matched.append((group, kw_entry))
                        # This group has matched with one of its entries,
                        # move to the next group
                        break
        return matched

    def _is_yasakli_kelime_match(self, yasakli_kelime, normalized_message, message_words):
        """
        Yasaklı kelimeler için tam kelime eşleşmesi.
        Örnek: "x1" varsa sadece "x1" kelimesini yakalar, "x10" kelimesini yakalamaz.
        """
        # Yasaklı kelimeyi normalize et
        normalized_yasakli = self.normalize(yasakli_kelime)
        
        # Mesajı kelimelere böl
        msg_words = normalized_message.split()
        
        # Yasaklı kelimeyi kelimeler arasında ara
        for word in msg_words:
            if word == normalized_yasakli:
                return True
        
        return False

    def add_message(self, msg, msg_id=None):
        # Mesaj ID'si oluştur
        if msg_id is None:
            msg_id = f"{msg}:{time.time()}"

        # Son mesaj zamanını güncelle
        self._last_message_time = time.time()

        print(f'[add_message] Yeni mesaj: {msg}')
        
        # Tekrarlanan mesaj kontrolü
        if not hasattr(self, '_processed_messages'):
            self._processed_messages = set()
        
        # Mesaj ID'si daha önce işlendiyse atla
        if msg_id in self._processed_messages:
            print(f'[add_message] Tekrarlanan mesaj atlandı: {msg}')
            return
        
        # Mesajı işlenmiş olarak işaretle
        self._processed_messages.add(msg_id)
        
        # Bellek sınırı (son 100 mesaj)
        if len(self._processed_messages) > 100:
            self._processed_messages = set(list(self._processed_messages)[-100:])

        # Yasaklı kelime kontrolü (anahtar kelime grubu mantığıyla)
        yasakli_kelimeler = [self.yasakli_list.item(i).text() for i in range(self.yasakli_list.count())]
        normalized_msg = self.normalize(msg)
        message_words = normalized_msg.split()
        yasakli_bulundu = False
        yasakli_vurgulu = msg
        import re
        for kelime in yasakli_kelimeler:
            if not kelime:
                continue
            # Virgül varsa: tüm alt kelimeler mesajda geçiyorsa engelle
            if ',' in kelime:
                alt_kelimeler = [k.strip() for k in kelime.split(',') if k.strip()]
                if all(self._is_yasakli_kelime_match(k, normalized_msg, message_words) for k in alt_kelimeler):
                    yasakli_bulundu = True
                    for k in alt_kelimeler:
                        pattern = re.compile(re.escape(k), re.IGNORECASE)
                        yasakli_vurgulu = pattern.sub(lambda m: f'<span style="color:#fff;background:#e74c3c;border-radius:7px;padding:2px 7px;">{m.group(0)}</span>', yasakli_vurgulu)
            # Boşluk varsa: tüm kelimeler sıralı olarak geçiyorsa engelle
            elif ' ' in kelime:
                if kelime in normalized_msg:
                    yasakli_bulundu = True
                    pattern = re.compile(re.escape(kelime), re.IGNORECASE)
                    yasakli_vurgulu = pattern.sub(lambda m: f'<span style="color:#fff;background:#e74c3c;border-radius:7px;padding:2px 7px;">{m.group(0)}</span>', yasakli_vurgulu)
            # Tek kelime: tam kelime eşleşmesi yap
            else:
                if self._is_yasakli_kelime_match(kelime, normalized_msg, message_words):
                    yasakli_bulundu = True
                    pattern = re.compile(re.escape(kelime), re.IGNORECASE)
                    yasakli_vurgulu = pattern.sub(lambda m: f'<span style="color:#fff;background:#e74c3c;border-radius:7px;padding:2px 7px;">{m.group(0)}</span>', yasakli_vurgulu)
        if yasakli_bulundu:
            balloon = f"<div style='background:linear-gradient(90deg,#31344b,#23243a);color:#fff;padding:10px 18px;border-radius:15px;margin:6px 0;font-size:20px;font-family:Montserrat,Segoe UI,Arial,sans-serif;font-weight:600;box-shadow:0 2px 8px rgba(0,0,0,0.13);'>{yasakli_vurgulu}</div>"
            self.messages.append(balloon)
            self.chat_box.setHtml('<br>'.join(self.messages))
            self.chat_box.moveCursor(QtGui.QTextCursor.End)
            return
        # Yasaklı kelime yoksa, sadece gerçekten ses çalınan anahtar kelimeler mavi vurgulansın
        highlighted = msg
        matched_entries = self._find_matched_groups(msg)
        if not matched_entries:
            balloon = f"<div style='background:linear-gradient(90deg,#31344b,#23243a);color:#fff;padding:10px 18px;border-radius:15px;margin:6px 0;font-size:20px;font-family:Montserrat,Segoe UI,Arial,sans-serif;font-weight:600;box-shadow:0 2px 8px rgba(0,0,0,0.13);'>{highlighted}</div>"
            self.messages.append(balloon)
            self.chat_box.setHtml('<br>'.join(self.messages))
            self.chat_box.moveCursor(QtGui.QTextCursor.End)
            return
        # ---- Ses Çalma Mantığı ----
        sound_groups_to_play = []
        current_time = time.time()
        cooldown_time = self.settings.data.get('spam_prevention_time', 5)
        if not hasattr(self, 'keyword_last_triggered'):
            self.keyword_last_triggered = {}
        played_keywords = set()
        for group, kw_entry in matched_entries:
            group_id = tuple(sorted(group.get('words', [])))
            last_triggered_group = self.keyword_last_triggered.get(group_id, 0)
            if cooldown_time > 0 and current_time - last_triggered_group < cooldown_time:
                continue
            self.keyword_last_triggered[group_id] = current_time
            sound_groups_to_play.append(group)
            played_keywords.update([kw.strip() for kw in kw_entry.split(',')])
        sound_paths = []
        for group in sound_groups_to_play:
            sounds = group.get('sounds', [])
            if not sounds:
                continue
            group_id = tuple(sorted(group.get('words', [])))
            if group_id not in self.group_sound_queues or not self.group_sound_queues[group_id]:
                import random
                self.group_sound_queues[group_id] = sounds.copy()
                random.shuffle(self.group_sound_queues[group_id])
                last = self.group_last_sound.get(group_id)
                if last and len(self.group_sound_queues[group_id]) > 1 and self.group_sound_queues[group_id][0] == last:
                    self.group_sound_queues[group_id].append(self.group_sound_queues[group_id].pop(0))
            chosen_sound = self.group_sound_queues[group_id].pop(0)
            sound_paths.append(chosen_sound)
            self.group_last_sound[group_id] = chosen_sound
        if sound_paths:
            self.play_sound_queued(sound_paths[0])
        for keyword in played_keywords:
            if not keyword: continue
            try:
                pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                highlighted = pattern.sub(lambda m: f'<span style="background:#3086f0;color:#fff;border-radius:7px;padding:2px 7px;">{m.group(0)}</span>', highlighted)
            except re.error:
                pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                highlighted = pattern.sub(lambda m: f'<span style="background:#3086f0;color:#fff;border-radius:7px;padding:2px 7px;">{m.group(0)}</span>', highlighted)
        balloon = f"<div style='background:linear-gradient(90deg,#31344b,#23243a);color:#fff;padding:10px 18px;border-radius:15px;margin:6px 0;font-size:20px;font-family:Montserrat,Segoe UI,Arial,sans-serif;font-weight:600;box-shadow:0 2px 8px rgba(0,0,0,0.13);'>{highlighted}</div>"
        self.messages.append(balloon)
        self.chat_box.setHtml('<br>'.join(self.messages))
        self.chat_box.moveCursor(QtGui.QTextCursor.End)

    def closeEvent(self, event):
        try:
            self.sound_thread.stop()
            self.sound_thread.wait()
        except Exception as e:
            print(f'[MainWindow] SoundPlayerThread durdurulamadı: {e}')
        self.stop_fetch()
        self.save_settings()
        event.accept()

    def add_yasakli_kelime(self):
        kelime = self.yasakli_input.text().strip()
        if kelime:
            for i in range(self.yasakli_list.count()):
                if self.yasakli_list.item(i).text().lower() == kelime.lower():
                    return
            self.yasakli_list.addItem(kelime)
            self.save_yasakli_kelime()
            self.yasakli_input.clear()

    def remove_selected_yasakli(self):
        for item in self.yasakli_list.selectedItems():
            self.yasakli_list.takeItem(self.yasakli_list.row(item))
        self.save_yasakli_kelime()

    def save_yasakli_kelime(self):
        kelimeler = [self.yasakli_list.item(i).text() for i in range(self.yasakli_list.count())]
        self.settings.data['yasakli_kelime'] = kelimeler
        self.settings.save()

    def load_yasakli_kelime(self):
        kelimeler = self.settings.data.get('yasakli_kelime', [])
        self.yasakli_list.clear()
        for k in kelimeler:
            self.yasakli_list.addItem(k)

    def refresh_sound_queues(self):
        """
        Tüm anahtar kelime grupları için RAM'deki ses kuyruklarını ve son çalınan ses bilgisini sıfırlar.
        Böylece ayarlarda yapılan değişiklikler (ses silme/ekleme) anında geçerli olur.
        """
        self.group_sound_queues = {}
        self.group_last_sound = {}

# --- LOG TEMİZLİĞİ: Haftada bir log dosyasını sil ---
def weekly_log_cleanup(log_path='uygulama.log', meta_path='.logmeta', days=7):
    try:
        now = time.time()
        last_clean = 0
        if os.path.exists(meta_path):
            with open(meta_path, 'r') as f:
                try:
                    last_clean = float(f.read().strip())
                except:
                    last_clean = 0
        if not os.path.exists(log_path):
            # Log dosyası yoksa sadece meta güncelle
            with open(meta_path, 'w') as f:
                f.write(str(now))
            return
        if now - last_clean > days * 86400:
            try:
                os.remove(log_path)
                print(f'[LOG TEMİZLİK] {log_path} dosyası silindi (haftalık temizlik).')
            except Exception as e:
                print(f'[LOG TEMİZLİK] {log_path} silinemedi: {e}')
            with open(meta_path, 'w') as f:
                f.write(str(now))
    except Exception as e:
        print(f'[LOG TEMİZLİK] Temizlik kontrolünde hata: {e}')

# Uygulama başlatılırken çağır
weekly_log_cleanup()

def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
