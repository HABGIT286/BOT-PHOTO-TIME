import sqlite3
import json
import os
from datetime import datetime
from config import DB_FILE

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()
    
    def _init_tables(self):
        c = self.conn.cursor()
        
        # جدول الحسابات
        c.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT UNIQUE,
                session_file TEXT,
                user_id INTEGER,
                first_name TEXT,
                username TEXT,
                is_active BOOLEAN DEFAULT 0,
                added_at TEXT
            )
        """)
        
        # جدول الأهداف
        c.execute("""
            CREATE TABLE IF NOT EXISTS targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_phone TEXT,
                target_input TEXT,
                target_id INTEGER,
                target_name TEXT,
                target_type TEXT,
                enabled BOOLEAN DEFAULT 1,
                added_at TEXT,
                FOREIGN KEY(account_phone) REFERENCES accounts(phone)
            )
        """)
        
        # جدول الوسائط الملتقطة
        c.execute("""
            CREATE TABLE IF NOT EXISTS captured_media (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER,
                chat_id INTEGER,
                target_input TEXT,
                media_type TEXT,
                file_path TEXT,
                file_size INTEGER,
                caption TEXT,
                ocr_text TEXT,
                whisper_text TEXT,
                captured_at TEXT
            )
        """)
        
        # جدول الرسائل المحذوفة
        c.execute("""
            CREATE TABLE IF NOT EXISTS deleted_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER,
                chat_id INTEGER,
                target_input TEXT,
                content TEXT,
                deleted_at TEXT
            )
        """)
        
        # جدول الرسائل المعدلة
        c.execute("""
            CREATE TABLE IF NOT EXISTS edited_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER,
                chat_id INTEGER,
                old_text TEXT,
                new_text TEXT,
                edited_at TEXT
            )
        """)
        
        # جدول الكلمات المفتاحية
        c.execute("""
            CREATE TABLE IF NOT EXISTS keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_input TEXT,
                keyword TEXT,
                added_at TEXT
            )
        """)
        
        # جدول الجدولة
        c.execute("""
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_input TEXT,
                start_time TEXT,
                end_time TEXT,
                days TEXT,
                enabled BOOLEAN DEFAULT 1
            )
        """)
        
        # جدول السجلات
        c.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT,
                message TEXT,
                created_at TEXT
            )
        """)
        
        # جدول الإعدادات
        c.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        
        # جدول الإحصائيات
        c.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                messages_count INTEGER DEFAULT 0,
                media_count INTEGER DEFAULT 0,
                deleted_count INTEGER DEFAULT 0,
                edited_count INTEGER DEFAULT 0
            )
        """)
        
        self.conn.commit()
    
    # ====== الحسابات ======
    def add_account(self, phone, session_file, user_id, first_name, username):
        c = self.conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO accounts 
            (phone, session_file, user_id, first_name, username, added_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (phone, session_file, user_id, first_name, username, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_accounts(self):
        c = self.conn.cursor()
        c.execute("SELECT * FROM accounts ORDER BY id DESC")
        return [dict(r) for r in c.fetchall()]
    
    def get_account(self, phone):
        c = self.conn.cursor()
        c.execute("SELECT * FROM accounts WHERE phone = ?", (phone,))
        r = c.fetchone()
        return dict(r) if r else None
    
    def set_active_account(self, phone):
        c = self.conn.cursor()
        c.execute("UPDATE accounts SET is_active = 0")
        c.execute("UPDATE accounts SET is_active = 1 WHERE phone = ?", (phone,))
        self.conn.commit()
    
    def get_active_account(self):
        c = self.conn.cursor()
        c.execute("SELECT * FROM accounts WHERE is_active = 1")
        r = c.fetchone()
        return dict(r) if r else None
    
    def delete_account(self, phone):
        c = self.conn.cursor()
        c.execute("DELETE FROM accounts WHERE phone = ?", (phone,))
        c.execute("DELETE FROM targets WHERE account_phone = ?", (phone,))
        self.conn.commit()
    
    # ====== الأهداف ======
    def add_target(self, account_phone, target_input, target_id, target_name, target_type):
        c = self.conn.cursor()
        c.execute("""
            INSERT INTO targets (account_phone, target_input, target_id, target_name, target_type, added_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (account_phone, target_input, target_id, target_name, target_type, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_targets(self, account_phone):
        c = self.conn.cursor()
        c.execute("SELECT * FROM targets WHERE account_phone = ?", (account_phone,))
        return [dict(r) for r in c.fetchall()]
    
    def toggle_target(self, target_id):
        c = self.conn.cursor()
        c.execute("UPDATE targets SET enabled = NOT enabled WHERE id = ?", (target_id,))
        self.conn.commit()
    
    def delete_target(self, target_id):
        c = self.conn.cursor()
        c.execute("DELETE FROM targets WHERE id = ?", (target_id,))
        self.conn.commit()
    
    # ====== الوسائط ======
    def add_captured_media(self, message_id, chat_id, target_input, media_type, 
                          file_path, file_size, caption, ocr_text=None, whisper_text=None):
        c = self.conn.cursor()
        c.execute("""
            INSERT INTO captured_media 
            (message_id, chat_id, target_input, media_type, file_path, file_size, 
             caption, ocr_text, whisper_text, captured_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (message_id, chat_id, target_input, media_type, file_path, file_size,
              caption, ocr_text, whisper_text, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_captured_stats(self):
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) as total, SUM(file_size) as total_size FROM captured_media")
        return dict(c.fetchone())
    
    # ====== الرسائل المحذوفة ======
    def add_deleted_message(self, message_id, chat_id, target_input, content):
        c = self.conn.cursor()
        c.execute("""
            INSERT INTO deleted_messages (message_id, chat_id, target_input, content, deleted_at)
            VALUES (?, ?, ?, ?, ?)
        """, (message_id, chat_id, target_input, content, datetime.now().isoformat()))
        self.conn.commit()
    
    # ====== الرسائل المعدلة ======
    def add_edited_message(self, message_id, chat_id, old_text, new_text):
        c = self.conn.cursor()
        c.execute("""
            INSERT INTO edited_messages (message_id, chat_id, old_text, new_text, edited_at)
            VALUES (?, ?, ?, ?, ?)
        """, (message_id, chat_id, old_text, new_text, datetime.now().isoformat()))
        self.conn.commit()
    
    # ====== الكلمات المفتاحية ======
    def add_keyword(self, target_input, keyword):
        c = self.conn.cursor()
        c.execute("INSERT INTO keywords (target_input, keyword, added_at) VALUES (?, ?, ?)",
                  (target_input, keyword, datetime.now().isoformat()))
        self.conn.commit()
    
    def get_keywords(self, target_input):
        c = self.conn.cursor()
        c.execute("SELECT * FROM keywords WHERE target_input = ?", (target_input,))
        return [dict(r) for r in c.fetchall()]
    
    def delete_keyword(self, keyword_id):
        c = self.conn.cursor()
        c.execute("DELETE FROM keywords WHERE id = ?", (keyword_id,))
        self.conn.commit()
    
    # ====== السجلات ======
    def add_log(self, level, message):
        c = self.conn.cursor()
        c.execute("INSERT INTO logs (level, message, created_at) VALUES (?, ?, ?)",
                  (level, message, datetime.now().isoformat()))
        self.conn.commit()
        
        # حذف السجلات القديمة (آخر 1000)
        c.execute("""
            DELETE FROM logs WHERE id NOT IN (
                SELECT id FROM logs ORDER BY id DESC LIMIT 1000
            )
        """)
        self.conn.commit()
    
    def get_logs(self, limit=50):
        c = self.conn.cursor()
        c.execute("SELECT * FROM logs ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in c.fetchall()]
    
    # ====== الإحصائيات ======
    def update_daily_stats(self, stat_type):
        today = datetime.now().strftime("%Y-%m-%d")
        c = self.conn.cursor()
        c.execute("SELECT * FROM stats WHERE date = ?", (today,))
        row = c.fetchone()
        
        if row:
            c.execute(f"UPDATE stats SET {stat_type} = {stat_type} + 1 WHERE date = ?", (today,))
        else:
            c.execute(f"INSERT INTO stats (date, {stat_type}) VALUES (?, 1)", (today,))
        self.conn.commit()
    
    def get_week_stats(self):
        c = self.conn.cursor()
        c.execute("""
            SELECT * FROM stats 
            WHERE date >= date('now', '-7 days')
            ORDER BY date DESC
        """)
        return [dict(r) for r in c.fetchall()]
    
    # ====== الإعدادات ======
    def set_setting(self, key, value):
        c = self.conn.cursor()
        c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                  (key, str(value)))
        self.conn.commit()
    
    def get_setting(self, key, default=None):
        c = self.conn.cursor()
        c.execute("SELECT value FROM settings WHERE key = ?", (key,))
        r = c.fetchone()
        return r[0] if r else default

db = Database()
