# 🛡️ Webcam Guard (Telegram Intrusion Alert)

A lightweight Python security guard that turns your PC webcam into a silent motion & face surveillance camera. When someone approaches your desk or looks toward your screen, it saves a timestamped snapshot locally and immediately sends you an alert photo on Telegram.

---

## ✨ Features

- **Double Detection**: Detects both sudden motion (via adaptive Gaussian background subtraction) and faces looking toward the camera (via Haar Cascade).
- **Instant Telegram Alerts**: Sends real-time photo alerts directly to your private Telegram chat.
- **Auto Keep-Awake**: Prevents Windows from putting your computer to sleep while watching.
- **Smart Cooldown & Retry**: Prevents spamming alerts, and retries photo uploads if Wi-Fi hiccups.
- **Secure Credentials**: Reads bot tokens and chat IDs from `.env` so private keys are never committed to git.
- **Zero Heavy Dependencies**: Built solely on `opencv-python` and `requests` (no extra dotenv package required).

---

## 🚀 Quick Setup

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/your-username/webcam-guard.git
cd webcam-guard
pip install -r requirements.txt
```

### 2. Create your Telegram Bot (~1 minute)
1. In Telegram, search for `@BotFather` and send `/newbot`.
2. Follow the prompt to name your bot and choose a username.
3. BotFather will provide your **`TG_BOT_TOKEN`**.
4. Open the link to your new bot in Telegram and click **Start** (or send `"hi"`).

### 3. Configure `.env`
Copy the example environment template:
```bash
cp .env.example .env
```
Open `.env` and paste your bot token:
```ini
TG_BOT_TOKEN=your_token_from_botfather
TG_CHAT_ID=
```

### 4. Automatically Fetch your Chat ID
Run the setup helper:
```bash
python guard.py --setup
```
It will display your personal `CHAT_ID`. Copy and paste it into `.env`:
```ini
TG_CHAT_ID=your_chat_id_here
```

---

## 🏃 Usage

Start the guard:
```bash
python guard.py
```

1. **Arming countdown (20s)**: Gives you 20 seconds to step away while the camera adjusts exposure.
2. **Notification**: You'll receive `🛡️ Guard is ON - watching your PC.` on Telegram.
3. **Alerts**: If anyone walks up or looks at your screen, you'll receive a photo alert stamped with date and time.
4. **Disarm**: When you return, press `Ctrl + C` in the terminal.

---

## ⚙️ Configuration

You can customize the detection sensitivity and cooldowns in `.env`:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `TG_BOT_TOKEN` | *(required)* | Telegram bot token from @BotFather |
| `TG_CHAT_ID` | *(required)* | Your Telegram user ID |
| `CAMERA_INDEX` | `0` | Camera index (`0` for built-in, `1` for USB webcam) |
| `ARM_DELAY` | `20` | Seconds to leave your desk before detection starts |
| `COOLDOWN` | `12` | Minimum seconds between two photo notifications |
| `MOTION_RATIO` | `0.08` | Threshold for motion (lower = more sensitive) |

---

## 📁 Project Structure

```
├── guard.py           # Main camera detection & Telegram dispatch script
├── requirements.txt   # Python dependencies
├── .env.example       # Template for environment variables
├── .gitignore         # Prevents secrets, captures & heavy files from git
└── README.md          # Project documentation
```
