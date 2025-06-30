from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QLineEdit, QFileDialog, QListWidget, QListWidgetItem, QMenu, QScrollArea
)
from PyQt5.QtCore import Qt
import os

class KeywordSoundGroupPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.groups = []  # Her grup: {"words": [...], "sounds": [...]}  
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        self.setMinimumHeight(320)
        # Modern koyu tema ve beyaz yazı
        self.setStyleSheet('''
            QWidget { background: #23243a; color: #fff; }
            QLabel { color: #fff; font-size: 16px; }
            QLineEdit { background: #23243a; color: #fff; border: 1px solid #3086f0; border-radius: 7px; font-size: 16px; padding: 6px; }
            QLineEdit:focus { border: 1.5px solid #4e9fff; }
            QPushButton { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4e9fff, stop:1 #3086f0); color: #fff; font-size: 15px; font-family: 'Segoe UI', 'Arial', sans-serif; font-weight: bold; border: none; border-radius: 12px; padding: 8px 0; min-width: 90px; min-height: 32px; }
            QPushButton:hover { background: #5baaff; }
            QListWidget { background: #23243a; color: #fff; border: 1px solid #3086f0; border-radius: 7px; font-size: 16px; }
            QScrollBar:vertical {
                background: #23243a;
                width: 18px;
                margin: 2px;
                border-radius: 8px;
            }
            QScrollBar::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4e9fff, stop:1 #3086f0);
                min-height: 32px;
                border-radius: 8px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: #31344b;
                height: 18px;
                border-radius: 8px;
            }
            QScrollBar::add-line:vertical:hover, QScrollBar::sub-line:vertical:hover {
                background: #4e9fff;
            }
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {
                width: 12px;
                height: 12px;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        ''')
        self.add_group_btn = QPushButton("+ Grup Ekle")
        self.add_group_btn.clicked.connect(self.add_group)
        self.group_widgets = []

        # SCROLLABLE ALAN
        from PyQt5.QtWidgets import QSizePolicy
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.scroll_area.setMinimumHeight(250)
        self.scroll_content = QWidget()
        self.scroll_content.setMinimumHeight(220)
        self.scroll_content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(8, 8, 8, 8)
        self.scroll_layout.setSpacing(10)
        self.scroll_content.setLayout(self.scroll_layout)
        self.scroll_area.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll_area)
        from PyQt5.QtWidgets import QSizePolicy
        self.add_group_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.layout.insertWidget(0, self.add_group_btn)
        self.scroll_layout.addStretch()

    def add_group(self, group=None):
        print('Grup ekleniyor:', group)
        print(f'[DEBUG] add_group çağrıldı: {group}')
        group = group or {"words": [], "sounds": []}
        self.groups.append(group)  # önce ana grup listesine ekle
        group_widget = KeywordSoundGroupWidget(group, self)
        # Silme callback'i ayarla
        def on_delete():
            if group_widget in self.group_widgets:
                self.group_widgets.remove(group_widget)
            if group in self.groups:
                self.groups.remove(group)
            group_widget.setParent(None)
            self.save_groups_to_settings()
        group_widget.on_delete = on_delete
        group_widget.del_btn.clicked.disconnect()
        group_widget.del_btn.clicked.connect(on_delete)
        # Grup widget'ını ekle
        self.scroll_layout.addWidget(group_widget)
        self.group_widgets.append(group_widget)
        # Sadece kullanıcı manuel olarak grup eklerse kaydet
        if group is None:
            self.save_groups_to_settings()


    def delete_group(self, group_widget):
        idx = self.group_widgets.index(group_widget)
        self.scroll_layout.removeWidget(group_widget)
        group_widget.deleteLater()
        del self.group_widgets[idx]
        del self.groups[idx]
        self.save_groups_to_settings()

    def get_groups(self):
        # Tüm grupları döndür (kelime ve ses dosyalarının tam yolu ile!)
        return [
            {
                "words": gw.group.get("words", []),
                "sounds": gw.group.get("sounds", [])
            } for gw in self.group_widgets
        ]

    def save_groups_to_settings(self):
        print('[DEBUG] save_groups_to_settings çağrıldı. Parent zinciri:')
        mainwin = self.parent()
        while mainwin:
            print('  parent:', type(mainwin))
            if hasattr(mainwin, 'settings'):
                print('  [DEBUG] MainWindow bulundu!')
                break
            mainwin = mainwin.parent()
        if mainwin and hasattr(mainwin, 'settings'):
            mainwin.settings.data['groups'] = self.get_groups()
            mainwin.settings.save()
            print('[KeywordSoundGroupPanel] Gruplar kaydedildi:', self.get_groups())
            if hasattr(mainwin, 'refresh_sound_queues'):
                mainwin.refresh_sound_queues()  # Ses kuyruklarını ve son sesleri sıfırla
        else:
            print('[HATA] MainWindow parent zincirinde bulunamadı, ayarlar kaydedilemedi!')

    def load_groups_from_settings(self, groups):
        print(f'[KeywordSoundGroupPanel] Gruplar yüklendi: {groups}')
        # Önce arayüzü ve listeleri temizle
        for gw in getattr(self, 'group_widgets', []):
            gw.setParent(None)
        self.group_widgets = []
        self.groups = []
        self.group_widgets = []
        self.groups = []
        for group in groups or []:
            self.add_group(group)
        print('[KeywordSoundGroupPanel] Gruplar yüklendi:', groups)

