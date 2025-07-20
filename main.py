import sys
import uuid
import socket
import threading
import numpy as np
import cv2
import qrcode
from io import BytesIO
from flask import Flask, request
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QMessageBox, QLineEdit, QDialog, QDialogButtonBox, QGraphicsOpacityEffect
)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve

# ------------------- GLOBAL STATE -------------------
latest_frame = None
current_token = None

def generate_token():
    global current_token
    current_token = str(uuid.uuid4())
    return current_token

# ------------------- FLASK SERVER -------------------
app = Flask(__name__)

@app.route('/upload', methods=['POST'])
def upload():
    token = request.args.get('token')
    if token != current_token:
        return "Unauthorized", 403

    file = request.files['frame']
    data = np.frombuffer(file.read(), np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)

    global latest_frame
    latest_frame = img
    return "OK", 200

def start_flask():
    app.run(host="0.0.0.0", port=5000)

# ------------------- DIALOG TO SET RECEIVER ID -------------------
class IDDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Receiver ID")
        self.setStyleSheet("background-color: #2b2b2b; color: white;")
        self.setFixedSize(300, 120)

        self.input = QLineEdit()
        self.input.setStyleSheet("background-color: #444; border: none; padding: 8px; border-radius: 6px; color: white;")
        self.input.setPlaceholderText("Enter receiver ID")

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(self.input)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)

    def get_text(self):
        return self.input.text()

