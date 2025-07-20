from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.graphics.texture import Texture
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics import Color, RoundedRectangle
import cv2
from pyzbar.pyzbar import decode
import threading
import requests
from io import BytesIO
import time

# ---------------- Styled Button ----------------
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle

class StyledButton(ButtonBehavior, BoxLayout):
    def __init__(self, text, callback, bg_color=(0.05, 0.05, 0.05, 1), **kwargs):
        super().__init__(orientation='vertical', padding=[10, 12], size_hint=(1, None), height=50, **kwargs)
        self.callback = callback
        self.bg_color = bg_color

        with self.canvas.before:
            Color(*self.bg_color)
            self.bg = RoundedRectangle(radius=[12])
        self.bind(pos=self.update_bg, size=self.update_bg)

        self.label = Label(
            text=text,
            color=(1, 1, 1, 1),  # white text for contrast
            font_size=15,
            bold=True
        )
        self.add_widget(self.label)

    def update_bg(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size

    def on_press(self):
        if self.callback:
            self.callback(None)




# ---------------- Main UI ----------------
class WebcamSenderUI(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=20, spacing=10, **kwargs)
        Window.size = (420, 640)
        Window.clearcolor = (0.12, 0.12, 0.12, 1)
        self.stream_url = None
        self.running = False
        self.capture = None
        self.camera_index = 0


        # Title
        self.title = Label(
            text="CamDroid Sender",
            font_size=20,
            color=(1, 1, 1, 1),
            size_hint=(1, 0.1)
        )
        self.add_widget(self.title)

        # --- QR Preview ---
        from kivy.uix.widget import Widget

        self.qr_preview_box = BoxLayout(
            size_hint=(1, 0.5),
            padding=10,
            orientation='vertical'
        )

        # Black background with centered text
        self.qr_placeholder = BoxLayout(
            size_hint=(1, 1),
            padding=10,
            orientation='vertical'
        )
        with self.qr_placeholder.canvas.before:
            Color(0, 0, 0, 1)  # Black background
            self.qr_bg = RoundedRectangle(radius=[10])
        self.qr_placeholder.bind(pos=self.update_qr_bg, size=self.update_qr_bg)

        self.qr_text = Label(
            text="Waiting to scan QR",
            color=(1, 1, 1, 0.5),
            font_size=18,
            halign='center',
            valign='middle'
        )
        self.qr_text.bind(size=self.qr_text.setter('text_size'))

        self.qr_preview_image = Image()

        self.qr_placeholder.add_widget(self.qr_text)
        self.qr_preview_box.add_widget(self.qr_placeholder)
        self.add_widget(self.qr_preview_box)



        # --- QR Controls ---
        self.qr_controls = BoxLayout(size_hint=(1, None), height=60, spacing=10)

        self.scan_btn = StyledButton("Scan QR", self.start_qr_scan, bg_color=(0.1, 0.1, 0.1, 1))        # Dark blue-gray
        self.cancel_btn = StyledButton("Cancel Scan", self.cancel_qr_scan, bg_color=(0.15, 0.05, 0.05, 1))   # Dark red
        self.switch_btn = StyledButton("Switch Camera", self.switch_camera, bg_color=(0.1, 0.1, 0.1, 1))
        self.qr_controls.add_widget(self.switch_btn)

        self.cancel_btn.opacity = 0
        self.cancel_btn.disabled = True

        self.qr_controls.add_widget(self.scan_btn)
        self.qr_controls.add_widget(self.cancel_btn)
        self.add_widget(self.qr_controls)



        # Status
        self.status = Label(
            text="Status: Not Connected",
            font_size=14,
            color=(0.8, 0.8, 0.8, 1),
            size_hint=(1, 0.1)
        )
        self.add_widget(self.status)

        # Streaming Buttons
        self.start_btn = StyledButton("Start Streaming", self.start_stream, bg_color=(0.0, 0.2, 0.0, 1))
        self.start_btn.disabled = True
        self.stop_btn = StyledButton("Stop Streaming", self.stop_stream, bg_color=(0.2, 0.0, 0.0, 1))
        self.stop_btn.disabled = True
        self.add_widget(self.start_btn)
        self.add_widget(self.stop_btn)

    # ---- QR Scan Methods ----
    def start_qr_scan(self, _):
        self.capture = cv2.VideoCapture(self.camera_index)
        self.status.text = "Scanning QR..."
        Clock.schedule_interval(self.update_qr_frame, 1 / 30)
        self.cancel_btn.disabled = False
        self.cancel_btn.opacity = 1
        self.qr_preview_box.remove_widget(self.qr_placeholder)
        if self.qr_preview_image.parent is None:
            self.qr_preview_box.add_widget(self.qr_preview_image)



    def cancel_qr_scan(self, _):
        if self.capture:
            self.capture.release()
            self.capture = None
        Clock.unschedule(self.update_qr_frame)
        if self.qr_preview_image.parent:
            self.qr_preview_box.remove_widget(self.qr_preview_image)
        if self.qr_placeholder.parent is None:
            self.qr_preview_box.add_widget(self.qr_placeholder)

        self.status.text = "QR Scan cancelled"
        self.cancel_btn.disabled = True
        self.cancel_btn.opacity = 0

    def update_qr_frame(self, dt):
        if not self.capture or not self.capture.isOpened():
            return

        ret, frame = self.capture.read()
        if not ret:
            return

        decoded = decode(frame)

        # Show camera frame in app
        frame = cv2.flip(frame, 0)
        buf = frame.tobytes()
        img_texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
        img_texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
        self.qr_preview_image.texture = img_texture

        if decoded:
            url = decoded[0].data.decode()
            self.stream_url = url

            # Extract Receiver ID if present
            import urllib.parse as urlparse
            parsed = urlparse.urlparse(url)
            params = urlparse.parse_qs(parsed.query)
            receiver_id = params.get("id", ["Unknown"])[0]

            self.status.text = f"Connected to ID: {receiver_id}"
            
            # Hide QR UI immediately
            if self.qr_preview_image.parent:
                self.qr_preview_box.remove_widget(self.qr_preview_image)
            if self.qr_placeholder.parent is None:
                self.qr_preview_box.add_widget(self.qr_placeholder)

            # Cleanup scan
            self.capture.release()
            self.capture = None
            Clock.unschedule(self.update_qr_frame)
            self.cancel_btn.disabled = True
            self.cancel_btn.opacity = 0
            self.start_btn.disabled = False


    def update_qr_bg(self, *args):
        self.qr_bg.pos = self.qr_placeholder.pos
        self.qr_bg.size = self.qr_placeholder.size


    # ---- Streaming Methods ----
    def start_stream(self, _):
        if not self.stream_url:
            self.status.text = "No stream URL"
            return

        self.running = True
        self.start_btn.disabled = True
        self.stop_btn.disabled = False
        self.status.text = "Streaming..."
        threading.Thread(target=self.send_frames, daemon=True).start()

    def stop_stream(self, _):
        self.running = False
        self.start_btn.disabled = False
        self.stop_btn.disabled = True
        self.status.text = "Stopped"
    
    def switch_camera(self, _):
        self.camera_index = (self.camera_index + 1) % 3  # Try 0, 1, 2
        if self.capture:
            self.capture.release()
        self.capture = cv2.VideoCapture(self.camera_index)

        if not self.capture.isOpened():
            self.status.text = f"Camera {self.camera_index} not found. Switching back."
            self.camera_index = 0
            self.capture = cv2.VideoCapture(self.camera_index)

        self.status.text = f"Switched to Camera {self.camera_index}"


    def send_frames(self):
        cap = cv2.VideoCapture(self.camera_index)
        while self.running:
            ret, frame = cap.read()
            if not ret:
                continue

            _, img = cv2.imencode('.jpg', frame)
            buf = BytesIO(img.tobytes())
            try:
                res = requests.post(self.stream_url, files={'frame': buf}, timeout=2)
                if res.status_code == 403:
                    self.status.text = "Disconnected by Receiver"
                    self.running = False
                    break
            except:
                self.status.text = "Stream Error"
                self.running = False
                break

            time.sleep(0.04)
        cap.release()

# ---------------- App Start ----------------
class SenderApp(App):
    def build(self):
        return WebcamSenderUI()

if __name__ == "__main__":
    SenderApp().run()
