import asyncio
from datetime import datetime
from telethon import events
from telethon.tl.types import (
    Channel, Chat, User, 
    UpdateDeleteChannelMessages, UpdateDeleteMessages,
    UpdateEditChannelMessage, UpdateEditMessage
)
from database import db
from media_handler import media_handler

class Monitor:
    def __init__(self, account_manager, bot_client, owner_id):
        self.account_manager = account_manager
        self.bot_client = bot_client
        self.owner_id = owner_id
        self.running = False
        self.monitored_chats = {}  # chat_id -> target_input
        self.keywords = {}  # target_input -> [keywords]
        self.status_check_task = None
    
    async def start(self):
        """بدء المراقبة"""
        self.running = True
        account = self.account_manager.get_active_account()
        if not account:
            return False
        
        client = self.account_manager.get_active_client()
        if not client:
            return False
        
        # تحميل الأهداف
        targets = db.get_targets(account["phone"])
        for t in targets:
            if t["enabled"]:
                self.monitored_chats[t["target_id"]] = t["target_input"]
                # تحميل الكلمات المفتاحية
                kws = db.get_keywords(t["target_input"])
                self.keywords[t["target_input"]] = [k["keyword"] for k in kws]
        
        # إضافة المعالجات
        client.remove_event_handler(self._on_new_message)
        client.remove_event_handler(self._on_delete)
        client.remove_event_handler(self._on_edit)
        
        client.add_event_handler(self._on_new_message, events.NewMessage(incoming=True))
        client.add_event_handler(self._on_delete, events.MessageDeleted())
        client.add_event_handler(self._on_edit, events.MessageEdited())
        
        # بدء فحص الحالة
        if self.status_check_task is None:
            self.status_check_task = asyncio.create_task(self._status_checker())
        
        db.add_log("INFO", f"بدأت المراقبة - {len(self.monitored_chats)} أهداف")
        return True
    
    async def stop(self):
        """إيقاف المراقبة"""
        self.running = False
        client = self.account_manager.get_active_client()
        if client:
            client.remove_event_handler(self._on_new_message)
            client.remove_event_handler(self._on_delete)
            client.remove_event_handler(self._on_edit)
        
        if self.status_check_task:
            self.status_check_task.cancel()
            self.status_check_task = None
        
        self.monitored_chats.clear()
        self.keywords.clear()
        db.add_log("INFO", "تم إيقاف المراقبة")
    
    async def _on_new_message(self, event):
        """معالجة الرسائل الجديدة"""
        if not self.running:
            return
        
        if event.chat_id not in self.monitored_chats:
            return
        
        target_input = self.monitored_chats[event.chat_id]
        msg = event.message
        
        db.update_daily_stats("messages_count")
        
        # فلترة الكلمات المفتاحية
        if target_input in self.keywords and self.keywords[target_input]:
            text = (msg.text or "").lower()
            matched = any(kw.lower() in text for kw in self.keywords[target_input])
            if not matched and not msg.media:
                return
        
        # معالجة الوسائط
        if msg.media and media_handler.is_temporary_media(msg):
            print(f"🔔 وسائط مؤقتة من {target_input}")
            await media_handler.capture(
                msg, target_input, self.bot_client, self.owner_id
            )
        
        # حفظ النص إذا كان مهماً (اختياري)
        elif msg.text and len(msg.text) > 0:
            # يمكن حفظ الرسائل النصية هنا
            pass
    
    async def _on_delete(self, event):
        """معالجة الرسائل المحذوفة"""
        if not self.running:
            return
        
        client = self.account_manager.get_active_client()
        if not client:
            return
        
        # الحصول على معرف المحادثة
        chat_id = getattr(event, 'chat_id', None)
        if not chat_id:
            return
        
        if chat_id not in self.monitored_chats:
            return
        
        target_input = self.monitored_chats[chat_id]
        
        for msg_id in event.deleted_ids:
            # محاولة جلب الرسالة من الكاش
            try:
                msg = await client.get_messages(chat_id, ids=msg_id)
                content = ""
                if msg:
                    content = msg.text or f"[{media_handler.get_media_type(msg)}]"
                
                db.add_deleted_message(msg_id, chat_id, target_input, content[:500])
                db.update_daily_stats("deleted_count")
                
                # إشعار المالك
                await self.bot_client.send_message(
                    self.owner_id,
                    f"🗑️ **رسالة محذوفة**\n\n"
                    f"🎯 الهدف: `{target_input}`\n"
                    f"🆔 معرّف الرسالة: `{msg_id}`\n"
                    f"📝 المحتوى: `{content[:200] or 'وسائط'}`\n"
                    f"🕒 الوقت: `{datetime.now().strftime('%H:%M:%S')}`"
                )
            except Exception as e:
                print(f"خطأ في معالجة الحذف: {e}")
    
    async def _on_edit(self, event):
        """معالجة الرسائل المعدلة"""
        if not self.running:
            return
        
        if event.chat_id not in self.monitored_chats:
            return
        
        target_input = self.monitored_chats[event.chat_id]
        msg = event.message
        
        # جلب النسخة الأصلية من قاعدة البيانات (إن وُجدت)
        old_text = ""  # في الإصدار الكامل، نحفظ النسخ السابقة
        
        new_text = msg.text or ""
        
        db.add_edited_message(msg.id, event.chat_id, old_text, new_text[:500])
        db.update_daily_stats("edited_count")
        
        # إشعار المالك
        await self.bot_client.send_message(
            self.owner_id,
            f"✏️ **رسالة معدّلة**\n\n"
            f"🎯 الهدف: `{target_input}`\n"
            f"🆔 معرّف الرسالة: `{msg.id}`\n"
            f"📝 النص الجديد:\n```\n{new_text[:300]}\n```"
        )
    
    async def _status_checker(self):
        """فحص حالة الأهداف (آخر ظهور)"""
        while self.running:
            try:
                await asyncio.sleep(300)  # كل 5 دقائق
                client = self.account_manager.get_active_client()
                if not client:
                    continue
                
                for chat_id, target_input in list(self.monitored_chats.items()):
                    try:
                        entity = await client.get_entity(chat_id)
                        if isinstance(entity, User):
                            status = entity.status
                            if status:
                                status_text = self._format_status(status)
                                # يمكن حفظ الحالة وإرسال إشعار عند التغير
                    except:
                        pass
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"خطأ في فحص الحالة: {e}")
                await asyncio.sleep(60)
    
    def _format_status(self, status):
        from telethon.tl.types import (
            UserStatusOnline, UserStatusOffline, 
            UserStatusRecently, UserStatusLastWeek, UserStatusLastMonth
        )
        if isinstance(status, UserStatusOnline):
            return "🟢 متصل الآن"
        elif isinstance(status, UserStatusOffline):
            return f"🔴 آخر ظهور: {status.was_online}"
        elif isinstance(status, UserStatusRecently):
            return "🟡 آخر ظهور مؤخراً"
        elif isinstance(status, UserStatusLastWeek):
            return "🟠 آخر ظهور خلال الأسبوع"
        elif isinstance(status, UserStatusLastMonth):
            return "⚪ آخر ظهور خلال الشهر"
        return "غير معروف"
    
    async def add_target(self, target_input):
        """إضافة هدف جديد"""
        account = self.account_manager.get_active_account()
        client = self.account_manager.get_active_client()
        if not account or not client:
            return False, "لا يوجد حساب نشط"
        
        targets = db.get_targets(account["phone"])
        if len(targets) >= 20:
            return False, "وصلت للحد الأقصى (20 هدف)"
        
        try:
            entity = await client.get_entity(target_input)
            
            # تحديد نوع الهدف
            if isinstance(entity, Channel):
                target_type = "channel" if entity.broadcast else "group"
                target_name = entity.title
            elif isinstance(entity, Chat):
                target_type = "group"
                target_name = entity.title
            elif isinstance(entity, User):
                target_type = "user"
                target_name = f"{entity.first_name or ''} {entity.last_name or ''}".strip()
            else:
                target_type = "unknown"
                target_name = target_input
            
            db.add_target(
                account_phone=account["phone"],
                target_input=target_input,
                target_id=entity.id,
                target_name=target_name,
                target_type=target_type
            )
            
            # إضافة للمراقبة الفورية
            self.monitored_chats[entity.id] = target_input
            self.keywords[target_input] = []
            
            db.add_log("INFO", f"تمت إضافة هدف: {target_input} ({target_type})")
            return True, f"✅ {target_name} ({target_type})"
            
        except Exception as e:
            return False, f"❌ {e}"

monitor = None  # سيتم إنشاؤه لاحقاً
