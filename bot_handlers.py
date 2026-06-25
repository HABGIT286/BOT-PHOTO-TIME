import os
import json
import shutil
import asyncio
import psutil
from datetime import datetime, timedelta
from telethon import events
from telethon.tl.custom import Button
from telethon.errors import (
    SessionPasswordNeededError, 
    PhoneCodeInvalidError,
    PasswordHashInvalidError
)
from config import *
from database import db
from account_manager import account_manager
from monitor import Monitor

# متغيرات عامة
bot_client = None
OWNER_ID_LOCAL = OWNER_ID
pending_logins = {}  # user_id -> {phone, client, phone_code_hash}
user_states = {}     # user_id -> state

def setup(bot, owner_id):
    global bot_client, OWNER_ID_LOCAL
    bot_client = bot
    OWNER_ID_LOCAL = owner_id

# ============ أدوات مساعدة ============
def check_auth(func):
    async def wrapper(event):
        if event.sender_id != OWNER_ID_LOCAL:
            await event.answer("⛔ غير مصرح", alert=True)
            return
        return await func(event)
    return wrapper

def main_menu():
    active = account_manager.get_active_account()
    active_text = f"\n✅ الحساب النشط: `{active['phone']}`" if active else ""
    
    return (
        f"🤖 **بوت المراقبة الشامل v5**\n\n"
        f"📊 الحسابات: `{len(db.get_accounts())}`"
        f"{active_text}\n\n"
        f"اختر من القائمة:",
        [
            [Button.inline("👥 الحسابات", b"menu_accounts"),
             Button.inline("🎯 الأهداف", b"menu_targets")],
            [Button.inline("📸 الوسائط", b"menu_media"),
             Button.inline("📊 التقارير", b"menu_reports")],
            [Button.inline("🔐 الأمان", b"menu_security"),
             Button.inline("⚙️ الإدارة", b"menu_admin")],
            [Button.inline("▶️ START", b"start_mon"),
             Button.inline("⏹️ STOP", b"stop_mon")],
        ]
    )

# ============ معالج /start ============
async def start_cmd(event):
    if event.sender_id != OWNER_ID_LOCAL:
        return
    text, buttons = main_menu()
    await event.respond(text, buttons=buttons)

