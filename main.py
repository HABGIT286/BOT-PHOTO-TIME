import asyncio
import logging
from telethon import TelegramClient, events
from config import *
from database import db
from account_manager import account_manager
import bot_handlers
from bot_handlers import (
    start_cmd, callback_handler, message_handler, create_monitor
)

# إعداد السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, "bot.log"), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# البوت
bot_client = TelegramClient("bot_session", API_ID, API_HASH)

async def setup_bot():
    """إعداد البوت"""
    await bot_client.start(bot_token=BOT_TOKEN)
    bot_handlers.setup(bot_client, OWNER_ID)
    
    # تسجيل المعالجات
    bot_client.add_event_handler(
        start_cmd,
        events.NewMessage(pattern=r"^/start")
    )
    bot_client.add_event_handler(
        callback_handler,
        events.CallbackQuery()
    )
    bot_client.add_event_handler(
        message_handler,
        events.NewMessage()
    )
    
    logger.info("✅ البوت يعمل")

async def auto_connect():
    """الاتصال التلقائي بالحساب النشط"""
    active = db.get_active_account()
    if active:
        client = await account_manager.connect_account(active["phone"])
        if client:
            logger.info(f"✅ تم الاتصال بـ {active['phone']}")
            await create_monitor()

async def daily_report_task():
    """مهمة التقرير اليومي"""
    while True:
        try:
            now = datetime.now()
            target_hour = DAILY_REPORT_HOUR
            next_run = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
            if now >= next_run:
                next_run += timedelta(days=1)
            
            await asyncio.sleep((next_run - now).total_seconds())
            
            # إرسال التقرير
            week_stats = db.get_week_stats()
            if week_stats:
                today = week_stats[0]
                report = (
                    f"📊 **التقرير اليومي**\n\n"
                    f"📅 `{today['date']}`\n\n"
                    f"💬 رسائل: `{today['messages_count']}`\n"
                    f"📸 وسائط: `{today['media_count']}`\n"
                    f"🗑️ محذوفة: `{today['deleted_count']}`\n"
                    f"✏️ معدّلة: `{today['edited_count']}`"
                )
                await bot_client.send_message(OWNER_ID, report)
        
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"خطأ في التقرير: {e}")
            await asyncio.sleep(3600)

async def main():
    """الدالة الرئيسية"""
    print("🤖 بدء تشغيل البوت...")
    
    await setup_bot()
    await auto_connect()
    
    # بدء المهام الخلفية
    tasks = [
        asyncio.create_task(bot_client.run_until_disconnected()),
        asyncio.create_task(daily_report_task()),
    ]
    
    print("\n⚡ البوت جاهز!")
    print(f"📁 عدد الحسابات: {len(db.get_accounts())}")
    
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        print("\n👋 جاري الإيقاف...")
        await account_manager.disconnect_all()
    except Exception as e:
        logger.error(f"خطأ فادح: {e}")

if __name__ == "__main__":
    try:
        bot_client.loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\n👋 تم الإيقاف")
