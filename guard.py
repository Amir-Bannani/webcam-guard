"""
guard.py - Webcam guard.
Watches your webcam and sends timestamped Telegram alerts & photos when someone approaches your PC.

SETUP:
  1. pip install -r requirements.txt
  2. Copy .env.example to .env
  3. Create a Telegram bot via @BotFather -> copy the token to TG_BOT_TOKEN in .env
  4. Open your bot in Telegram and send it a message (e.g. "hi")
  5. Run: python guard.py --setup
     Copy the CHAT_ID it prints to TG_CHAT_ID in .env
  6. Run: python guard.py (you get 20 s to walk away)

STOP: Press Ctrl+C in the terminal.
"""
import os
import sys
import time
import ctypes
import datetime
import threading
from pathlib import Path

import cv2
import requests


def load_env(env_path=".env"):
    """Lightweight .env loader (avoids needing python-dotenv)."""
    p = Path(env_path)
    if not p.is_file():
        return
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key, val = key.strip(), val.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = val


load_env()

# ------------------------- CONFIG -------------------------
BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TG_CHAT_ID", "").strip()

CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))
ARM_DELAY = int(os.getenv("ARM_DELAY", "20"))
COOLDOWN = int(os.getenv("COOLDOWN", "12"))
MOTION_RATIO = float(os.getenv("MOTION_RATIO", "0.08"))
SAVE_DIR = Path("captures")   # local backup of every photo
# -----------------------------------------------------------

API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_text(text):
    try:
        requests.post(f"{API}/sendMessage", data={"chat_id": CHAT_ID, "text": text}, timeout=15)
    except requests.RequestException as e:
        print("Could not send message:", e)


def send_photo(path, caption):
    for _ in range(3):  # retry if the university wifi hiccups
        try:
            with open(path, "rb") as f:
                r = requests.post(
                    f"{API}/sendPhoto",
                    data={"chat_id": CHAT_ID, "caption": caption},
                    files={"photo": f},
                    timeout=30,
                )
            if r.ok:
                print("Photo sent:", path)
                return
            print("Telegram error:", r.status_code, r.text)
        except requests.RequestException as e:
            print("Send failed, retrying:", e)
        time.sleep(3)


def setup():
    """Prints your chat id after you've messaged the bot."""
    try:
        data = requests.get(f"{API}/getUpdates", timeout=15).json()
    except requests.RequestException as e:
        sys.exit(f"Network error: {e}")
    if not data.get("ok"):
        sys.exit(f"Telegram says: {data}  -> check BOT_TOKEN")
    chats = {}
    for u in data.get("result", []):
        chat = (u.get("message") or {}).get("chat")
        if chat:
            chats[chat["id"]] = chat.get("first_name") or chat.get("title") or ""
    if not chats:
        sys.exit("No messages found. Send a message to your bot in Telegram, then run --setup again.")
    for cid, name in chats.items():
        print(f'CHAT_ID = "{cid}"   ({name})')


def keep_awake():
    """Stops Windows from going to sleep while the script runs (closing the lid still sleeps!)."""
    if sys.platform == "win32":
        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)


def open_camera():
    cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW) if sys.platform == "win32" else cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        sys.exit("Cannot open the camera. Close other apps using it, or change CAMERA_INDEX.")
    return cap


def main():
    if "--setup" in sys.argv:
        if not BOT_TOKEN:
            sys.exit("Please set TG_BOT_TOKEN in your .env file first.")
        return setup()
    if not BOT_TOKEN or not CHAT_ID or "PASTE_" in BOT_TOKEN or "PASTE_" in CHAT_ID:
        sys.exit("Please configure TG_BOT_TOKEN and TG_CHAT_ID in your .env file (see .env.example).")

    keep_awake()
    SAVE_DIR.mkdir(exist_ok=True)
    faces_model = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    cap = open_camera()

    print(f"Arming in {ARM_DELAY} s - walk away now...")
    t0 = time.time()
    while time.time() - t0 < ARM_DELAY:  # keep reading so the camera adjusts exposure
        cap.read()
    send_text("🛡️ Guard is ON - watching your PC.")
    print("Watching. Ctrl+C to stop.")

    background = None
    last_sent = 0.0
    failures = 0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                failures += 1
                if failures == 50:
                    send_text("⚠️ Camera stopped working!")
                time.sleep(0.2)
                continue
            failures = 0

            h, w = frame.shape[:2]
            small = cv2.resize(frame, (640, int(h * 640 / w)))
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (21, 21), 0)

            # Motion: compare with a slowly-updating background (adapts to light changes)
            if background is None:
                background = blur.astype("float")
                continue
            diff = cv2.absdiff(blur, cv2.convertScaleAbs(background))
            cv2.accumulateWeighted(blur, background, 0.02)
            mask = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1]
            motion = cv2.countNonZero(mask) / mask.size

            # Face: someone looking toward the screen
            faces = faces_model.detectMultiScale(gray, 1.2, 5, minSize=(60, 60))

            reason = None
            if len(faces) > 0:
                reason = "face detected"
            elif motion > MOTION_RATIO:
                reason = "someone close to the PC"

            if reason and time.time() - last_sent > COOLDOWN:
                last_sent = time.time()
                stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                shot = frame.copy()
                cv2.putText(shot, stamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
                path = SAVE_DIR / f"{datetime.datetime.now():%Y%m%d_%H%M%S}.jpg"
                cv2.imwrite(str(path), shot)
                threading.Thread(
                    target=send_photo, args=(str(path), f"⚠️ {reason} - {stamp}"), daemon=True
                ).start()
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        send_text("🛑 Guard stopped.")
        print("Stopped.")


if __name__ == "__main__":
    main()