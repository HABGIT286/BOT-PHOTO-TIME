import os
import time
import sqlite3
import asyncio

import discord
from discord import app_commands
from discord.ext import commands

# =========================================================
# الإعدادات
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

# عدد مرات المنشن المسموحة لكل عضو خلال الساعة
MAX_USES = 3

# مدة الحماية: ساعة واحدة
WINDOW_SECONDS = 60 * 60

# اسم قاعدة البيانات
DB_FILE = "everywhere.sqlite3"


# =========================================================
# قاعدة البيانات
# =========================================================

db = sqlite3.connect(DB_FILE, check_same_thread=False)
db.row_factory = sqlite3.Row

db.execute("""
CREATE TABLE IF NOT EXISTS mention_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    mention_type TEXT NOT NULL,
    used_at REAL NOT NULL
)
""")

db.execute("""
CREATE INDEX IF NOT EXISTS idx_mention_usage
ON mention_usage(guild_id, user_id, used_at)
""")

db.commit()

db_lock = asyncio.Lock()


# =========================================================
# Discord Intents
# =========================================================

intents = discord.Intents.default()
intents.guilds = True


# =========================================================
# Bot
# =========================================================

class EverywhereBot(commands.Bot):

    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        # مزامنة Slash Commands
        synced = await self.tree.sync()
        print(f"✅ تم مزامنة {len(synced)} أمر/أوامر")

    async def on_ready(self):
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"🤖 البوت: {self.user}")
        print(f"🆔 ID: {self.user.id}")
        print(f"🌐 السيرفرات: {len(self.guilds)}")
        print("🛡️ نظام حماية المنشن: يعمل")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


bot = EverywhereBot()


# =========================================================
# تنظيف الاستخدامات القديمة
# =========================================================

async def cleanup_old_usage(guild_id: int, user_id: int):
    now = time.time()
    limit = now - WINDOW_SECONDS

    db.execute(
        """
        DELETE FROM mention_usage
        WHERE guild_id = ?
        AND user_id = ?
        AND used_at < ?
        """,
        (guild_id, user_id, limit)
    )

    db.commit()


# =========================================================
# الحصول على عدد الاستخدامات
# =========================================================

async def get_usage(guild_id: int, user_id: int):

    now = time.time()
    limit = now - WINDOW_SECONDS

    cursor = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM mention_usage
        WHERE guild_id = ?
        AND user_id = ?
        AND used_at >= ?
        """,
        (guild_id, user_id, limit)
    )

    row = cursor.fetchone()

    return int(row["total"])


# =========================================================
# تسجيل استخدام
# =========================================================

async def add_usage(
    guild_id: int,
    user_id: int,
    mention_type: str
):

    db.execute(
        """
        INSERT INTO mention_usage
        (guild_id, user_id, mention_type, used_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            guild_id,
            user_id,
            mention_type,
            time.time()
        )
    )

    db.commit()


# =========================================================
# معرفة وقت أقدم استخدام
# =========================================================

async def get_oldest_usage(guild_id: int, user_id: int):

    now = time.time()
    limit = now - WINDOW_SECONDS

    cursor = db.execute(
        """
        SELECT used_at
        FROM mention_usage
        WHERE guild_id = ?
        AND user_id = ?
        AND used_at >= ?
        ORDER BY used_at ASC
        LIMIT 1
        """,
        (guild_id, user_id, limit)
    )

    row = cursor.fetchone()

    if row is None:
        return None

    return float(row["used_at"])


# =========================================================
# التحقق من صلاحية البوت
# =========================================================

def bot_can_mention_everyone(guild: discord.Guild):

    me = guild.me

    if me is None:
        return False

    permissions = me.guild_permissions

    return permissions.mention_everyone


# =========================================================
# أمر /everywhere
# =========================================================

@bot.tree.command(
    name="everywhere",
    description="منشن جميع أعضاء السيرفر"
)
@app_commands.guild_only()
async def everywhere(interaction: discord.Interaction):

    guild = interaction.guild
    user = interaction.user

    if guild is None:
        return

    # =====================================================
    # التحقق من صلاحية البوت
    # =====================================================

    if not bot_can_mention_everyone(guild):

        await interaction.response.send_message(
            "❌ البوت لا يملك صلاحية **Mention @everyone, @here, and All Roles**.",
            ephemeral=True
        )

        return

    # =====================================================
    # قفل العملية لمنع التكرار السريع
    # =====================================================

    async with db_lock:

        await cleanup_old_usage(
            guild.id,
            user.id
        )

        used = await get_usage(
            guild.id,
            user.id
        )

        # =================================================
        # التحقق من الحد
        # =================================================

        if used >= MAX_USES:

            oldest = await get_oldest_usage(
                guild.id,
                user.id
            )

            if oldest:

                remaining = int(
                    WINDOW_SECONDS - (time.time() - oldest)
                )

                if remaining < 0:
                    remaining = 0

                minutes = remaining // 60
                seconds = remaining % 60

                await interaction.response.send_message(
                    "🛡️ **تم تفعيل نظام الحماية**\n\n"
                    f"❌ استنفدت الحد المسموح: **{MAX_USES}/{MAX_USES}**\n"
                    f"⏳ الاستخدام القادم متاح بعد: "
                    f"**{minutes} دقيقة و {seconds} ثانية**",
                    ephemeral=True
                )

                return

        # =================================================
        # تسجيل الاستخدام قبل الإرسال
        # =================================================

        await add_usage(
            guild.id,
            user.id,
            "everyone"
        )

    # =====================================================
    # إرسال المنشن
    # =====================================================

    try:

        await interaction.response.send_message(
            "@everyone",
            allowed_mentions=discord.AllowedMentions(
                everyone=True,
                users=False,
                roles=False,
                replied_user=False
            )
        )

    except discord.Forbidden:

        await interaction.followup.send(
            "❌ Discord رفض إرسال المنشن. "
            "تأكد من صلاحيات البوت في هذه القناة.",
            ephemeral=True
        )

    except discord.HTTPException:

        await interaction.followup.send(
            "❌ حدث خطأ أثناء إرسال المنشن.",
            ephemeral=True
        )


