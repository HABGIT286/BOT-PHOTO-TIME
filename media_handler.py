import os
import asyncio
from datetime import datetime
from config import CAPTURED_DIR, COMPRESS_MEDIA, ENABLE_OCR, ENABLE_WHISPER, MAX_FILE_SIZE_MB
from database import db

# محاولة استيراد المكتبات الاختيارية
try:
    from PIL import Image
    PIL_AVAILABLE = True
except:
    PIL_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except:
    TESSERACT_AVAILABLE = False

try:
    import whisper
    WHISPER_AVAILABLE = True
    whisper_model = None
except:
    WHISPER_AVAILABLE = False

def get_whisper_model():
    global whisper_model
    if whisper_model is None and WHISPER_AVAILABLE:
        whisper_model = whisper.load_model("base")
    return whisper_model

class MediaHandler:
    def __init__(self):
        self.processed_ids = set()
    
    def is_temporary_media(self, msg):
        """كشف الوسائط المؤقتة"""
        if not msg.media:
            return False
        if msg.voice or msg.video_note:
            return True
        if getattr(msg, "ttl_period", None) and msg.ttl_period > 0:
            return True
        if hasattr(msg.media, "ttl_seconds") and msg.media.ttl_seconds:
            return True
        return False
    
    def get_media_type(self, msg):
        if msg.video or msg.video_note:
            return "video"
        if msg.voice:
            return "voice"
        if msg.audio:
            return "audio"
        if msg.photo:
            return "photo"
        if msg.sticker:
            return "sticker"
        if msg.document:
            return "document"
        return "file"
    
    def get_target_folder(self, target_input):
        """إنشاء مجلد للهدف"""
        safe_name = "".join(c if c.isalnum() else "_" for c in target_input)
        folder = os.path.join(CAPTURED_DIR, safe_name)
        os.makedirs(folder, exist_ok=True)
        return folder
    
    async def compress_image(self, path):
        """ضغط الصورة"""
        if not COMPRESS_MEDIA or not PIL_AVAILABLE:
            return path
        try:
            img = Image.open(path)
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            
            # تقليل الحجم إذا كان كبير
            max_size = (1920, 1920)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            compressed = path.replace(".png", ".jpg").replace(".webp", ".jpg")
            if not compressed.endswith(".jpg"):
                compressed += ".jpg"
            img.save(compressed, "JPEG", quality=85, optimize=True)
            
            if compressed != path:
                os.remove(path)
            return compressed
        except Exception as e:
            print(f"فشل ضغط الصورة: {e}")
            return path
    
    async def extract_text_from_image(self, path):
        """OCR - استخراج النص من الصورة"""
        if not ENABLE_OCR or not TESSERACT_AVAILABLE or not PIL_AVAILABLE:
            return None
        try:
            img = Image.open(path)
            # دعم العربية والإنجليزية
            text = pytesseract.image_to_string(img, lang='ara+eng')
            return text.strip() if text.strip() else None
        except Exception as e:
            print(f"فشل OCR: {e}")
            return None
    
    async def transcribe_audio(self, path):
        """تحويل الصوت لنص باستخدام Whisper"""
        if not ENABLE_WHISPER or not WHISPER_AVAILABLE:
            return None
        try:
            model = get_whisper_model()
            if model is None:
                return None
            result = model.transcribe(path, language=None)
            return result.get("text", "").strip() or None
        except Exception as e:
            print(f"فشل Whisper: {e}")
            return None
    
    async def capture(self, msg, target_input, bot_client, owner_id):
        """التقاط الوسائط ومعالجتها"""
        if msg.id in self.processed_ids:
            return False
        self.processed_ids.add(msg.id)
        
        if len(self.processed_ids) > 5000:
            self.processed_ids.clear()
        
        mtype = self.get_media_type(msg)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        folder = self.get_target_folder(target_input)
        
        # امتداد الملف
        ext_map = {
            "photo": ".jpg", "video": ".mp4", "voice": ".ogg",
            "audio": ".mp3", "document": ".bin", "sticker": ".webp", "file": ".bin"
        }
        ext = ext_map.get(mtype, ".bin")
        filename = f"{timestamp}_{msg.id}_{mtype}{ext}"
        save_path = os.path.join(folder, filename)
        
        try:
            # التنزيل
            downloaded = await msg.download_media(file=save_path)
            if not downloaded:
                return False
            
            file_size = os.path.getsize(downloaded)
            
            # معالجة خاصة حسب النوع
            ocr_text = None
            whisper_text = None
            
            if mtype == "photo":
                downloaded = await self.compress_image(downloaded)
                ocr_text = await self.extract_text_from_image(downloaded)
            
            elif mtype in ("voice", "audio"):
                whisper_text = await self.transcribe_audio(downloaded)
            
            # حفظ في قاعدة البيانات
            caption = msg.text or ""
            db.add_captured_media(
                message_id=msg.id,
                chat_id=msg.chat_id,
                target_input=target_input,
                media_type=mtype,
                file_path=downloaded,
                file_size=file_size,
                caption=caption[:500],
                ocr_text=ocr_text,
                whisper_text=whisper_text
            )
            
            db.update_daily_stats("media_count")
            
            # الإرسال للبوت
            await self._send_to_bot(downloaded, mtype, msg, target_input, 
                                   bot_client, owner_id, ocr_text, whisper_text)
            
            return True
            
        except Exception as e:
            print(f"❌ خطأ في التقاط الوسائط: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def _send_to_bot(self, file_path, mtype, msg, target_input, 
                          bot_client, owner_id, ocr_text=None, whisper_text=None):
        """إرسال الوسائط للبوت مع معلومات إضافية"""
        try:
            caption_parts = [
                f"📨 **وسائط مؤقتة تم حفظها**",
                f"🎯 الهدف: `{target_input}`",
                f"📂 النوع: `{mtype}`",
                f"🕒 الوقت: `{msg.date.strftime('%Y-%m-%d %H:%M:%S')}`",
            ]
            
            if ocr_text:
                caption_parts.append(f"\n📝 **النص المستخرج (OCR):**\n```\n{ocr_text[:500]}\n```")
            
            if whisper_text:
                caption_parts.append(f"\n🎤 **تفريغ الصوت:**\n```\n{whisper_text[:500]}\n```")
            
            caption = "\n".join(caption_parts)
            
            # تقسيم الكابشن إذا كان طويلاً
            if len(caption) > 1024:
                caption = caption[:1000] + "\n..."
            
            with open(file_path, "rb") as f:
                if mtype == "video":
                    await bot_client.send_file(
                        owner_id, f, caption=caption,
                        supports_streaming=True,
                        attributes=msg.document.attributes if msg.document else None
                    )
                elif mtype == "voice":
                    await bot_client.send_file(
                        owner_id, f, caption=caption,
                        voice_note=True,
                        attributes=msg.document.attributes if msg.document else None
                    )
                elif mtype == "sticker":
                    await bot_client.send_file(owner_id, f, caption=caption)
                else:
                    await bot_client.send_file(owner_id, f, caption=caption)
            
        except Exception as e:
            print(f"❌ فشل الإرسال: {e}")

media_handler = MediaHandler()
