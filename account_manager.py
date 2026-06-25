import os
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from database import db
from config import API_ID, API_HASH, SESSIONS_DIR, STEALTH_MODE

class AccountManager:
    def __init__(self):
        self.clients = {}  # phone -> TelegramClient
        self.active_phone = None
    
    def get_session_path(self, phone):
        safe_phone = phone.replace("+", "").replace(" ", "")
        return os.path.join(SESSIONS_DIR, f"session_{safe_phone}")
    
    def create_client(self, phone):
        session_path = self.get_session_path(phone)
        return TelegramClient(session_path, API_ID, API_HASH)
    
    async def connect_account(self, phone):
        """الاتصال بحساب محفوظ"""
        account = db.get_account(phone)
        if not account:
            return None
        
        client = self.create_client(phone)
        try:
            await client.connect()
            if await client.is_user_authorized():
                self.clients[phone] = client
                self.active_phone = phone
                db.set_active_account(phone)
                
                # وضع التخفي
                if STEALTH_MODE:
                    try:
                        from telethon.tl.functions.account import UpdatePrivacyRequest
                        from telethon.tl.types import InputPrivacyKeyStatusTimestamp, InputPrivacyValueDisallowAll
                        # هذا اختياري
                    except:
                        pass
                
                return client
        except Exception as e:
            print(f"فشل الاتصال بـ {phone}: {e}")
            return None
    
    async def disconnect_all(self):
        for client in self.clients.values():
            try:
                await client.disconnect()
            except:
                pass
    
    def get_active_client(self):
        if self.active_phone and self.active_phone in self.clients:
            return self.clients[self.active_phone]
        return None
    
    def get_active_account(self):
        return db.get_active_account()
    
    async def send_code(self, phone):
        """إرسال كود التحقق"""
        client = self.create_client(phone)
        await client.connect()
        result = await client.send_code_request(phone)
        return client, result.phone_code_hash
    
    async def verify_code(self, client, phone, code, phone_code_hash):
        """التحقق من الكود"""
        try:
            await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
            return await self._finalize_login(client, phone)
        except SessionPasswordNeededError:
            return "2FA_REQUIRED"
    
    async def verify_2fa(self, client, phone, password):
        """التحقق من كلمة المرور الثنائية"""
        await client.sign_in(password=password)
        return await self._finalize_login(client, phone)
    
    async def _finalize_login(self, client, phone):
        """حفظ الحساب بعد نجاح الدخول"""
        me = await client.get_me()
        session_file = self.get_session_path(phone)
        
        db.add_account(
            phone=phone,
            session_file=session_file,
            user_id=me.id,
            first_name=me.first_name or "",
            username=me.username or ""
        )
        
        self.clients[phone] = client
        self.active_phone = phone
        db.set_active_account(phone)
        
        db.add_log("INFO", f"تم تسجيل دخول: {phone} - {me.first_name}")
        
        return {
            "user_id": me.id,
            "first_name": me.first_name,
            "username": me.username,
            "phone": phone
        }
    
    def delete_account(self, phone):
        """حذف حساب"""
        if phone in self.clients:
            try:
                self.clients[phone].disconnect()
            except:
                pass
            del self.clients[phone]
        
        # حذف ملف الجلسة
        session_path = self.get_session_path(phone)
        if os.path.exists(session_path):
            os.remove(session_path)
        
        db.delete_account(phone)
        db.add_log("INFO", f"تم حذف الحساب: {phone}")

account_manager = AccountManager()
