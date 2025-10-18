import subprocess
import time
import webbrowser
import os
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

# === CONFIGURATION ===
APP_TITLE = "FMTECH Operation Dashboard"
DASHBOARD_SCRIPT = "fmtech_dashboard.py"
LOCAL_URL = "http://localhost:8501"
LOGO_PATH = "fmtech_logo.jpg"

# === SPLASH SCREEN ===
root = tk.Tk()
root.title(APP_TITLE)
root.geometry("700x400")
root.configure(bg="#0b5394")
root.overrideredirect(True)
root.eval('tk::PlaceWindow . center')

# Logo
try:
    img = Image.open(LOGO_PATH)
    img = img.resize((150, 150), Image.LANCZOS)
    logo = ImageTk.PhotoImage(img)
    logo_label = tk.Label(root, image=logo, bg="#0b5394")
    logo_label.pack(pady=20)
except Exception:
    pass

# Loading Text
label = tk.Label(root, text=f"Loading {APP_TITLE} — please wait...",
                 font=("Segoe UI", 13), fg="#c1a14f", bg="#0b5394")
label.pack(pady=10)

# Progress Bar
progress = ttk.Progressbar(root, mode="indeterminate", length=300)
progress.pack(pady=20)
progress.start(15)

# === LAUNCH FUNCTION ===
def launch_dashboard():
    try:
        subprocess.Popen(["streamlit", "run", DASHBOARD_SCRIPT], shell=True)
        time.sleep(5)
        webbrowser.open(LOCAL_URL)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        root.destroy()

root.after(2500, launch_dashboard)
root.mainloop()
