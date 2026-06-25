import os

# ============ الإعدادات الأساسية ============
API_ID = 22334084
API_HASH = "b599ca4e4c68f97072aa690fc8e76cdf"
BOT_TOKEN = "8873866209:AAExp-CQKB8-6WDARWcotQKm8HUEpIomeKM"
OWNER_ID = 7753969972

# ============ المسارات ============
BASE_DIR = "data"
SESSIONS_DIR = os.path.join(BASE_DIR, "sessions")
CAPTURED_DIR = os.path.join(BASE_DIR, "captured_media")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
DB_FILE = os.path.join(BASE_DIR, "bot.db")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

# ============ إنشاء المجلدات ============
for d in [SESSIONS_DIR, CAPTURED_DIR, LOGS_DIR, BACKUP_DIR, BASE_DIR]:
    os.makedirs(d, exist_ok=True)

# ============ إعدادات المراقبة ============
MAX_TARGETS = 20              # أقصى عدد أهداف
AUTO_DELETE_DAYS = 30         # حذف تلقائي بعد (0 = معطل)
DAILY_REPORT_HOUR = 20        # ساعة التقرير اليومي (24h)

# ============ إعدادات الوسائط ============
COMPRESS_MEDIA = True         # ضغط الوسائط
MAX_FILE_SIZE_MB = 50         # أقصى حجم ملف
ENABLE_OCR = True             # استخراج النص من الصور
ENABLE_WHISPER = True         # تحويل الصوت لنص

# ============ الأمان ============
BOT_PASSWORD = None           # ضع كلمة مرور أو None للتعطيل
ENCRYPT_FILES = False         # تشفير الملفات المحفوظة
STEALTH_MODE = False          # إخفاء آخر ظهور

# ============ Google Drive (اختياري) ============
GDRIVE_ENABLED = False
GDRIVE_CREDENTIALS = "credentials.json"
GDRIVE_FOLDER_ID = None