# =========================================================
# أمر /here
# =========================================================

@bot.tree.command(
    name="here",
    description="منشن الأعضاء المتواجدين"
)
@app_commands.guild_only()
async def here(interaction: discord.Interaction):

    guild = interaction.guild
    user = interaction.user

    if guild is None:
        return

    # =====================================================
    # التحقق من صلاحية البوت
    # =====================================================

    if not bot_can_mention_everyone(guild):

        await interaction.response.send_message(
            "❌ البوت لا يملك صلاحية "
            "**Mention @everyone, @here, and All Roles**.",
            ephemeral=True
        )

        return

    # =====================================================
    # حماية الاستخدام
    # =====================================================

    async with db_lock:

        await cleanup_old_usage(
            guild.id,
            user.id
        )

        used = await get_usage(
            guild.id,
            user.id
        )

        if used >= MAX_USES:

            oldest = await get_oldest_usage(
                guild.id,
                user.id
            )

            if oldest:

                remaining = int(
                    WINDOW_SECONDS - (time.time() - oldest)
                )

                if remaining < 0:
                    remaining = 0

                minutes = remaining // 60
                seconds = remaining % 60

                await interaction.response.send_message(
                    "🛡️ **تم تفعيل نظام الحماية**\n\n"
                    f"❌ استنفدت الحد المسموح: **{MAX_USES}/{MAX_USES}**\n"
                    f"⏳ الاستخدام القادم متاح بعد: "
                    f"**{minutes} دقيقة و {seconds} ثانية**",
                    ephemeral=True
                )

                return

        # تسجيل الاستخدام
        await add_usage(
            guild.id,
            user.id,
            "here"
        )

    # =====================================================
    # إرسال @here
    # =====================================================

    try:

        await interaction.response.send_message(
            "@here",
            allowed_mentions=discord.AllowedMentions(
                everyone=True,
                users=False,
                roles=False,
                replied_user=False
            )
        )

    except discord.Forbidden:

        await interaction.followup.send(
            "❌ Discord رفض إرسال المنشن. "
            "تأكد من صلاحيات البوت في هذه القناة.",
            ephemeral=True
        )

    except discord.HTTPException:

        await interaction.followup.send(
            "❌ حدث خطأ أثناء إرسال المنشن.",
            ephemeral=True
        )


# =========================================================
# أمر /mention_status
# معرفة عدد الاستخدامات المتبقية
# =========================================================

@bot.tree.command(
    name="mention_status",
    description="معرفة عدد مرات المنشن المتبقية"
)
@app_commands.guild_only()
async def mention_status(interaction: discord.Interaction):

    guild = interaction.guild
    user = interaction.user

    if guild is None:
        return

    async with db_lock:

        await cleanup_old_usage(
            guild.id,
            user.id
        )

        used = await get_usage(
            guild.id,
            user.id
        )

        remaining = max(
            0,
            MAX_USES - used
        )

    await interaction.response.send_message(
        "🛡️ **حالة نظام المنشن**\n\n"
        f"👤 العضو: {user.mention}\n"
        f"📊 الاستخدام: **{used}/{MAX_USES}**\n"
        f"✅ المتبقي: **{remaining}**\n"
        f"⏱️ الفترة: **ساعة متحركة**",
        ephemeral=True
    )


# =========================================================
# معالجة الأخطاء
# =========================================================

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):

    if interaction.response.is_done():

        await interaction.followup.send(
            "❌ حدث خطأ غير متوقع.",
            ephemeral=True
        )

    else:

        await interaction.response.send_message(
            "❌ حدث خطأ غير متوقع.",
            ephemeral=True
        )

    print(f"❌ Command Error: {repr(error)}")


# =========================================================
# تشغيل البوت
# =========================================================

if not TOKEN:

    raise RuntimeError(
        "❌ لم يتم العثور على DISCORD_TOKEN"
    )

bot.run(TOKEN)
