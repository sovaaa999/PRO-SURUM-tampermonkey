from PyQt5 import QtWidgets

class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent, status_retry_interval, platforms=None):
        super().__init__(parent)
        self.setWindowTitle("Ayarlar")
        self.setModal(True)
        self.resize(420, 350)
        self.status_retry_interval = status_retry_interval
        # Platformları normalize et: string ise dict'e çevir
        self.platforms = {}
        for plat, val in (platforms or {}).items():
            if isinstance(val, str):
                self.platforms[plat] = {"chat": val, "status": []}
            else:
                self.platforms[plat] = val

        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()

        # Yayın durumu deneme aralığı
        self.status_retry_spin = QtWidgets.QSpinBox()
        self.status_retry_spin.setRange(1, 3600)
        self.status_retry_spin.setMinimum(1)
        self.status_retry_spin.setValue(self.status_retry_interval)
        self.status_retry_spin.setSuffix(" saniye")
        form.addRow("Yayın durumu deneme aralığı:", self.status_retry_spin)

        # Mesaj deneme aralığı
        self.message_retry_spin = QtWidgets.QSpinBox()
        self.message_retry_spin.setRange(1, 3600)
        self.message_retry_spin.setMinimum(1)
        self.message_retry_spin.setValue(parent.settings.data.get("message_retry_interval", 30))
        self.message_retry_spin.setSuffix(" saniye")
        form.addRow("Mesaj deneme aralığı:", self.message_retry_spin)

        # Spam önleme süresi
        self.spam_prevention_spin = QtWidgets.QSpinBox()
        self.spam_prevention_spin.setRange(0, 360)  # 0 = bekleme yok, her seferinde ses çal
        self.spam_prevention_spin.setMinimum(0)
        self.spam_prevention_spin.setValue(parent.settings.data.get("spam_prevention_time", 5))
        self.spam_prevention_spin.setSuffix(" saniye")
        form.addRow("Aynı kelime için bekleme süresi (0 = bekleme yok):", self.spam_prevention_spin)

        layout.addLayout(form)

        # Platform seçimi ve ayarları
        plat_layout = QtWidgets.QHBoxLayout()
        self.platform_combo = QtWidgets.QComboBox()
        self.platform_combo.addItems(list(self.platforms.keys()))
        self.platform_combo.currentTextChanged.connect(self.load_platform_settings)
        plat_layout.addWidget(QtWidgets.QLabel("Platform:"))
        plat_layout.addWidget(self.platform_combo)
        layout.addLayout(plat_layout)

        self.chat_selector_edit = QtWidgets.QLineEdit()
        layout.addWidget(QtWidgets.QLabel("Chat Selector:"))
        layout.addWidget(self.chat_selector_edit)

        # Yayın durumu selector listesi
        self.status_list = QtWidgets.QListWidget()
        layout.addWidget(QtWidgets.QLabel("Yayın Durumu Selector(ları):"))
        layout.addWidget(self.status_list)

        btns = QtWidgets.QHBoxLayout()
        self.add_status_btn = QtWidgets.QPushButton("Ekle")
        self.remove_status_btn = QtWidgets.QPushButton("Sil")
        btns.addWidget(self.add_status_btn)
        btns.addWidget(self.remove_status_btn)
        layout.addLayout(btns)

        self.add_status_btn.clicked.connect(self.add_status_selector)
        self.remove_status_btn.clicked.connect(self.remove_status_selector)

        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

        if not self.platforms or len(self.platforms) == 0:
            QtWidgets.QMessageBox.warning(self, "Hata", "Hiç platform tanımlı değil! Lütfen platform ayarlarını kontrol edin.")
            self.close()
            return
        if self.platform_combo.count() == 0:
            QtWidgets.QMessageBox.warning(self, "Hata", "Hiç platform seçeneği yok! Lütfen platform ayarlarını kontrol edin.")
            self.close()
            return

        self.load_platform_settings(self.platform_combo.currentText())

    def load_platform_settings(self, platform):
        if not platform or platform not in self.platforms:
            self.chat_selector_edit.setText("")
            self.status_list.clear()
            return
        plat_info = self.platforms.get(platform, {})
        self.chat_selector_edit.setText(plat_info.get("chat", ""))
        self.status_list.clear()
        for sel in plat_info.get("status", []):
            if sel.get("type") == "css":
                self.status_list.addItem(f"CSS: {sel['selector']}")
            elif sel.get("type") == "text":
                self.status_list.addItem(f"Metin: {sel['selector']} | {sel['text']}")

    def add_status_selector(self):
        typ, ok = QtWidgets.QInputDialog.getItem(self, "Selector Tipi", "Tip:", ["CSS", "Metin"], 0, False)
        if not ok:
            return
        if typ == "CSS":
            sel, ok2 = QtWidgets.QInputDialog.getText(self, "CSS Selector", "CSS selector girin:")
            if ok2 and sel:
                self.status_list.addItem(f"CSS: {sel}")
        else:
            sel, ok2 = QtWidgets.QInputDialog.getText(self, "Selector", "Hangi öğede aranacak (örn: body, .panel vs):")
            if not ok2 or not sel:
                return
            text, ok3 = QtWidgets.QInputDialog.getText(self, "Metin", "Aranacak metin:")
            if ok3 and text:
                self.status_list.addItem(f"Metin: {sel} | {text}")

    def remove_status_selector(self):
        for item in self.status_list.selectedItems():
            self.status_list.takeItem(self.status_list.row(item))

    def get_status_retry_interval(self):
        return self.status_retry_spin.value()

    def get_message_retry_interval(self):
        return self.message_retry_spin.value()

    def get_spam_prevention_time(self):
        return self.spam_prevention_spin.value()

    def get_platform_settings(self):
        # Tüm platform ayarlarını döndür
        for i in range(self.platform_combo.count()):
            plat = self.platform_combo.itemText(i)
            if plat == self.platform_combo.currentText():
                chat = self.chat_selector_edit.text()
                status = []
                for idx in range(self.status_list.count()):
                    txt = self.status_list.item(idx).text()
                    if txt.startswith("CSS: "):
                        status.append({"type": "css", "selector": txt[5:]})
                    elif txt.startswith("Metin: "):
                        try:
                            sel, metin = txt[7:].split(" | ", 1)
                            status.append({"type": "text", "selector": sel, "text": metin})
                        except Exception:
                            continue
                self.platforms[plat] = {"chat": chat, "status": status}
        return self.platforms
