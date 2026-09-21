# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║     Kairozen All-in-One Bot v4 — カイロゼン                  ║
║     ហាង + SMM Panel · ដាក់លុយ KHQR · Top Up Game Menu       ║
║     Global Discount · Panel Admin · Promo Code              ║
║     Compatible: Python 3.10+ · Termux / Pydroid 3         ║
╚══════════════════════════════════════════════════════════════╝
ដំឡើង:
  pip install pyTelegramBotAPI requests flask qrcode pillow --break-system-packages
"""

import json, logging, time, re, threading, hashlib, io, os, sys, subprocess, datetime
import requests as http_req
import telebot
from telebot.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from flask import Flask, request as flask_request, jsonify
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ─── COLOR CONSTANTS FOR TERMINAL ───
CLR_RESET   = "\033[0m"
CLR_BOLD    = "\033[1m"
CLR_RED     = "\033[91m"
CLR_GREEN   = "\033[92m"
CLR_YELLOW  = "\033[93m"
CLR_BLUE    = "\033[94m"
CLR_MAGENTA = "\033[95m"
CLR_CYAN    = "\033[96m"
CLR_WHITE   = "\033[97m"

BG_RED      = "\033[41m"
BG_GREEN    = "\033[42m"
BG_BLUE     = "\033[44m"

# Custom Colored Formatter for Logging
class ColoredFormatter(logging.Formatter):
    FORMATS = {
        logging.DEBUG:    f"{CLR_CYAN}%(asctime)s{CLR_RESET} [{CLR_BLUE}%(levelname)s{CLR_RESET}] %(message)s",
        logging.INFO:     f"{CLR_CYAN}%(asctime)s{CLR_RESET} [{CLR_GREEN}%(levelname)s{CLR_RESET}] %(message)s",
        logging.WARNING:  f"{CLR_CYAN}%(asctime)s{CLR_RESET} [{CLR_YELLOW}%(levelname)s{CLR_RESET}] %(message)s",
        logging.ERROR:    f"{CLR_CYAN}%(asctime)s{CLR_RESET} [{CLR_RED}%(levelname)s{CLR_RESET}] %(message)s",
        logging.CRITICAL: f"{CLR_CYAN}%(asctime)s{CLR_RESET} [{CLR_BOLD}{CLR_RED}%(levelname)s{CLR_RESET}] %(message)s"
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)

# Setup Logging with Colors
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setFormatter(ColoredFormatter())
logger.addHandler(console_handler)

# ─── Auto-install deps ───
def _ensure_deps():
    pkgs = {"PIL": "pillow", "qrcode": "qrcode"}
    for mod, pkg in pkgs.items():
        try: __import__(mod)
        except ImportError:
            logger.info(f"{CLR_YELLOW}Installing missing package: {pkg}...{CLR_RESET}")
            subprocess.run([sys.executable, "-m", "pip", "install", pkg,
                            "--break-system-packages", "-q"], check=False)
_ensure_deps()

import qrcode
from PIL import Image, ImageDraw, ImageFont

# ═══════════════════════════════════════════════════════════
#  CONFIG  — ដូរតម្លៃទាំងនេះ
# ═══════════════════════════════════════════════════════════
BOT_TOKEN          = "8914728102:AAGkoa_RIi2hQmCMr8SzVdxZ7Nv7YgfRcIo"
ADMIN_ID           = 8807182741

# Bakong KHQR (ដាក់ Token ពេញលេញពីអ៊ីមែលរបស់អ្នក)
BAKONG_TOKEN       = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJkYXJjb2pMZm1lYzJNY1GQ2NDAyYiJvJiJvJjkuSWJXi03NDQzNDQzNTIzNzFNaHptNGxDbTYiLCJpc3MiOiJCYWtvbmcifQ.eyJhaGNvdW50X2lkIjoibW9uX3NhbW5hbmdAYmtydCIsImRhdGVfaXNzdWVkIjoiMTc2MzgyOTc1MCIsImV4cGlyZXNfYXQiOjE4MjkyMzg5NTB9"
BANK_ACCOUNT       = "mon_samnang@bkrt"
MERCHANT_NAME      = "Khmer SMM"
MERCHANT_CITY      = "Phnom Penh"

DEPOSIT_EXPIRE_SEC = 1200  # 20 នាទី[span_2](start_span)[span_2](end_span)
POLL_INTERVAL      = 5
STOCK_ALERT_MIN    = 5

# ═══════════════════════════════════════════════════════════
#  FILES
# ═══════════════════════════════════════════════════════════
WALLETS_FILE    = "aio_wallets.json"
USERS_FILE      = "aio_users.json"
LANG_FILE       = "aio_lang.json"
PROMO_FILE      = "aio_promos.json"
SETTINGS_FILE   = "aio_settings.json"
DISCOUNT_FILE   = "aio_discount.json"   # Global Discount File[span_3](start_span)[span_3](end_span)

PRODUCTS_FILE   = "aio_products.json"
ORDERS_FILE     = "aio_orders.json"
STOCK_FILE      = "aio_stock.json"
STORE_DEP_FILE  = "aio_store_deposits.json"
SEEN_TXN_FILE   = "aio_seen_txn.json"

SMM_API_FILE    = "aio_smm_api.json"
SMM_SVC_FILE    = "aio_smm_services.json"
SMM_ORD_FILE    = "aio_smm_orders.json"
SMM_PROFIT_FILE = "aio_smm_profit.json"
SMM_POLL_FILE   = "aio_smm_poll.json"

def _load(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except: return default

def _save(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e: logger.error(f"{CLR_RED}Save {path}: {e}{CLR_RESET}")

# ─── Load all state ───
wallets         = _load(WALLETS_FILE,   {})
users_db        = _load(USERS_FILE,     {})
user_lang       = _load(LANG_FILE,      {})
promos          = _load(PROMO_FILE,     {})
settings        = _load(SETTINGS_FILE,  {})
discount_config = _load(DISCOUNT_FILE,  {"active": False, "pct": 0})

products        = _load(PRODUCTS_FILE,  [])
orders          = _load(ORDERS_FILE,    {})
stock           = _load(STOCK_FILE,     {})
store_deps      = _load(STORE_DEP_FILE, {})
seen_txn        = set(_load(SEEN_TXN_FILE, []))

smm_api         = _load(SMM_API_FILE,   {"url": "", "key": ""})
smm_services    = _load(SMM_SVC_FILE,   {})
smm_orders      = _load(SMM_ORD_FILE,   {})
smm_profit      = _load(SMM_PROFIT_FILE,{"pct": 20})
smm_poll        = _load(SMM_POLL_FILE,  {"interval": POLL_INTERVAL})

waiting         = {}   # uid -> step/dict
lang_cooldown   = {}

# Default products including Mobile Legends, Free Fire KH/SG, Roblox, and PUBG Mobile
if not products:
    products = [
        {"id": "mobilelegends", "name": "Mobile Legends", "icon": "⚔️",
         "desc": "MLBB Top Up · Delivery via User ID & Zone ID",
         "plans": [
             {"label": "86 Diamonds", "price": 1.20},
             {"label": "172 Diamonds", "price": 2.40},
             {"label": "257 Diamonds", "price": 3.60},
             {"label": "706 Diamonds", "price": 9.50}
         ]},
        {"id": "freefire", "name": "Free Fire KH/SG", "icon": "💎",
         "desc": "Free Fire KH/SG Top Up · Delivery via User ID",
         "plans": [
             {"label": "Weekly Pass", "price": 1.54},
             {"label": "Monthly Membership", "price": 7.59},
             {"label": "Weekly Lite", "price": 0.31},
             {"label": "20 Diamonds", "price": 0.18},
             {"label": "40 Diamonds", "price": 0.36},
             {"label": "60 Diamonds", "price": 0.51},
             {"label": "100 Diamonds", "price": 0.87},
             {"label": "160 Diamonds", "price": 1.37},
             {"label": "205 Diamonds", "price": 1.75},
             {"label": "420 Diamonds", "price": 3.51},
             {"label": "650 Diamonds", "price": 5.39},
             {"label": "840 Diamonds", "price": 6.98},
             {"label": "1100 Diamonds", "price": 8.79},
             {"label": "2250 Diamonds", "price": 17.85},
             {"label": "3350 Diamonds", "price": 25.79},
             {"label": "4500 Diamonds", "price": 33.85},
             {"label": "4765 Diamonds", "price": 37.19},
             {"label": "5600 Diamonds", "price": 43.59},
             {"label": "6700 Diamonds", "price": 50.79},
             {"label": "7650 Diamonds", "price": 58.98},
             {"label": "11500 Diamonds", "price": 87.89}
         ]},
        {"id": "roblox", "name": "Roblox Robux", "icon": "🟥",
         "desc": "Roblox Robux Top Up · Delivery via Username",
         "plans": [
             {"label": "400 Robux", "price": 4.99},
             {"label": "800 Robux", "price": 9.99},
             {"label": "1700 Robux", "price": 19.99}
         ]},
        {"id": "pubgmobile", "name": "PUBG Mobile", "icon": "🔫",
         "desc": "PUBG Mobile UC Top Up · Delivery via Player ID",
         "plans": [
             {"label": "60 UC", "price": 0.99},
             {"label": "325 UC", "price": 4.99},
             {"label": "660 UC", "price": 9.99},
             {"label": "1800 UC", "price": 24.99}
         ]},
    ]
    _save(PRODUCTS_FILE, products)

# ═══════════════════════════════════════════════════════════
#  BOT + HTTP
# ═══════════════════════════════════════════════════════════
bot = telebot.TeleBot(BOT_TOKEN, parse_mode=None)

def _make_session():
    s = http_req.Session()
    r = Retry(total=3, backoff_factor=2, status_forcelist=[500,502,503,504])
    a = HTTPAdapter(max_retries=r)
    s.mount("http://", a); s.mount("https://", a)
    return s
http = _make_session()

# ═══════════════════════════════════════════════════════════
#  LANGUAGE
# ═══════════════════════════════════════════════════════════
STRINGS = {
    "kh": {
        "welcome": (
            "👋 សូស្ដីមក <b>Kairozen カイロゼン</b>!\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🌟 Bot នេះផ្ដល់សេវាកម្ម:\n"
            "🛍️ ទិញផលិតផលឌីជីថល & Top Up Game\n"
            "📊 សេវា SMM (Followers/Likes)\n"
            "💳 បញ្ចូលលុយ · ប្រវត្តិ · ជំនួយ\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "💰 សាច់ប្រាក់: <b>${:.2f}</b>"
        ),
        "select_lang":   "🌐 ជ្រើសរើសភាសា:",
        "lang_set":      "✅ ភាសាត្រូវបានផ្លាស់ប្ដូរ!",
        "menu":          "🏠 ត្រឡប់ Menu ដើម",
        "banned":        "🚫 គណនីរបស់អ្នកត្រូវបាន ban!",
        "cancel_ok":     "🏠 Menu",
        "no_service":    "❌ គ្មាន SMM Service ទេ",
        "choose_platform": "ជ្រើស Platform:",
        "choose_qty":    "ជ្រើស ចំនួន:",
        "send_link":     "ផ្ញើ Link របស់អ្នក:",
        "low_balance":   "❌ លុយមិនគ្រប់!",
        "order_done":    "✅ បញ្ជាទិញបានជោគជ័យ!",
        "deposit_ok":    "✅ ដាក់លុយបានជោគជ័យ!",
        "qr_expired":    "⏰ QR ផុតកំណត់! សូម top up ម្ដងទៀត",
        "qr_error":      "⚠️ QR Generate Error! ទំនាក់ Admin",
        "order_notfound":"❌ Order រកមិនឃើញ!",
        "no_orders":     "❌ គ្មាន Order ទេ!",
        "how_to_use": (
            "💡 <b>របៀបប្រើប្រាស់</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "1️⃣ ចុច <b>💳 ដាក់ប្រាក់</b> → ជ្រើស ចំនួន → ស្កេន QR តាម Bakong[span_4](start_span)[span_4](end_span)\n"
            "2️⃣ ចុច <b>🛍️ ហាងឌីជីថល</b> → ជ្រើស ផលិតផល → Plan → ទូទាត់[span_5](start_span)[span_5](end_span)\n"
            "3️⃣ ចុច <b>💎 ថុបអាប់ហ្គេម</b> → ជ្រើសហ្គេម និងកញ្ចប់ → បញ្ចូល ID[span_6](start_span)[span_6](end_span)\n"
            "4️⃣ ចុច <b>📊 សេវាកម្ម SMM</b> → Platform → សេវា → ចំនួន → ផ្ញើ Link[span_7](start_span)[span_7](end_span)"
        ),
        "support_msg": (
            "💬 <b>ជំនួយ</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "📞 Admin: https://t.me/KhmerSMM007\n"
            "🌐 Channel: "
        ),
        "fallback": "❓ ប្រើ Menu ខាងក្រោម",
    },
    "en": {
        "welcome": (
            "👋 Welcome to <b>Kairozen カイロゼン</b>!\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "🌟 Services available:\n"
            "🛍️ Buy Digital Products & Game Top Up\n"
            "📊 SMM Services (Followers/Likes)\n"
            "💳 Top Up · History · Support\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "💰 Balance: <b>${:.2f}</b>"
        ),
        "select_lang":   "🌐 Select Language:",
        "lang_set":      "✅ Language changed!",
        "menu":          "🏠 Back to Menu",
        "banned":        "🚫 Your account has been banned!",
        "cancel_ok":     "🏠 Menu",
        "no_service":    "❌ No SMM Services available",
        "choose_platform": "Choose Platform:",
        "choose_qty":    "Choose Quantity:",
        "send_link":     "Send your Link:",
        "low_balance":   "❌ Insufficient balance!",
        "order_done":    "✅ Order placed successfully!",
        "deposit_ok":    "✅ Deposit successful!",
        "qr_expired":    "⏰ QR expired! Please top up again",
        "qr_error":      "⚠️ QR Generate Error! Contact Admin",
        "order_notfound":"❌ Order not found!",
        "no_orders":     "❌ No orders yet!",
        "how_to_use": (
            "💡 <b>How to Use</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "1️⃣ Tap <b>💳 Top Up</b> → Choose Amount → Scan Bakong QR[span_8](start_span)[span_8](end_span)\n"
            "2️⃣ Tap <b>🛍️ Shop</b> → Choose Product → Plan → Pay[span_9](start_span)[span_9](end_span)\n"
            "3️⃣ Tap <b>💎 Game Top Up</b> → Choose Game/Package → Enter ID[span_10](start_span)[span_10](end_span)\n"
            "4️⃣ Tap <b>📊 SMM Services</b> → Platform → Service → Qty → Send Link[span_11](start_span)[span_11](end_span)"
        ),
        "support_msg": (
            "💬 <b>Support</b>\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "📞 Admin: @KhmerSmm099\n"
            "🌐 Channel: @KhmerSmm099"
        ),
        "fallback": "❓ Use the menu below",
    },
}

def get_lang(uid): return user_lang.get(str(uid), "kh")

def t(uid, key, *args):
    lang = get_lang(uid)
    s = STRINGS.get(lang, STRINGS["kh"]).get(key) or STRINGS["kh"].get(key, key)
    if args:
        try: return s.format(*args)
        except: return s
    return s

def toggle_lang(uid):
    uid_str = str(uid)
    now = time.time()
    if now - lang_cooldown.get(uid_str, 0) < 3.0: return
    lang_cooldown[uid_str] = now
    cycle = {"kh": "en", "en": "kh"}
    user_lang[uid_str] = cycle.get(get_lang(uid), "kh")
    _save(LANG_FILE, user_lang)

def lang_flag(uid):
    return {"kh": "🇰🇭 ខ្មែរ", "en": "🇬🇧 English"}.get(get_lang(uid), "🇰🇭")

# ═══════════════════════════════════════════════════════════
#  WALLET & DISCOUNT HELPERS
# ═══════════════════════════════════════════════════════════
def bal(uid): return float(wallets.get(str(uid), 0))
def add_bal(uid, amt):
    wallets[str(uid)] = round(bal(uid) + amt, 2)
    _save(WALLETS_FILE, wallets)
def ded_bal(uid, amt):
    wallets[str(uid)] = max(0, round(bal(uid) - amt, 2))
    _save(WALLETS_FILE, wallets)
def set_bal(uid, amt):
    wallets[str(uid)] = round(float(amt), 2)
    _save(WALLETS_FILE, wallets)

def _calc_discounted_price(price):
    if discount_config.get("active", False):
        pct = float(discount_config.get("pct", 0))
        return round(price * (1 - pct / 100), 2)
    return price

# ═══════════════════════════════════════════════════════════
#  PROMO CODE
# ═══════════════════════════════════════════════════════════
def apply_promo(uid, code, amount):
    code = code.strip().upper()
    p = promos.get(code)
    if not p: return amount, 0, "❌ Promo Code ខុស!"
    if p.get("uses", 0) > 0 and p.get("used", 0) >= p["uses"]:
        return amount, 0, "❌ Promo Code ផុតសិទ្ធហើយ!"
    user_used = p.get("user_used", {})
    if str(uid) in user_used:
        return amount, 0, "❌ អ្នកបានប្រើ Promo Code នេះហើយ!"
    if p.get("pct", False):
        discount = round(amount * float(p["discount"]) / 100, 2)
    else:
        discount = min(float(p["discount"]), amount)
    final = max(0, round(amount - discount, 2))
    return final, discount, None

def confirm_promo(code, uid):
    code = code.strip().upper()
    p = promos.get(code)
    if not p: return
    p["used"] = p.get("used", 0) + 1
    uu = p.get("user_used", {})
    uu[str(uid)] = 1
    p["user_used"] = uu
    _save(PROMO_FILE, promos)

# ═══════════════════════════════════════════════════════════
#  KEYBOARDS
# ═══════════════════════════════════════════════════════════
def main_kb(uid=None):
    lang = get_lang(uid) if uid else "kh"
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == "en":
        kb.row("🛍️ Shop",          "💎 Game Top Up")
        kb.row("📊 SMM Services",  "📦 Orders")
        kb.row("💳 Top Up",        "👜 Wallet",         "📜 History")
        kb.row("💬 Support",       "💡 How to Use",    "🌐 Language")
    else:
        kb.row("🛍️ ហាងឌីជីថល",    "💎 ថុបអាប់ហ្គេម")
        kb.row("📊 សេវាកម្ម SMM",  "📦 ការបញ្ជាទិញ")
        kb.row("💳 ដាក់ប្រាក់",    "👜 កាបូបលុយ",      "📜 ប្រវត្តិ")
        kb.row("💬 ជំនួយ Support", "💡 របៀបប្រើប្រាស់", "🌐 ភាសា / Language")
    return kb

def admin_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🛍️ ផលិតផល",       "📦 ការបញ្ជាទិញ")
    kb.row("💎 គ្រប់គ្រងហ្គេម",   "✏️ កែតម្លៃហ្គេម")
    kb.row("📦 ស្តុក",         "➕ បន្ថែមស្តុក",    "➕ បន្ថែមផលិតផល")
    kb.row("➕ បន្ថែមគ្រប់សេវាកម្ម", "🔥 បញ្ចុះតម្លៃទាំងអស់")
    kb.row("✏️ កែតម្លៃ",       "💳 ប្រាក់បញ្ញើ")
    kb.row("━━━ 📊 SMM ━━━")
    kb.row("📊 ការបញ្ជា SMM",  "⚙️ កំណត់ SMM API")
    kb.row("➕ បន្ថែម SMM",    "🗑️ លុប SMM")
    kb.row("💹 ប្រាក់ចំណេញ SMM")
    kb.row("━━━ 💰 ហិរញ្ញវត្ថុ ━━━")
    kb.row("💰 កាបូបលុយ",      "💰 ឆែកលុយ API")
    kb.row("💸 បន្ថែមប្រាក់",   "💔 កាត់ប្រាក់")
    kb.row("━━━ 👥 អ្នកប្រើ ━━━")
    kb.row("👥 អ្នកប្រើប្រាស់",  "📊 ស្ថិតិ")
    kb.row("🎟️ លេខកូដPromo",   "📢 ផ្សព្វផ្សាយ")
    kb.row("⏱ ល្បឿន Poll",     "🔄 ធ្វើឱ្យទាន់សម័យ")
    return kb

def cancel_kb():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("✕ Cancel")
    return kb

def lang_select_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇰🇭 ខ្មែរ", callback_data="setlang:kh"),
         InlineKeyboardButton("🇬🇧 English", callback_data="setlang:en")]
    ])

def deposit_amt_kb(uid=None, promo_code=None):
    lang = get_lang(uid) if uid else "kh"
    amts = [1, 2, 5, 10, 20, 50]
    btns = []
    row = []
    for a in amts:
        row.append(InlineKeyboardButton(f"${a}", callback_data=f"dep:{a}"))
        if len(row) == 3:
            btns.append(row); row = []
    if row: btns.append(row)
    btns.append([InlineKeyboardButton(
        "✏️ ផ្ទាល់ខ្លួន" if lang=="kh" else "✏️ Custom",
        callback_data="dep:custom")])
    if promo_code:
        btns.append([InlineKeyboardButton(
            f"🎟️ Promo: {promo_code} ✅", callback_data="dep:clrpromo")])
    else:
        btns.append([InlineKeyboardButton(
            "🎟️ ដាក់ Promo Code" if lang=="kh" else "🎟️ Enter Promo Code",
            callback_data="dep:promo")])
    return InlineKeyboardMarkup(btns)

def game_menu_kb():
    btns = []
    game_ids = ["mobilelegends", "freefire", "roblox", "pubgmobile"]
    game_list = [p for p in products if p["id"] in game_ids]
    for g in game_list:
        btns.append([InlineKeyboardButton(f"{g.get('icon','🎮')} {g['name']}", callback_data=f"game_sel:{g['id']}")])
    btns.append([InlineKeyboardButton("🔙 Back", callback_data="back:main")])
    return InlineKeyboardMarkup(btns)

def smm_cat_kb():
    PLATFORM_ICONS = {
        "tiktok": "🎵", "telegram": "📱", "facebook": "📘",
        "instagram": "📸", "youtube": "▶️", "twitter": "🐦",
        "x": "🐦", "threads": "🧵"
    }
    cats = _smm_get_categories()
    btns = []
    for cat in cats:
        icon = "📱"
        for key, ico in PLATFORM_ICONS.items():
            if key in cat.lower(): icon = ico; break
        btns.append([InlineKeyboardButton(f"{icon}  {cat}", callback_data=f"smmcat:{cat}")])
    btns.append([InlineKeyboardButton("🔙 Back", callback_data="back:main")])
    return InlineKeyboardMarkup(btns)

def smm_svc_kb(cat):
    SVC_ICONS = {
        "follower":"👤","like":"❤️","view":"👁","comment":"💬",
        "share":"🔗","save":"🔖","member":"👥","subscriber":"🔔",
        "watch":"👀","reaction":"😍",
    }
    svcs = _smm_get_svcs_in_cat(cat)
    btns = []
    for slug, s in svcs:
        label = s.get("label", slug)
        icon = "⚡"
        for key, ico in SVC_ICONS.items():
            if key in label.lower(): icon = ico; break
        btns.append([InlineKeyboardButton(f"{icon}  {label}", callback_data=f"smmsvc:{slug}")])
    btns.append([InlineKeyboardButton("🔙 Back", callback_data="back:smmcats")])
    return InlineKeyboardMarkup(btns)

def smm_qty_kb(slug, s):
    sr   = _smm_sell_rate(s["cost_rate"], slug)
    mn   = s.get("min", 100)
    mx   = s.get("max", 100000)
    label= s.get("label", slug)
    first= label.split()[0] if label else slug
    preset = s.get("preset_qtys")
    if preset and isinstance(preset, list):
        qtys 