class KeywordSoundGroupWidget(QWidget):
    def __init__(self, group, parent=None):
        super().__init__(parent)
        self.group = group
        self.on_delete = None
        from PyQt5.QtWidgets import QSizePolicy
        self.layout = QHBoxLayout()
        self.layout.setSpacing(4)
        self.layout.setContentsMargins(2, 2, 2, 2)
        self.layout.setSizeConstraint(self.layout.SetMinimumSize)
        self.setLayout(self.layout)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # --- Sol: Yukarı Taşıma Butonu (küçük, dikey) ---
        from PyQt5.QtWidgets import QPushButton, QVBoxLayout
        btn_col = QVBoxLayout()
        btn_col.setSpacing(2)
        self.up_btn = QPushButton('▲')
        self.up_btn.setFixedSize(22, 22)
        self.up_btn.setStyleSheet('font-size:13px; font-weight:bold; padding:0; color:#3086f0;')
        btn_col.addWidget(self.up_btn)
        btn_col.addStretch()
        self.up_btn.clicked.connect(self.move_up)
        self.layout.addLayout(btn_col)

        # Grup içi kelime ekleme
        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText("Kelime ekle...")
        self.word_input.returnPressed.connect(self.add_word)
        self.layout.addWidget(QLabel("Kelimeler:"))
        self.layout.addWidget(self.word_input)
        self.word_list = QListWidget()
        self.word_list.setMinimumHeight(80)
        self.word_list.setMaximumHeight(160)
        self.layout.addWidget(self.word_list)
        # Grup içi ses ekleme
        self.sound_btn = QPushButton("Ses Ekle")
        self.sound_btn.setMinimumHeight(28)
        self.sound_btn.setMaximumHeight(32)
        self.sound_btn.clicked.connect(lambda: self.add_sound())
        self.layout.addWidget(QLabel("Sesler:"))
        self.layout.addWidget(self.sound_btn)
        self.sound_list = QListWidget()
        self.sound_list.setMinimumHeight(80)
        self.sound_list.setMaximumHeight(160)
        self.layout.addWidget(self.sound_list)
        # Grup silme
        self.del_btn = QPushButton("Grubu Sil")
        self.del_btn.setMinimumHeight(28)
        self.del_btn.setMaximumHeight(32)
        self.del_btn.clicked.connect(self.delete_group)
        self.layout.addWidget(self.del_btn)
        # Başlangıç değerleri (sadece grup içi kelime ve sesler)
        print(f'[DEBUG] Grup içi kelimeler: {group.get("words", [])}')
        for word in self.group["words"]:
            self.word_list.addItem(word)
        print(f'[DEBUG] group widget kelime ekleme sonrası, word_list count: {self.word_list.count()}, visible: {self.word_list.isVisible()}')
        for s in group.get("sounds", []):
            self.sound_list.addItem(os.path.basename(s))
        self.word_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.word_list.customContextMenuRequested.connect(self.word_context_menu)
        self.sound_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.sound_list.customContextMenuRequested.connect(self.sound_context_menu)

    def move_up(self):
        panel = self.parentWidget()
        while panel and not hasattr(panel, 'group_widgets'):
            panel = panel.parentWidget()
        if panel:
            idx = panel.group_widgets.index(self)
            if idx > 0:
                # Listelerde yer değiştir
                panel.group_widgets[idx], panel.group_widgets[idx-1] = panel.group_widgets[idx-1], panel.group_widgets[idx]
                panel.groups[idx], panel.groups[idx-1] = panel.groups[idx-1], panel.groups[idx]
                # Önce tüm grup widget'larını scroll_layout'tan çıkar
                for gw in panel.group_widgets:
                    panel.scroll_layout.removeWidget(gw)
                # Sonra sırayla tekrar ekle (sadece grup widget'ları)
                for i, gw in enumerate(panel.group_widgets):
                    panel.scroll_layout.insertWidget(i, gw)
                panel.save_groups_to_settings()

    def add_word(self, word=None, save=True):
        print(f'[DEBUG] add_word çağrıldı: word={word}, save={save}')
        if word is None:
            word = self.word_input.text().strip()
        if word is None or word == "":
            print("[HATA] add_word: word parametresi boş!")
            return
        if word and word not in self.group["words"]:
            self.group["words"].append(word)
            self.word_list.addItem(word)
            print(f'[KeywordSoundGroupWidget] Anahtar kelime eklendi: {word}')
            print('[DEBUG] word_list item count:', self.word_list.count())
            print('[DEBUG] word_list parent:', self.word_list.parent())
            print('[DEBUG] word_list geometry:', self.word_list.geometry())
            print('[DEBUG] word_list isVisible:', self.word_list.isVisible())
            self.word_list.repaint()
            self.word_list.update()
            # KAYDET
            if save:
                panel = self.parentWidget()
                print(f'[DEBUG] parentWidget: {type(panel)}')
                # Zincir ile doğru paneli bul
                while panel and not hasattr(panel, 'save_groups_to_settings'):
                    panel = panel.parentWidget()
                if panel and hasattr(panel, 'save_groups_to_settings'):
                    panel.save_groups_to_settings()
                else:
                    print('[HATA] save_groups_to_settings fonksiyonu parent zincirinde bulunamadı!')
        self.word_input.clear()

    def word_context_menu(self, pos):
        item = self.word_list.itemAt(pos)
        if item:
            menu = QMenu()
            delete_action = menu.addAction("Sil")
            action = menu.exec_(self.word_list.mapToGlobal(pos))
            if action == delete_action:
                word = item.text()
                self.group["words"].remove(word)
                self.word_list.takeItem(self.word_list.row(item))
                print(f'[KeywordSoundGroupWidget] Anahtar kelime silindi: {word}')
                # KAYDET
                panel = self.parentWidget()
                while panel and not hasattr(panel, 'save_groups_to_settings'):
                    panel = panel.parentWidget()
                if panel and hasattr(panel, 'save_groups_to_settings'):
                    panel.save_groups_to_settings()
                else:
                    print('[HATA] save_groups_to_settings fonksiyonu parent zincirinde bulunamadı!')

    def add_sound(self, sound=None, save=True):
        # Çoklu dosya seçimi desteği
        if sound is None:
            files, _ = QFileDialog.getOpenFileNames(self, "Ses Dosyası Seç", os.getcwd(), "Ses Dosyaları (*.wav *.mp3)")
            if not files:
                return
            sounds_to_add = files
        else:
            sounds_to_add = [sound]
        for s in sounds_to_add:
            if s and s not in self.group["sounds"]:
                self.group["sounds"].append(s)
                self.sound_list.addItem(os.path.basename(s))
                print(f'[KeywordSoundGroupWidget] Ses eklendi: {s}')
        # KAYDET
        if save and sounds_to_add:
            panel = self.parentWidget()
            while panel and not hasattr(panel, 'save_groups_to_settings'):
                panel = panel.parentWidget()
            if panel and hasattr(panel, 'save_groups_to_settings'):
                panel.save_groups_to_settings()
            else:
                print('[HATA] save_groups_to_settings fonksiyonu parent zincirinde bulunamadı!')


    def sound_context_menu(self, pos):
        item = self.sound_list.itemAt(pos)
        if item:
            menu = QMenu()
            delete_action = menu.addAction("Sil")
            action = menu.exec_(self.sound_list.mapToGlobal(pos))
            if action == delete_action:
                idx = self.sound_list.row(item)
                removed = self.group["sounds"][idx]
                del self.group["sounds"][idx]
                self.sound_list.takeItem(idx)
                print(f'[KeywordSoundGroupWidget] Ses silindi: {removed}')
                # KAYDET
                panel = self.parentWidget()
                while panel and not hasattr(panel, 'save_groups_to_settings'):
                    panel = panel.parentWidget()
                if panel and hasattr(panel, 'save_groups_to_settings'):
                    panel.save_groups_to_settings()
                else:
                    print('[HATA] save_groups_to_settings fonksiyonu parent zincirinde bulunamadı!')

    def delete_group(self):
        if self.on_delete:
            self.on_delete()

    def get_group(self):
        return dict(words=list(self.group["words"]), sounds=list(self.group["sounds"]))