# ------------------- MAIN GUI -------------------
class WebcamReceiver(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("CamDroid Receiver")
        self.setObjectName("CamDroidReceiver")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setWindowOpacity(0.95)
        self.setFixedSize(780, 580)
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                border-radius: 12px;
                color: white;
            }
        """)

        self.receiver_id = "Unknown"

        # Title bar
        self.title_bar = QWidget()
        self.title_bar.setFixedHeight(42)
        self.title_bar.setStyleSheet("background-color: #292929; border-top-left-radius: 10px; border-top-right-radius: 10px;")

        self.title_label = QLabel("CamDroid Receiver")
        self.title_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")

        self.minimize_btn = QPushButton("–")
        self.maximize_btn = QPushButton("□")
        self.close_btn = QPushButton("✖")

        for btn in [self.minimize_btn, self.maximize_btn, self.close_btn]:
            btn.setFixedSize(40, 40)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: white;
                    font-size: 16px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #444;
                }
            """)

        self.minimize_btn.clicked.connect(self.showMinimized)
        self.maximize_btn.clicked.connect(self.toggle_max_restore)
        self.close_btn.clicked.connect(self.close)

        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(10, 0, 10, 0)
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        title_layout.addWidget(self.minimize_btn)
        title_layout.addWidget(self.maximize_btn)
        title_layout.addWidget(self.close_btn)
        self.title_bar.setLayout(title_layout)

        # Video Display
        self.image_label = QLabel("Waiting for frames...")
        self.image_label.setFixedSize(640, 480)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: black; border-radius: 8px; color: white;")

        # QR Code
        self.qr_label = QLabel()
        self.qr_label.setFixedSize(200, 200)
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setStyleSheet("background-color: #111; border-radius: 10px;")
        self.qr_label.setVisible(False)

        self.hide_qr_btn = QPushButton("Close QR")
        self.hide_qr_btn.setFixedSize(100, 30)
        self.hide_qr_btn.setVisible(False)
        self.hide_qr_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #505050;
            }
        """)
        self.hide_qr_btn.clicked.connect(self.hide_qr)

        self.qr_area = QWidget()
        qr_layout = QVBoxLayout(self.qr_area)
        qr_layout.setAlignment(Qt.AlignCenter)
        qr_layout.setContentsMargins(0, 10, 0, 10)
        qr_layout.setSpacing(10)
        qr_layout.addWidget(self.qr_label)
        qr_layout.addWidget(self.hide_qr_btn)
        self.qr_area.setVisible(False)

        # Buttons
        self.qr_btn = QPushButton("Generate QR")
        self.disconnect_btn = QPushButton("Disconnect")
        self.set_id_btn = QPushButton("Set Receiver ID")

        for btn in [self.qr_btn, self.disconnect_btn, self.set_id_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #3a3a3a;
                    color: white;
                    padding: 10px 20px;
                    font-size: 14px;
                    border-radius: 6px;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #505050;
                }
            """)

        self.qr_btn.clicked.connect(self.show_qr)
        self.disconnect_btn.clicked.connect(self.disconnect)
        self.set_id_btn.clicked.connect(self.set_receiver_id)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(20)
        btn_layout.addStretch()
        btn_layout.addWidget(self.qr_btn)
        btn_layout.addWidget(self.disconnect_btn)
        btn_layout.addWidget(self.set_id_btn)
        btn_layout.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(0)
        layout.addWidget(self.title_bar)
        layout.addSpacing(10)
        layout.addWidget(self.image_label, alignment=Qt.AlignCenter)
        layout.addWidget(self.qr_area, alignment=Qt.AlignCenter)
        layout.addLayout(btn_layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_image)
        self.timer.start(50)

    def toggle_max_restore(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def update_image(self):
        global latest_frame
        if latest_frame is not None:
            if self.qr_area.isVisible():
                self.hide_qr()

            mirrored = cv2.flip(latest_frame, 1)
            rgb = cv2.cvtColor(mirrored, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
            self.image_label.setPixmap(QPixmap.fromImage(img))
        else:
            self.image_label.setText("Waiting for frames...")


    def get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
        except:
            ip = "127.0.0.1"
        s.close()
        return ip

    def show_qr(self):
        token = generate_token()
        ip = self.get_local_ip()
        qr_data = f"http://{ip}:5000/upload?token={token}&id={self.receiver_id}"
        print("🔗 QR Data:", qr_data)

        qr_img = qrcode.make(qr_data)
        buf = BytesIO()
        qr_img.save(buf, format='PNG')
        buf.seek(0)

        qt_img = QImage()
        if qt_img.loadFromData(buf.read(), "PNG"):
            pixmap = QPixmap.fromImage(qt_img).scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.qr_label.setPixmap(pixmap)
            self.qr_label.setVisible(True)
            self.qr_area.setVisible(True)
            self.hide_qr_btn.setVisible(True)

    def hide_qr(self):
        self.qr_label.clear()
        self.qr_label.setVisible(False)
        self.qr_area.setVisible(False)
        self.hide_qr_btn.setVisible(False)

        if not self.qr_label.isVisible():
            return

        effect = QGraphicsOpacityEffect(self.qr_label)
        self.qr_label.setGraphicsEffect(effect)

        fade_anim = QPropertyAnimation(effect, b"opacity")
        fade_anim.setDuration(1000)
        fade_anim.setStartValue(1)
        fade_anim.setEndValue(0)
        fade_anim.setEasingCurve(QEasingCurve.InOutQuad)

        scale_anim = QPropertyAnimation(self.qr_label, b"geometry")
        rect = self.qr_label.geometry()
        scale_anim.setDuration(1000)
        scale_anim.setStartValue(rect)
        scale_anim.setEndValue(rect.adjusted(-30, -30, 30, 30))
        scale_anim.setEasingCurve(QEasingCurve.OutCubic)

        fade_anim.start()
        scale_anim.start()

        def cleanup():
            self.hide_qr()

        fade_anim.finished.connect(cleanup)
        self._fade_anim = fade_anim
        self._scale_anim = scale_anim

    def disconnect(self):
        global latest_frame, current_token
        latest_frame = None
        current_token = None
        self.image_label.setPixmap(QPixmap())
        self.image_label.setText("Disconnected")

    def set_receiver_id(self):
        dialog = IDDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            new_id = dialog.get_text().strip()
            if new_id:
                self.receiver_id = new_id
                QMessageBox.information(self, "Receiver ID Set", f"Receiver ID set to: {new_id}", QMessageBox.Ok)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()

# ------------------- START EVERYTHING -------------------
if __name__ == "__main__":
    threading.Thread(target=start_flask, daemon=True).start()
    app = QApplication(sys.argv)
    win = WebcamReceiver()
    win.show()
    sys.exit(app.exec_())
