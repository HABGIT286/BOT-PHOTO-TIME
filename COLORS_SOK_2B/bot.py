import os
import re
import sqlite3
import logging
import asyncio
from datetime import datetime, timezone

import discord
from discord.ext import commands
from discord import app_commands

DB = "colors_sok_2b.sqlite3"
IMAGE = "colors.png"

OWNER_USER_ID = 1531577881548034100
OWNER_CODE = "uefoxe1436"

# ضع التوكن الجديد هنا بعد عمل Reset للتوكن السابق:
TOKEN = "MTUzNjA3MjYxMjU2MjczNTMzOA.GjiJGD.seyFjOUNNPG_Gebq97dgG5_tA-RtHxoc0X-omM"

COLORS = [
    (1, "#FF1744", "أحمر نيون"), (2, "#D50000", "أحمر قوي"), (3, "#B71C1C", "أحمر داكن"), (4, "#FF5252", "أحمر فاتح"),
    (5, "#FF6D00", "برتقالي نيون"), (6, "#E65100", "برتقالي داكن"), (7, "#FF9100", "برتقالي"), (8, "#FFB300", "ذهبي برتقالي"),
    (9, "#FFD600", "أصفر نيون"), (10, "#F9A825", "أصفر ذهبي"), (11, "#F57F17", "أصفر داكن"), (12, "#FFF176", "أصفر فاتح"),
    (13, "#76FF03", "أخضر نيون"), (14, "#64DD17", "أخضر ليموني"), (15, "#00C853", "أخضر قوي"), (16, "#1B5E20", "أخضر داكن"),
    (17, "#00E676", "أخضر RGB"), (18, "#00BFA5", "تركوازي"), (19, "#009688", "تركوازي داكن"), (20, "#A7FFEB", "نعناعي"),
    (21, "#00E5FF", "سماوي نيون"), (22, "#00B8D4", "سماوي قوي"), (23, "#00838F", "سماوي داكن"), (24, "#80DEEA", "سماوي فاتح"),
    (25, "#2979FF", "أزرق نيون"), (26, "#2962FF", "أزرق قوي"), (27, "#1565C0", "أزرق داكن"), (28, "#82B1FF", "أزرق فاتح"),
    (29, "#3D5AFE", "نيلي نيون"), (30, "#304FFE", "نيلي قوي"), (31, "#1A237E", "نيلي داكن"), (32, "#8C9EFF", "نيلي فاتح"),
    (33, "#651FFF", "بنفسجي نيون"), (34, "#6200EA", "بنفسجي قوي"), (35, "#4527A0", "بنفسجي داكن"), (36, "#B388FF", "بنفسجي فاتح"),
    (37, "#D500F9", "فوشيا نيون"), (38, "#AA00FF", "أرجواني نيون"), (39, "#6A1B9A", "أرجواني داكن"), (40, "#EA80FC", "أرجواني فاتح"),
    (41, "#FF00FF", "ماجنتا"), (42, "#F50057", "وردي قوي"), (43, "#880E4F", "وردي داكن"), (44, "#FF80AB", "وردي فاتح"),
    (45, "#FF4081", "وردي نيون"), (46, "#C51162", "وردي عميق"), (47, "#AD1457", "كرزي داكن"), (48, "#FFCDD2", "وردي باهت"),
    (49, "#FFFFFF", "أبيض"), (50, "#F5F5F5", "رمادي فاتح جدًا"), (51, "#E0E0E0", "فضي فاتح"), (52, "#BDBDBD", "فضي"),
    (53, "#757575", "رمادي"), (54, "#424242", "رمادي داكن"), (55, "#212121", "فحمي"), (56, "#000000", "أسود"),
    (57, "#263238", "أزرق فحمي"), (58, "#37474F", "رمادي أزرق"), (59, "#455A64", "رمادي أزرق متوسط"), (60, "#546E7A", "رمادي أزرق فاتح"),
    (61, "#3E2723", "بني داكن"), (62, "#4E342E", "بني"), (63, "#5D4037", "بني متوسط"), (64, "#795548", "بني فاتح"),
    (65, "#FF3D00", "أحمر برتقالي"), (66, "#FF7043", "مرجاني"), (67, "#FF8A65", "مرجاني فاتح"), (68, "#BF360C", "نحاسي داكن"),
    (69, "#8BC34A", "ليموني"), (70, "#CDDC39", "ليموني أصفر"), (71, "#AFB42B", "زيتوني"), (72, "#827717", "زيتوني داكن"),
    (73, "#00ACC1", "سماوي متوسط"), (74, "#006064", "سماوي عميق"), (75, "#26C6DA", "سماوي فاتح قوي"), (76, "#4DD0E1", "سماوي ناعم"),
    (77, "#5E35B1", "بنفسجي متوسط"), (78, "#7E57C2", "بنفسجي ناعم"), (79, "#9575CD", "بنفسجي فاتح قوي"), (80, "#311B92", "بنفسجي عميق"),
    (81, "#EC407A", "وردي متوسط"), (82, "#E91E63", "وردي قوي 2"), (83, "#9C275A", "توتي داكن"), (84, "#F48FB1", "وردي ناعم"),
    (85, "#00FF9C", "RGB أخضر"), (86, "#00FFD5", "RGB تركوازي"), (87, "#00A2FF", "RGB أزرق"), (88, "#7A00FF", "RGB بنفسجي"),
    (89, "#FF00A8", "RGB وردي"), (90, "#FF0055", "RGB أحمر وردي"), (91, "#39FF14", "Lime Neon"), (92, "#B026FF", "Purple Neon"),
    (93, "#FFEA00", "Yellow Neon"), (94, "#00FFFF", "Cyan Neon"), (95, "#FF1493", "Deep Pink"), (96, "#7C4DFF", "Electric Violet"),
    (97, "#FF6B00", "Neon Orange"), (98, "#00FF66", "Neon Green"), (99, "#6B00FF", "Neon Purple"), (100, "#FF006B", "Neon Pink"),
]

logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

db = sqlite3.connect(DB, check_same_thread=False)
db.row_factory = sqlite3.Row


def init():
    db.execute("""CREATE TABLE IF NOT EXISTS settings(
        guild_id INTEGER PRIMARY KEY,
        members_on INTEGER DEFAULT 1,
        admins_on INTEGER DEFAULT 1,
        system_on INTEGER DEFAULT 1,
        log_channel INTEGER)""")
    db.execute("""CREATE TABLE IF NOT EXISTS roles(
        guild_id INTEGER,
        user_id INTEGER,
        role_id INTEGER,
        PRIMARY KEY(guild_id, user_id))""")
    db.commit()


def ensure(guild_id):
    db.execute("INSERT OR IGNORE INTO settings(guild_id) VALUES(?)", (guild_id,))
    db.commit()


def get_bool(guild_id, key):
    if key not in {"members_on", "admins_on", "system_on"}:
        raise ValueError("Invalid setting")
    ensure(guild_id)
    row = db.execute(f"SELECT {key} FROM settings WHERE guild_id=?", (guild_id,)).fetchone()
    return bool(row[key])


def put(guild_id, key, value):
    if key not in {"members_on", "admins_on", "system_on", "log_channel"}:
        raise ValueError("Invalid setting")
    ensure(guild_id)
    db.execute(f"UPDATE settings SET {key}=? WHERE guild_id=?", (int(value), guild_id))
    db.commit()


def get_log_channel(guild_id):
    ensure(guild_id)
    return db.execute("SELECT log_channel FROM settings WHERE guild_id=?", (guild_id,)).fetchone()["log_channel"]


def is_admin(member):
    return isinstance(member, discord.Member) and (
        member.guild.owner_id == member.id or member.guild_permissions.administrator
    )


def is_owner(user_id):
    return user_id == OWNER_USER_ID


def valid_hex(value):
    value = value.strip().upper()
    if not value.startswith("#"):
        value = "#" + value
    if re.fullmatch(r"#[0-9A-F]{6}", value):
        return value
    if re.fullmatch(r"#[0-9A-F]{3}", value):
        return "#" + "".join(c * 2 for c in value[1:])
    return None


def parse_color(value):
    value = value.strip()
    if value.isdigit():
        number = int(value)
        result = next(((h, n) for i, h, n in COLORS if i == number), None)
        if not result:
            raise ValueError("رقم اللون يجب أن يكون من 1 إلى 100.")
        h, name = result
        return f"COLOR {number:03d}", h, name

    h = valid_hex(value)
    if not h:
        raise ValueError("HEX غير صالح. مثال: #F11111 أو F11111.")
    return h, h, "HEX مخصص"


async def color_role(member):
    row = db.execute(
        "SELECT role_id FROM roles WHERE guild_id=? AND user_id=?",
        (member.guild.id, member.id)
    ).fetchone()

    role = member.guild.get_role(row["role_id"]) if row else None

    if role is None:
        role = await member.guild.create_role(
            name=f"COLOR • {member.display_name}"[:100],
            colour=discord.Colour.default(),
            reason="COLORS_SOK_2B personal color role"
        )
        db.execute(
            "INSERT OR REPLACE INTO roles(guild_id,user_id,role_id) VALUES(?,?,?)",
            (member.guild.id, member.id, role.id)
        )
        db.commit()

    return role