# ============ معالج الأزرار الرئيسي ============
async def callback_handler(event):
    if event.sender_id != OWNER_ID_LOCAL:
        await event.answer("⛔ غير مصرح", alert=True)
        return
    
    data = event.data.decode()
    
    # ===== القائمة الرئيسية =====
    if data == "main_menu":
        text, buttons = main_menu()
        await event.edit(text, buttons=buttons)
    
    # ===== قائمة الحسابات =====
    elif data == "menu_accounts":
        accounts = db.get_accounts()
        active = account_manager.get_active_account()
        
        buttons = []
        for acc in accounts:
            mark = "✅" if active and acc["phone"] == active["phone"] else "📱"
            name = acc["first_name"] or "بدون اسم"
            text = f"{mark} {acc['phone']} - {name}"
            buttons.append([Button.inline(text[:60], f"acc_{acc['phone']}")])
        
        buttons.append([Button.inline("➕ تسجيل جديد", b"new_login")])
        buttons.append([Button.inline("↩️ رجوع", b"main_menu")])
        
        await event.edit(
            f"👥 **إدارة الحسابات**\n\nالعدد: `{len(accounts)}`",
            buttons=buttons
        )
    
    elif data.startswith("acc_"):
        phone = data[4:]
        account = db.get_account(phone)
        if not account:
            await event.answer("❌ الحساب غير موجود", alert=True)
            return
        
        buttons = [
            [Button.inline("🔗 اتصال", f"connect_{phone}")],
            [Button.inline("🗑️ حذف", f"delete_{phone}")],
            [Button.inline("↩️ رجوع", b"menu_accounts")],
        ]
        
        await event.edit(
            f"📱 **تفاصيل الحساب**\n\n"
            f"👤 الاسم: `{account['first_name']}`\n"
            f"📞 الهاتف: `{account['phone']}`\n"
            f"🆔 المعرف: `{account['user_id']}`\n"
            f"📛 اليوزر: `@{account['username'] or 'لا يوجد'}`\n"
            f"📅 أضيف: `{account['added_at'][:10]}`",
            buttons=buttons
        )
    
    elif data.startswith("connect_"):
        phone = data[8:]
        await event.answer("⏳ جاري الاتصال...")
        client = await account_manager.connect_account(phone)
        if client:
            # إعادة إنشاء المراقب
            global monitor
            from monitor import monitor as m
            if m:
                await m.stop()
            from bot_handlers import create_monitor
            await create_monitor()
            
            me = await client.get_me()
            await event.edit(
                f"✅ **تم الاتصال**\n\n"
                f"👤 `{me.first_name}`\n"
                f"📱 `{phone}`",
                buttons=[[Button.inline("↩️ رجوع", b"main_menu")]]
            )
        else:
            await event.edit("❌ فشل الاتصال", buttons=[[Button.inline("↩️ رجوع", b"menu_accounts")]])
    
    elif data.startswith("delete_"):
        phone = data[7:]
        user_states[event.sender_id] = {"action": "confirm_delete", "phone": phone}
        await event.edit(
            f"⚠️ **تأكيد الحذف**\n\n"
            f"هل تريد حذف الحساب `{phone}`؟\n"
            f"سيتم حذف الجلسة وجميع البيانات المرتبطة.",
            buttons=[
                [Button.inline("✅ نعم، احذف", f"confirm_del_{phone}")],
                [Button.inline("❌ إلغاء", b"menu_accounts")]
            ]
        )
    
    elif data.startswith("confirm_del_"):
        phone = data[12:]
        account_manager.delete_account(phone)
        await event.edit(
            f"✅ **تم حذف الحساب**\n\n`{phone}`",
            buttons=[[Button.inline("↩️ رجوع", b"menu_accounts")]]
        )
    
    # ===== تسجيل جديد =====
    elif data == "new_login":
        user_states[event.sender_id] = {"action": "waiting_phone"}
        await event.edit(
            "📱 **تسجيل حساب جديد**\n\n"
            "أرسل رقم الهاتف مع كود الدولة\n\n"
            "**مثال:**\n`+967712345678`\n`+966501234567`",
            buttons=[[Button.inline("↩️ إلغاء", b"main_menu")]]
        )
    
    # ===== قائمة الأهداف =====
    elif data == "menu_targets":
        active = account_manager.get_active_account()
        if not active:
            await event.answer("⚠️ اتصل بحساب أولاً!", alert=True)
            return
        
        targets = db.get_targets(active["phone"])
        buttons = []
        for t in targets:
            mark = "🟢" if t["enabled"] else "🔴"
            type_icon = {"user": "👤", "channel": "📢", "group": "👥"}.get(t["target_type"], "❓")
            text = f"{mark} {type_icon} {t['target_name'][:30]}"
            buttons.append([Button.inline(text, f"tgt_{t['id']}")])
        
        buttons.append([Button.inline("➕ إضافة هدف", b"add_target")])
        buttons.append([Button.inline("↩️ رجوع", b"main_menu")])
        
        await event.edit(
            f"🎯 **الأهداف**\n\nالعدد: `{len(targets)}/20`",
            buttons=buttons
        )
    
    elif data.startswith("tgt_"):
        target_id = int(data[4:])
        # جلب التفاصيل من DB
        c = db.conn.cursor()
        c.execute("SELECT * FROM targets WHERE id = ?", (target_id,))
        t = c.fetchone()
        if not t:
            await event.answer("❌ غير موجود", alert=True)
            return
        t = dict(t)
        
        buttons = [
            [Button.inline("🔄 تبديل", f"toggle_{target_id}")],
            [Button.inline("🔑 كلمات مفتاحية", f"kw_{target_id}")],
            [Button.inline("🗑️ حذف", f"deltgt_{target_id}")],
            [Button.inline("↩️ رجوع", b"menu_targets")],
        ]
        
        status = "🟢 مفعّل" if t["enabled"] else "🔴 معطّل"
        await event.edit(
            f"🎯 **تفاصيل الهدف**\n\n"
            f"📛 الاسم: `{t['target_name']}`\n"
            f"🔖 الإدخال: `{t['target_input']}`\n"
            f"📂 النوع: `{t['target_type']}`\n"
            f"📊 الحالة: {status}",
            buttons=buttons
        )
    
    elif data.startswith("toggle_"):
        target_id = int(data[7:])
        db.toggle_target(target_id)
        await event.answer("✅ تم التبديل")
        # إعادة تحميل المراقب
        from bot_handlers import create_monitor
        await create_monitor()
        await callback_handler.__wrapped__(event) if hasattr(callback_handler, '__wrapped__') else None
        # إعادة عرض القائمة
        event.data = b"menu_targets"
        await callback_handler(event)
    
    elif data.startswith("deltgt_"):
        target_id = int(data[7:])
        db.delete_target(target_id)
        from bot_handlers import create_monitor
        await create_monitor()
        await event.edit("✅ تم الحذف", buttons=[[Button.inline("↩️ رجوع", b"menu_targets")]])
    
    elif data == "add_target":
        user_states[event.sender_id] = {"action": "waiting_target"}
        await event.edit(
            "🎯 **إضافة هدف جديد**\n\n"
            "أرسل:\n"
            "• يوزر: `@username`\n"
            "• رابط: `t.me/username`\n"
            "• معرف رقمي: `123456789`\n"
            "• رابط قناة/مجموعة",
            buttons=[[Button.inline("↩️ إلغاء", b"menu_targets")]]
        )
    
    # ===== قائمة الوسائط =====
    elif data == "menu_media":
        stats = db.get_captured_stats()
        total = stats.get("total") or 0
        size = stats.get("total_size") or 0
        size_mb = size / (1024 * 1024)
        
        buttons = [
            [Button.inline("📁 عرض المجلد", b"show_folder")],
            [Button.inline("🧹 حذف القديم", b"cleanup_media")],
            [Button.inline("↩️ رجوع", b"main_menu")],
        ]
        
        await event.edit(
            f"📸 **الوسائط الملتقطة**\n\n"
            f"📊 العدد: `{total}`\n"
            f"💾 الحجم: `{size_mb:.2f} MB`",
            buttons=buttons
        )
    
    elif data == "cleanup_media":
        # حذف الملفات القديمة
        deleted = 0
        cutoff = datetime.now() - timedelta(days=AUTO_DELETE_DAYS) if AUTO_DELETE_DAYS > 0 else None
        if cutoff:
            for root, dirs, files in os.walk(CAPTURED_DIR):
                for f in files:
                    path = os.path.join(root, f)
                    try:
                        mtime = datetime.fromtimestamp(os.path.getmtime(path))
                        if mtime < cutoff:
                            os.remove(path)
                            deleted += 1
                    except:
                        pass
        
        await event.edit(
            f"✅ **تم التنظيف**\n\n🗑️ حُذف: `{deleted}` ملف",
            buttons=[[Button.inline("↩️ رجوع", b"main_menu")]]
        )
    
    # ===== التقارير =====
    elif data == "menu_reports":
        week_stats = db.get_week_stats()
        
        report = "📊 **تقرير الأسبوع**\n\n"
        total_msg = total_media = total_del = total_edit = 0
        
        for s in week_stats:
            report += f"📅 `{s['date']}`: "
            report += f"💬{s['messages_count']} "
            report += f"📸{s['media_count']} "
            report += f"🗑️{s['deleted_count']} "
            report += f"✏️{s['edited_count']}\n"
            total_msg += s['messages_count']
            total_media += s['media_count']
            total_del += s['deleted_count']
            total_edit += s['edited_count']
        
        report += f"\n**الإجمالي:**\n"
        report += f"💬 رسائل: `{total_msg}`\n"
        report += f"📸 وسائط: `{total_media}`\n"
        report += f"🗑️ محذوفة: `{total_del}`\n"
        report += f"✏️ معدّلة: `{total_edit}`"
        
        buttons = [
            [Button.inline("📥 تصدير JSON", b"export_json")],
            [Button.inline("📋 السجلات", b"view_logs")],
            [Button.inline("↩️ رجوع", b"main_menu")],
        ]
        
        await event.edit(report, buttons=buttons)
    
    elif data == "export_json":
        # تصدير البيانات
        export = {
            "accounts": db.get_accounts(),
            "stats": db.get_week_stats(),
            "logs": db.get_logs(100),
            "exported_at": datetime.now().isoformat()
        }
        
        export_path = os.path.join(BACKUP_DIR, f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(export, f, ensure_ascii=False, indent=2, default=str)
        
        await bot_client.send_file(
            OWNER_ID_LOCAL, export_path,
            caption="📥 **نسخة احتياطية**"
        )
        await event.edit("✅ تم التصدير", buttons=[[Button.inline("↩️ رجوع", b"main_menu")]])
    
    elif data == "view_logs":
        logs = db.get_logs(20)
        text = "📋 **آخر السجلات**\n\n"
        for log in logs:
            icon = {"INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌"}.get(log["level"], "•")
            text += f"{icon} `{log['created_at'][11:19]}` - {log['message'][:50]}\n"
        
        await event.edit(
            text,
            buttons=[[Button.inline("↩️ رجوع", b"main_menu")]]
        )
    
    # ===== الأمان =====
    elif data == "menu_security":
        buttons = [
            [Button.inline("🔑 كلمة مرور البوت", b"set_bot_pass")],
            [Button.inline("🔒 تشفير الملفات", b"toggle_encrypt")],
            [Button.inline("👻 وضع التخفي", b"toggle_stealth")],
            [Button.inline("⏰ حذف تلقائي", b"set_auto_delete")],
            [Button.inline("↩️ رجوع", b"main_menu")],
        ]
        
        await event.edit(
            "🔐 **إعدادات الأمان**\n\n"
            f"🔒 التشفير: `{'مفعّل' if ENCRYPT_FILES else 'معطّل'}`\n"
            f"👻 التخفي: `{'مفعّل' if STEALTH_MODE else 'معطّل'}`\n"
            f"⏰ الحذف التلقائي: `{AUTO_DELETE_DAYS} يوم`",
            buttons=buttons
        )
    
    elif data == "toggle_stealth":
        import config
        config.STEALTH_MODE = not config.STEALTH_MODE
        db.set_setting("stealth_mode", config.STEALTH_MODE)
        await event.answer(f"👻 التخفي: {'مفعّل' if config.STEALTH_MODE else 'معطّل'}")
    
    elif data == "toggle_encrypt":
        import config
        config.ENCRYPT_FILES = not config.ENCRYPT_FILES
        db.set_setting("encrypt_files", config.ENCRYPT_FILES)
        await event.answer(f"🔒 التشفير: {'مفعّل' if config.ENCRYPT_FILES else 'معطّل'}")
    
    elif data == "set_auto_delete":
        user_states[event.sender_id] = {"action": "set_auto_delete"}
        await event.edit(
            "⏰ **الحذف التلقائي**\n\n"
            "أرسل عدد الأيام (0 للتعطيل)\n\n"
            "**مثال:** `30`",
            buttons=[[Button.inline("↩️ إلغاء", b"menu_security")]]
        )
    
    # ===== الإدارة =====
    elif data == "menu_admin":
        # معلومات النظام
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent
        
        buttons = [
            [Button.inline("🔄 إعادة تشغيل", b"restart_bot")],
            [Button.inline("💾 نسخة احتياطية", b"full_backup")],
            [Button.inline("📥 استعادة", b"restore_backup")],
            [Button.inline("💻 Terminal", b"terminal_mode")],
            [Button.inline("↩️ رجوع", b"main_menu")],
        ]
        
        await event.edit(
            f"⚙️ **الإدارة**\n\n"
            f"💻 CPU: `{cpu}%`\n"
            f"🧠 RAM: `{ram}%`\n"
            f"💾 Disk: `{disk}%`",
            buttons=buttons
        )
    
    elif data == "restart_bot":
        await event.edit("🔄 جاري إعادة التشغيل...")
        await account_manager.disconnect_all()
        import sys
        import os
        os.execl(sys.executable, sys.executable, *sys.argv)
    
    elif data == "full_backup":
        backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_path = os.path.join(BACKUP_DIR, backup_name)
        shutil.make_archive(backup_path, 'zip', BASE_DIR)
        
        await bot_client.send_file(
            OWNER_ID_LOCAL,
            backup_path + ".zip",
            caption=f"💾 **نسخة احتياطية كاملة**\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        await event.edit("✅ تم إرسال النسخة", buttons=[[Button.inline("↩️ رجوع", b"main_menu")]])
    
    elif data == "terminal_mode":
        user_states[event.sender_id] = {"action": "terminal"}
        await event.edit(
            "💻 **وضع Terminal**\n\n"
            "أرسل أي أمر لتنفيذه\n\n"
            "⚠️ **تحذير:** استخدم بحذر!",
            buttons=[[Button.inline("❌ خروج", b"main_menu")]]
        )
    
    # ===== START / STOP =====
    elif data == "start_mon":
        from bot_handlers import create_monitor, monitor
        if not account_manager.get_active_client():
            await event.answer("⚠️ اتصل بحساب أولاً!", alert=True)
            return
        
        targets = db.get_targets(account_manager.get_active_account()["phone"])
        enabled = [t for t in targets if t["enabled"]]
        if not enabled:
            await event.answer("⚠️ أضف أهدافاً أولاً!", alert=True)
            return
        
        await create_monitor()
        if monitor:
            success = await monitor.start()
            if success:
                await event.edit(
                    f"▶️ **بدأت المراقبة**\n\n"
                    f"🎯 الأهداف: `{len(enabled)}`\n"
                    f"⚡ المراقبة نشطة",
                    buttons=[[Button.inline("↩️ رجوع", b"main_menu")]]
                )
            else:
                await event.edit("❌ فشل بدء المراقبة", buttons=[[Button.inline("↩️ رجوع", b"main_menu")]])
    
    elif data == "stop_mon":
        from bot_handlers import monitor
        if monitor:
            await monitor.stop()
        await event.edit("⏹️ **تم إيقاف المراقبة**", buttons=[[Button.inline("↩️ رجوع", b"main_menu")]])

# ============ معالج الرسائل النصية ============
async def message_handler(event):
    if event.sender_id != OWNER_ID_LOCAL:
        return
    if event.text.startswith("/"):
        return
    
    text = event.text.strip()
    state = user_states.get(event.sender_id)
    
    if not state:
        return
    
    action = state.get("action")
    
    # ===== إدخال رقم الهاتف =====
    if action == "waiting_phone":
        if not text.startswith("+"):
            await event.respond("❌ يجب أن يبدأ بـ `+`")
            return
        
        await event.respond("⏳ جاري إرسال الكود...")
        
        try:
            client, phone_code_hash = await account_manager.send_code(text)
            pending_logins[event.sender_id] = {
                "phone": text,
                "client": client,
                "phone_code_hash": phone_code_hash
            }
            user_states[event.sender_id] = {"action": "waiting_code"}
            
            await event.respond(
                f"✅ **تم إرسال الكود إلى**\n📱 `{text}`\n\n"
                "📩 أرسل كود التحقق الآن",
                buttons=[[Button.inline("↩️ إلغاء", b"main_menu")]]
            )
        except Exception as e:
            await event.respond(f"❌ خطأ:\n`{e}`")
            user_states.pop(event.sender_id, None)
    
    # ===== إدخال كود التحقق =====
    elif action == "waiting_code":
        login = pending_logins.get(event.sender_id)
        if not login:
            await event.respond("❌ انتهت الجلسة، ابدأ من جديد")
            user_states.pop(event.sender_id, None)
            return
        
        code = text.replace(" ", "")
        await event.respond("⏳ جاري التحقق...")
        
        try:
            result = await account_manager.verify_code(
                login["client"], login["phone"], code, login["phone_code_hash"]
            )
            
            if result == "2FA_REQUIRED":
                user_states[event.sender_id] = {"action": "waiting_2fa"}
                await event.respond(
                    "🔐 **الحساب محمي بـ 2FA**\n\n"
                    "📝 **اكتب رمز 2FA الآن**",
                    buttons=[[Button.inline("↩️ إلغاء", b"main_menu")]]
                )
            else:
                pending_logins.pop(event.sender_id, None)
                user_states.pop(event.sender_id, None)
                
                await event.respond(
                    f"✅ **تم تسجيل الدخول!**\n\n"
                    f"👤 `{result['first_name']}`\n"
                    f"📱 `{result['phone']}`",
                    buttons=[[Button.inline("↩️ رجوع", b"main_menu")]]
                )
                
                # إعادة إنشاء المراقب
                await create_monitor()
        
        except PhoneCodeInvalidError:
            await event.respond("❌ كود غير صحيح، حاول مرة أخرى")
        except Exception as e:
            await event.respond(f"❌ خطأ:\n`{e}`")
    
    # ===== إدخال 2FA =====
    elif action == "waiting_2fa":
        login = pending_logins.get(event.sender_id)
        if not login:
            user_states.pop(event.sender_id, None)
            return
        
        await event.respond("⏳ جاري التحقق...")
        
        try:
            result = await account_manager.verify_2fa(login["client"], login["phone"], text)
            pending_logins.pop(event.sender_id, None)
            user_states.pop(event.sender_id, None)
            
            await event.respond(
                f"✅ **تم تسجيل الدخول!**\n\n"
                f"👤 `{result['first_name']}`\n"
                f"📱 `{result['phone']}`",
                buttons=[[Button.inline("↩️ رجوع", b"main_menu")]]
            )
            await create_monitor()
        
        except PasswordHashInvalidError:
            await event.respond("❌ كلمة مرور خاطئة، حاول مرة أخرى")
        except Exception as e:
            await event.respond(f"❌ خطأ:\n`{e}`")
    
    # ===== إدخال هدف =====
    elif action == "waiting_target":
        await event.respond("⏳ جاري الإضافة...")
        from bot_handlers import monitor
        if not monitor:
            await event.respond("❌ المراقب غير جاهز")
            user_states.pop(event.sender_id, None)
            return
        
        success, msg = await monitor.add_target(text)
        user_states.pop(event.sender_id, None)
        await event.respond(msg, buttons=[[Button.inline("↩️ رجوع", b"menu_targets")]])
    
    # ===== حذف تلقائي =====
    elif action == "set_auto_delete":
        try:
            days = int(text)
            import config
            config.AUTO_DELETE_DAYS = days
            db.set_setting("auto_delete_days", days)
            user_states.pop(event.sender_id, None)
            await event.respond(
                f"✅ تم تعيين الحذف التلقائي: `{days} يوم`" + (" (معطّل)" if days == 0 else ""),
                buttons=[[Button.inline("↩️ رجوع", b"main_menu")]]
            )
        except:
            await event.respond("❌ أدخل رقماً صحيحاً")
    
    # ===== Terminal =====
    elif action == "terminal":
        if text.lower() == "exit":
            user_states.pop(event.sender_id, None)
            await event.respond("✅ خرجت من Terminal", buttons=[[Button.inline("↩️ رجوع", b"main_menu")]])
            return
        
        try:
            proc = await asyncio.create_subprocess_shell(
                text,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            output = stdout.decode() if stdout else ""
            error = stderr.decode() if stderr else ""
            
            result = ""
            if output:
                result += f"📤 **Output:**\n```\n{output[:3500]}\n```\n"
            if error:
                result += f"⚠️ **Error:**\n```\n{error[:1000]}\n```"
            if not result:
                result = "✅ تم التنفيذ (لا يوجد ناتج)"
            
            await event.respond(result[:4000])
        except Exception as e:
            await event.respond(f"❌ خطأ:\n`{e}`")

# ============ إنشاء المراقب ============
async def create_monitor():
    global monitor
    from monitor import Monitor
    monitor = Monitor(account_manager, bot_client, OWNER_ID_LOCAL)
