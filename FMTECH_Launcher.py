# FMTECH_Launcher.py
import os, sys, time, socket, threading, subprocess, webbrowser
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk  # pip install pillow

APP_PORT = 8501
SPLASH_SECS = 7
FMTECH_BLUE = "#0b5394"   # أزرق FMTECH
FMTECH_GOLD = "#b59b3b"   # ذهبي FMTECH

def resource_path(rel):
    # يدعم وضع PyInstaller (داخل مجلد _MEIPASS)
    base = getattr(sys, "_MEIPASS", os.path.abspath(os.path.dirname(__file__)))
    return os.path.join(base, rel)

def cwd_path():
    # مجلد المشروع الذي يحتوي fmtech_dashboard.py
    # عند تشغيل الـ EXE سيكون __file__ = المسار المؤقت لـ PyInstaller
    # لذا نستخدم مكان وجود الـ EXE كـ CWD للمشروع
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def is_port_open(host="127.0.0.1", port=APP_PORT, timeout=0.5):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False

def ensure_deps():
    """
    يحاول استيراد streamlit. لو فشل، يثبت المكتبات من requirements.txt
    بدون أي نوافذ، ويحدّث رسالة الحالة على شاشة البداية.
    """
    try:
        import streamlit  # noqa
        return True, "Dependencies OK"
    except Exception:
        pass

    req = os.path.join(cwd_path(), "requirements.txt")
    if not os.path.exists(req):
        return False, "requirements.txt not found"

    try:
        # تثبيت صامت بدون نافذة
        flags = 0
        if os.name == "nt":
            flags = subprocess.CREATE_NO_WINDOW
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", req],
            cwd=cwd_path(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags
        )
        return True, "Dependencies installed"
    except subprocess.CalledProcessError:
        return False, "pip install failed"

def launch_streamlit(status_cb=lambda s: None):
    """
    يشغّل Streamlit في الخلفية بدون نافذة، من ملف fmtech_dashboard.py
    """
    app_py = os.path.join(cwd_path(), "fmtech_dashboard.py")
    if not os.path.exists(app_py):
        status_cb("fmtech_dashboard.py not found")
        return False

    # تأكد من التبعيات
    ok, msg = ensure_deps()
    status_cb(msg)
    if not ok:
        return False

    # تشغيل streamlit headless وعلى نفس المنفذ
    cmd = [
        sys.executable, "-m", "streamlit", "run", "fmtech_dashboard.py",
        "--server.headless=true",
        f"--server.port={APP_PORT}",
        "--browser.gatherUsageStats=false"
    ]
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NO_WINDOW

    try:
        subprocess.Popen(
            cmd,
            cwd=cwd_path(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags
        )
        status_cb("Starting Streamlit…")
        return True
    except Exception as e:
        status_cb(f"Failed to start: {e}")
        return False

class Splash(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FMTECH")
        self.overrideredirect(True)  # بدون إطار
        self.configure(bg=FMTECH_BLUE)

        # قياس 550x300 وتوسيط
        w, h = 550, 300
        ws, hs = self.winfo_screenwidth(), self.winfo_screenheight()
        x, y = int((ws - w) / 2), int((hs - h) / 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

        # شعار
        logo_path = resource_path("fmtech_logo.jpg")
        try:
            im = Image.open(logo_path)
            # ملاءمة ارتفاع ~140px
            ratio = 140 / im.height
            im = im.resize((int(im.width * ratio), int(im.height * ratio)), Image.LANCZOS)
            self.logo = ImageTk.PhotoImage(im)
            tk.Label(self, image=self.logo, bg=FMTECH_BLUE).pack(pady=(30, 10))
        except Exception:
            tk.Label(self, text="FMTECH", fg="white", bg=FMTECH_BLUE,
                     font=("Segoe UI", 28, "bold")).pack(pady=(40, 10))

        # نص
        self.msg_var = tk.StringVar(value="Loading FMTECH Operation Dashboard — please wait…")
        tk.Label(self, textvariable=self.msg_var, fg=FMTECH_GOLD, bg=FMTECH_BLUE,
                 font=("Segoe UI", 12)).pack(pady=(0, 10))

        # شريط تقدم بسيط
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Gold.Horizontal.TProgressbar",
                        troughcolor=FMTECH_BLUE, bordercolor=FMTECH_BLUE,
                        background=FMTECH_GOLD, lightcolor=FMTECH_GOLD, darkcolor=FMTECH_GOLD)
        self.pb = ttk.Progressbar(self, orient="horizontal",
                                  length=380, mode="indeterminate",
                                  style="Gold.Horizontal.TProgressbar")
        self.pb.pack(pady=(0, 10))
        self.pb.start(12)

        # تشغيل ستريمليت بخيط جانبي
        self.start_time = time.time()
        threading.Thread(target=self._start_and_wait, daemon=True).start()

    def set_status(self, text):
        self.msg_var.set(text)
        self.update_idletasks()

    def _start_and_wait(self):
        # 1) شغل ستريمليت
        ok = launch_streamlit(self.set_status)
        if not ok:
            self.set_status("Failed to start Streamlit.")
            time.sleep(3)
            self._quit()
            return

        # 2) انتظر فتح المنفذ + تأكد من 7 ثواني حد أدنى
        deadline = self.start_time + SPLASH_SECS
        while time.time() < deadline or not is_port_open():
            time.sleep(0.2)
            # لو المنفذ انفتح قبل 7 ثواني، نكمل عدّ الزمن حتى يتم الـ 7 ثواني
            # ولو ما انفتح بعد 60 ثانية، نفتح المتصفح على أي حال
            if time.time() - self.start_time > 60:
                break

        # 3) افتح المتصفح الافتراضي
        try:
            webbrowser.open(f"http://localhost:{APP_PORT}", new=2)
        except Exception:
            pass

        # 4) أغلق السبلّاش
        self._quit()

    def _quit(self):
        try:
            self.destroy()
        except Exception:
            pass

def main():
    app = Splash()
    app.mainloop()

if __name__ == "__main__":
    main()