async def write_log(guild, member, old, new, who):
    channel_id = get_log_channel(guild.id)
    if not channel_id:
        return

    channel = guild.get_channel(channel_id)
    if not channel:
        return

    now = datetime.now(timezone.utc).astimezone()
    text = (
        "🎨 **COLOR LOG**\n\n"
        f"👤 **العضو:**\n{member.display_name}\n\n"
        f"🆔 **ID:**\n{member.id}\n\n"
        f"🔴 **اللون السابق:**\n{old}\n\n"
        f"🟢 **اللون الجديد:**\n{new}\n\n"
        f"👮 **بواسطة:**\n{who}\n\n"
        f"🕒 **الوقت:**\n{now.strftime('%Y/%m/%d %H:%M:%S')}"
    )
    try:
        await channel.send(text)
    except discord.HTTPException:
        pass


async def apply_color(member, value, who):
    label, hex_code, _ = parse_color(value)
    role = await color_role(member)
    old = role.name

    await role.edit(
        name=f"COLOR • {member.display_name}"[:100],
        colour=discord.Colour(int(hex_code[1:], 16)),
        reason="COLORS_SOK_2B"
    )

    if role not in member.roles:
        await member.add_roles(role, reason="COLORS_SOK_2B")

    await write_log(member.guild, member, old, label, who)
    return label, hex_code


@bot.tree.command(name="colors", description="عرض صورة الألوان")
async def colors_cmd(i: discord.Interaction):
    if not i.guild:
        return await i.response.send_message("❌ استخدمه داخل السيرفر.", ephemeral=True)
    if not get_bool(i.guild.id, "system_on"):
        return await i.response.send_message("⛔ النظام متوقف.", ephemeral=True)
    if not os.path.exists(IMAGE):
        return await i.response.send_message("❌ colors.png غير موجود بجانب bot.py.", ephemeral=True)

    await i.response.send_message(
        "🎨 أرسل رقم اللون 1-100 أو HEX مثل `#FF1744`.",
        file=discord.File(IMAGE)
    )


@bot.tree.command(name="setcolor", description="تغيير لون عضو - الإدارة")
@app_commands.describe(user_id="ID العضو المستهدف")
async def setcolor(i: discord.Interaction, user_id: str):
    if not i.guild:
        return await i.response.send_message("❌ داخل السيرفر فقط.", ephemeral=True)
    if not is_admin(i.user):
        return await i.response.send_message("❌ للإدارة فقط.", ephemeral=True)
    if not get_bool(i.guild.id, "admins_on"):
        return await i.response.send_message("⛔ إدارة البوت متوقفة.", ephemeral=True)
    if not user_id.isdigit():
        return await i.response.send_message("❌ ID غير صحيح.", ephemeral=True)

    member = i.guild.get_member(int(user_id))
    if member is None:
        try:
            member = await i.guild.fetch_member(int(user_id))
        except discord.HTTPException:
            member = None

    if member is None:
        return await i.response.send_message("❌ العضو غير موجود.", ephemeral=True)

    await i.response.send_message(
        f"👤 {member.mention}\n🎨 أرسل الآن رقم اللون 1-100 أو HEX.\n⏳ لديك 120 ثانية.",
        ephemeral=True
    )

    def check(message):
        return (
            message.author.id == i.user.id
            and message.channel.id == i.channel.id
            and message.guild is not None
            and message.guild.id == i.guild.id
        )

    try:
        msg = await bot.wait_for("message", timeout=120, check=check)
        label, hex_code = await apply_color(member, msg.content, i.user.display_name)

        try:
            await msg.delete()
        except discord.HTTPException:
            pass

        await i.followup.send(
            f"✅ تم تطبيق {label} `{hex_code}` على {member.mention}.",
            ephemeral=True
        )
    except asyncio.TimeoutError:
        await i.followup.send("⌛ انتهى الوقت.", ephemeral=True)
    except ValueError as e:
        await i.followup.send(f"❌ {e}", ephemeral=True)
    except discord.Forbidden:
        await i.followup.send("❌ البوت لا يملك صلاحيات إدارة الرتب.", ephemeral=True)
    except Exception:
        logging.exception("setcolor error")
        await i.followup.send("❌ حدث خطأ أثناء تطبيق اللون.", ephemeral=True)


class OwnerModal(discord.ui.Modal, title="SOKO_IDMIN"):
    code = discord.ui.TextInput(label="رمز المالك", required=True)

    async def on_submit(self, i: discord.Interaction):
        if not is_owner(i.user.id):
            return await i.response.send_message("❌ غير مصرح.", ephemeral=True)
        if str(self.code) != OWNER_CODE:
            return await i.response.send_message("❌ رمز غير صحيح.", ephemeral=True)
        if not i.guild:
            return await i.response.send_message("❌ داخل السيرفر فقط.", ephemeral=True)

        await i.response.send_message(
            "👑 **لوحة تحكم COLORS_SOK_2B**",
            view=OwnerView(),
            ephemeral=True
        )


class OwnerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    async def allowed(self, i):
        if not is_owner(i.user.id):
            await i.response.send_message("❌ غير مصرح.", ephemeral=True)
            return False
        if not i.guild:
            await i.response.send_message("❌ داخل السيرفر فقط.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🎨 الأعضاء", style=discord.ButtonStyle.primary)
    async def members(self, i, button):
        if not await self.allowed(i):
            return
        v = not get_bool(i.guild.id, "members_on")
        put(i.guild.id, "members_on", v)
        await i.response.send_message(
            "🟢 تغيير الألوان للأعضاء مفعّل." if v else "🔴 تغيير الألوان للأعضاء متوقف.",
            ephemeral=True
        )

    @discord.ui.button(label="👑 الإدارة", style=discord.ButtonStyle.secondary)
    async def admins(self, i, button):
        if not await self.allowed(i):
            return
        v = not get_bool(i.guild.id, "admins_on")
        put(i.guild.id, "admins_on", v)
        await i.response.send_message(
            "🟢 أوامر الإدارة مفعّلة." if v else "🔴 أوامر الإدارة متوقفة.",
            ephemeral=True
        )

    @discord.ui.button(label="🤖 النظام", style=discord.ButtonStyle.success)
    async def system(self, i, button):
        if not await self.allowed(i):
            return
        v = not get_bool(i.guild.id, "system_on")
        put(i.guild.id, "system_on", v)
        await i.response.send_message(
            "🟢 النظام يعمل." if v else "🔴 النظام متوقف.",
            ephemeral=True
        )

    @discord.ui.button(label="📋 تعيين LOG", style=discord.ButtonStyle.secondary)
    async def log(self, i, button):
        if not await self.allowed(i):
            return
        put(i.guild.id, "log_channel", i.channel.id)
        await i.response.send_message(
            f"✅ تم تعيين هذه القناة للـLOG.\n🆔 `{i.channel.id}`",
            ephemeral=True
        )

    @discord.ui.button(label="⛔ إيقاف البوت", style=discord.ButtonStyle.danger)
    async def stop(self, i, button):
        if not await self.allowed(i):
            return
        await i.response.send_message("⛔ سيتم إيقاف البوت.", ephemeral=True)
        await bot.close()


@bot.tree.command(name="SOKO_IDMIN", description="لوحة تحكم المبرمج")
async def soko(i: discord.Interaction):
    if not is_owner(i.user.id):
        return await i.response.send_message("❌ هذا الأمر خاص بمالك البوت.", ephemeral=True)
    await i.response.send_modal(OwnerModal())


@bot.tree.command(name="help", description="مساعدة")
async def help_cmd(i: discord.Interaction):
    await i.response.send_message(
        "🎨 **COLORS_SOK_2B**\n\n"
        "🎨 `/colors` — صورة الألوان\n"
        "🛠️ `/setcolor ID` — تغيير لون عضو للإدارة\n"
        "👑 `/SOKO_IDMIN` — لوحة المبرمج\n"
        "ℹ️ `/help` — المساعدة\n\n"
        "👤 العضو: أرسل رقم اللون مثل `27` أو HEX مثل `#2962FF`.",
        ephemeral=True
    )


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.guild and get_bool(message.guild.id, "system_on") and get_bool(message.guild.id, "members_on"):
        raw = message.content.strip()
        is_number = raw.isdigit() and 1 <= int(raw) <= 100
        is_hex = valid_hex(raw) is not None

        if is_number or is_hex:
            try:
                label, hex_code = await apply_color(message.author, raw, "Self")
                try:
                    await message.delete()
                except discord.HTTPException:
                    pass
                await message.channel.send(
                    f"✅ {message.author.mention} تم تغيير لونك إلى {label} `{hex_code}`.",
                    delete_after=8
                )
                return
            except discord.Forbidden:
                await message.channel.send("❌ البوت لا يملك صلاحية إدارة الرتب.", delete_after=8)
                return
            except Exception:
                logging.exception("member color error")
                await message.channel.send("❌ حدث خطأ أثناء تغيير اللون.", delete_after=8)
                return

    await bot.process_commands(message)


@bot.event
async def on_ready():
    init()
    try:
        synced = await bot.tree.sync()
        print(f"COLORS_SOK_2B online: {bot.user} | commands: {len(synced)}")
    except Exception:
        logging.exception("Command sync failed")


if __name__ == "__main__":
    init()
    if not TOKEN or TOKEN == "PUT_YOUR_NEW_DISCORD_BOT_TOKEN_HERE":
        raise RuntimeError("ضع توكن Discord الجديد في المتغير TOKEN.")
    bot.run(TOKEN)
