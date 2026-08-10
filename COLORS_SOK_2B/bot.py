import os
import re
import sqlite3
import logging
import asyncio
from datetime import datetime, timezone

import discord
from discord.ext import commands
from discord import app_commands


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB = os.path.join(BASE_DIR, "colors_sok_2b.sqlite3")
IMAGE = os.path.join(BASE_DIR, "colors.png")


# ============================================================
# OWNER
# ============================================================

OWNER_USER_ID = 1531577881548034100
OWNER_CODE = "uefoxe1436"


# ============================================================
# DISCORD TOKEN
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")


# ============================================================
# COLORS
# ============================================================

COLORS = [
    (1, "#FF1744", "أحمر نيون"),
    (2, "#D50000", "أحمر قوي"),
    (3, "#B71C1C", "أحمر داكن"),
    (4, "#FF5252", "أحمر فاتح"),

    (5, "#FF6D00", "برتقالي نيون"),
    (6, "#E65100", "برتقالي داكن"),
    (7, "#FF9100", "برتقالي"),
    (8, "#FFB300", "ذهبي برتقالي"),

    (9, "#FFD600", "أصفر نيون"),
    (10, "#F9A825", "أصفر ذهبي"),
    (11, "#F57F17", "أصفر داكن"),
    (12, "#FFF176", "أصفر فاتح"),

    (13, "#76FF03", "أخضر نيون"),
    (14, "#64DD17", "أخضر ليموني"),
    (15, "#00C853", "أخضر قوي"),
    (16, "#1B5E20", "أخضر داكن"),

    (17, "#00E676", "أخضر RGB"),
    (18, "#00BFA5", "تركوازي"),
    (19, "#009688", "تركوازي داكن"),
    (20, "#A7FFEB", "نعناعي"),

    (21, "#00E5FF", "سماوي نيون"),
    (22, "#00B8D4", "سماوي قوي"),
    (23, "#00838F", "سماوي داكن"),
    (24, "#80DEEA", "سماوي فاتح"),

    (25, "#2979FF", "أزرق نيون"),
    (26, "#2962FF", "أزرق قوي"),
    (27, "#1565C0", "أزرق داكن"),
    (28, "#82B1FF", "أزرق فاتح"),

    (29, "#3D5AFE", "نيلي نيون"),
    (30, "#304FFE", "نيلي قوي"),
    (31, "#1A237E", "نيلي داكن"),
    (32, "#8C9EFF", "نيلي فاتح"),

    (33, "#651FFF", "بنفسجي نيون"),
    (34, "#6200EA", "بنفسجي قوي"),
    (35, "#4527A0", "بنفسجي داكن"),
    (36, "#B388FF", "بنفسجي فاتح"),

    (37, "#D500F9", "فوشيا نيون"),
    (38, "#AA00FF", "أرجواني نيون"),
    (39, "#6A1B9A", "أرجواني داكن"),
    (40, "#EA80FC", "أرجواني فاتح"),

    (41, "#FF00FF", "ماجنتا"),
    (42, "#F50057", "وردي قوي"),
    (43, "#880E4F", "وردي داكن"),
    (44, "#FF80AB", "وردي فاتح"),

    (45, "#FF4081", "وردي نيون"),
    (46, "#C51162", "وردي عميق"),
    (47, "#AD1457", "كرزي داكن"),
    (48, "#FFCDD2", "وردي باهت"),

    (49, "#FFFFFF", "أبيض"),
    (50, "#F5F5F5", "رمادي فاتح جدًا"),
    (51, "#E0E0E0", "فضي فاتح"),
    (52, "#BDBDBD", "فضي"),

    (53, "#757575", "رمادي"),
    (54, "#424242", "رمادي داكن"),
    (55, "#212121", "فحمي"),
    (56, "#000000", "أسود"),

    (57, "#263238", "أزرق فحمي"),
    (58, "#37474F", "رمادي أزرق"),
    (59, "#455A64", "رمادي أزرق متوسط"),
    (60, "#546E7A", "رمادي أزرق فاتح"),

    (61, "#3E2723", "بني داكن"),
    (62, "#4E342E", "بني"),
    (63, "#5D4037", "بني متوسط"),
    (64, "#795548", "بني فاتح"),

    (65, "#FF3D00", "أحمر برتقالي"),
    (66, "#FF7043", "مرجاني"),
    (67, "#FF8A65", "مرجاني فاتح"),
    (68, "#BF360C", "نحاسي داكن"),

    (69, "#8BC34A", "ليموني"),
    (70, "#CDDC39", "ليموني أصفر"),
    (71, "#AFB42B", "زيتوني"),
    (72, "#827717", "زيتوني داكن"),

    (73, "#00ACC1", "سماوي متوسط"),
    (74, "#006064", "سماوي عميق"),
    (75, "#26C6DA", "سماوي فاتح قوي"),
    (76, "#4DD0E1", "سماوي ناعم"),

    (77, "#5E35B1", "بنفسجي متوسط"),
    (78, "#7E57C2", "بنفسجي ناعم"),
    (79, "#9575CD", "بنفسجي فاتح قوي"),
    (80, "#311B92", "بنفسجي عميق"),

    (81, "#EC407A", "وردي متوسط"),
    (82, "#E91E63", "وردي قوي 2"),
    (83, "#9C275A", "توتي داكن"),
    (84, "#F48FB1", "وردي ناعم"),

    (85, "#00FF9C", "RGB أخضر"),
    (86, "#00FFD5", "RGB تركوازي"),
    (87, "#00A2FF", "RGB أزرق"),
    (88, "#7A00FF", "RGB بنفسجي"),

    (89, "#FF00A8", "RGB وردي"),
    (90, "#FF0055", "RGB أحمر وردي"),
    (91, "#39FF14", "Lime Neon"),
    (92, "#B026FF", "Purple Neon"),

    (93, "#FFEA00", "Yellow Neon"),
    (94, "#00FFFF", "Cyan Neon"),
    (95, "#FF1493", "Deep Pink"),
    (96, "#7C4DFF", "Electric Violet"),

    (97, "#FF6B00", "Neon Orange"),
    (98, "#00FF66", "Neon Green"),
    (99, "#6B00FF", "Neon Purple"),
    (100, "#FF006B", "Neon Pink"),
]


# ============================================================
# COLOR ALIASES
# ============================================================

COLOR_ALIASES = {
    "احمر": "#FF1744",
    "أحمر": "#FF1744",

    "احمر نيون": "#FF1744",
    "أحمر نيون": "#FF1744",

    "برتقالي": "#FF9100",
    "برتقالي نيون": "#FF6D00",

    "اصفر": "#FFD600",
    "أصفر": "#FFD600",

    "اصفر نيون": "#FFD600",
    "أصفر نيون": "#FFD600",

    "اصفر ليموني": "#CDDC39",
    "أصفر ليموني": "#CDDC39",

    "اخضر": "#00C853",
    "أخضر": "#00C853",

    "اخضر ليموني": "#64DD17",
    "أخضر ليموني": "#64DD17",

    "اخضر نيون": "#76FF03",
    "أخضر نيون": "#76FF03",

    "تركوازي": "#00BFA5",

    "سماوي": "#00E5FF",
    "سماوي نيون": "#00E5FF",

    "ازرق": "#2979FF",
    "أزرق": "#2979FF",

    "ازرق نيون": "#2979FF",
    "أزرق نيون": "#2979FF",

    "نيلي": "#3D5AFE",

    "بنفسجي": "#651FFF",
    "بنفسجي نيون": "#651FFF",

    "بنفسجي فاتح": "#B388FF",

    "بنفسجي قوي": "#6200EA",

    "بنفسجي عميق": "#311B92",

    "ارجواني": "#AA00FF",
    "أرجواني": "#AA00FF",

    "ارجواني نيون": "#AA00FF",
    "أرجواني نيون": "#AA00FF",

    "وردي": "#F50057",
    "وردي نيون": "#FF4081",

    "ماجنتا": "#FF00FF",

    "ابيض": "#FFFFFF",
    "أبيض": "#FFFFFF",

    "اسود": "#000000",
    "أسود": "#000000",

    "ذهبي": "#F9A825",

    "ليموني": "#8BC34A",

    "purple": "#651FFF",
    "purple neon": "#B026FF",
    "light purple": "#B388FF",

    "yellow": "#FFD600",
    "yellow neon": "#FFEA00",

    "lime": "#39FF14",
    "lime neon": "#39FF14",

    "green": "#00C853",
    "green neon": "#76FF03",

    "blue": "#2979FF",
    "blue neon": "#2979FF",

    "cyan": "#00FFFF",
    "cyan neon": "#00FFFF",

    "pink": "#F50057",
    "pink neon": "#FF4081",

    "red": "#FF1744",
    "red neon": "#FF1744",

    "orange": "#FF9100",
    "orange neon": "#FF6D00",

    "violet": "#7C4DFF",
    "electric violet": "#7C4DFF",

    "magenta": "#FF00FF",
}


# ============================================================
# DISCORD
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# ============================================================
# DATABASE
# ============================================================

db = sqlite3.connect(
    DB,
    check_same_thread=False
)

db.row_factory = sqlite3.Row


def init():
    db.execute("""
        CREATE TABLE IF NOT EXISTS settings(
            guild_id INTEGER PRIMARY KEY,
            members_on INTEGER DEFAULT 1,
            admins_on INTEGER DEFAULT 1,
            system_on INTEGER DEFAULT 1,
            log_channel INTEGER
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS roles(
            guild_id INTEGER,
            user_id INTEGER,
            role_id INTEGER,
            PRIMARY KEY(guild_id, user_id)
        )
    """)

    db.commit()


def ensure(guild_id):
    db.execute(
        "INSERT OR IGNORE INTO settings(guild_id) VALUES(?)",
        (guild_id,)
    )

    db.commit()


def get_bool(guild_id, key):
    if key not in {
        "members_on",
        "admins_on",
        "system_on"
    }:
        raise ValueError("Invalid setting")

    ensure(guild_id)

    row = db.execute(
        f"SELECT {key} FROM settings WHERE guild_id=?",
        (guild_id,)
    ).fetchone()

    return bool(row[key])


def put(guild_id, key, value):
    if key not in {
        "members_on",
        "admins_on",
        "system_on",
        "log_channel"
    }:
        raise ValueError("Invalid setting")

    ensure(guild_id)

    db.execute(
        f"UPDATE settings SET {key}=? WHERE guild_id=?",
        (int(value), guild_id)
    )

    db.commit()


def get_log_channel(guild_id):
    ensure(guild_id)

    row = db.execute(
        "SELECT log_channel FROM settings WHERE guild_id=?",
        (guild_id,)
    ).fetchone()

    return row["log_channel"]


# ============================================================
# PERMISSIONS
# ============================================================

def is_admin(member):
    return isinstance(member, discord.Member) and (
        member.guild.owner_id == member.id
        or member.guild_permissions.administrator
    )


def is_owner(user_id):
    return user_id == OWNER_USER_ID


# ============================================================
# BASIC HEX
# ============================================================

def valid_hex(value):
    value = value.strip().upper()

    if not value.startswith("#"):
        value = "#" + value

    if re.fullmatch(r"#[0-9A-F]{6}", value):
        return value

    if re.fullmatch(r"#[0-9A-F]{3}", value):
        return "#" + "".join(
            c * 2 for c in value[1:]
        )

    return None


def hex_to_int(value):
    return int(value.replace("#", ""), 16)


# ============================================================
# COLOR PARSER
# ============================================================

def find_colors_from_text(value):
    text = value.strip()
    lower = text.lower()

    found = []

    # --------------------------------------------------------
    # HEX COLORS
    # --------------------------------------------------------

    hex_matches = re.findall(
        r"(?<![0-9A-Fa-f])#?[0-9A-Fa-f]{6}(?![0-9A-Fa-f])",
        text
    )

    for item in hex_matches:
        h = valid_hex(item)

        if h and h not in found:
            found.append(h)

    # --------------------------------------------------------
    # COLOR NUMBERS
    # --------------------------------------------------------

    number_matches = re.findall(
        r"(?<!\d)(100|[1-9]\d?)(?!\d)",
        text
    )

    for item in number_matches:
        number = int(item)

        result = next(
            (
                (h, name)
                for i, h, name in COLORS
                if i == number
            ),
            None
        )

        if result:
            h, _ = result

            if h not in found:
                found.append(h)

    # --------------------------------------------------------
    # COLOR NAMES
    # --------------------------------------------------------

    aliases = sorted(
        COLOR_ALIASES.items(),
        key=lambda x: len(x[0]),
        reverse=True
    )

    for name, h in aliases:

        pattern = re.escape(name.lower())

        if re.search(
            rf"(?<!\w){pattern}(?!\w)",
            lower
        ):
            if h not in found:
                found.append(h)

    return found


def parse_color(value):

    if not value or not value.strip():
        raise ValueError(
            "اكتب لونًا مثل `27` أو `#C86BFF`."
        )

    raw = value.strip()
    lower = raw.lower()

    colors = find_colors_from_text(raw)

    if not colors:
        raise ValueError(
            "لم أتعرف على اللون.\n"
            "أمثلة:\n"
            "`27`\n"
            "`#C86BFF`\n"
            "`بنفسجي فاتح`\n"
            "`#C86BFF #FFD900`"
        )

    if len(colors) > 3:
        raise ValueError(
            "❌ الحد الأقصى 3 ألوان."
        )

    is_neon = any(
        word in lower
        for word in (
            "neon",
            "نيون",
            "rgb",
            "مضيء",
            "مضيئ"
        )
    )

    is_gradient = (
        "gradient" in lower
        or "grad" in lower
        or "تدرج" in lower
        or "تدرّج" in lower
        or len(colors) >= 2
    )

    # --------------------------------------------------------
    # ONE COLOR
    # --------------------------------------------------------

    if len(colors) == 1:

        h = colors[0]

        if is_neon:
            label = f"NEON {h}"
        else:
            label = h

        return {
            "type": "solid",
            "colors": [h],
            "label": label,
            "description": "لون واحد"
        }

    # --------------------------------------------------------
    # TWO COLORS
    # --------------------------------------------------------

    if len(colors) == 2:

        if not is_gradient:
            is_gradient = True

        return {
            "type": "gradient",
            "colors": colors,
            "label": f"GRADIENT {colors[0]} → {colors[1]}",
            "description": "تدرج بلونين"
        }

    # --------------------------------------------------------
    # THREE COLORS
    # --------------------------------------------------------

    if len(colors) == 3:

        raise ValueError(
            "⚠️ Discord حاليًا لا يسمح بتدرج مخصص من 3 ألوان "
            "داخل Role واحد.\n\n"
            "يمكن استخدام لونين حقيقيين فقط للتدرج:\n"
            f"`{colors[0]} {colors[1]}`\n\n"
            "أما اللون الثالث في Discord فهو مخصص لنمط "
            "Holographic بألوان ثابتة من Discord."
        )

    raise ValueError("تعذر تحليل اللون.")


# ============================================================
# ROLE
# ============================================================

async def color_role(member):

    row = db.execute(
        """
        SELECT role_id
        FROM roles
        WHERE guild_id=? AND user_id=?
        """,
        (
            member.guild.id,
            member.id
        )
    ).fetchone()

    role = (
        member.guild.get_role(row["role_id"])
        if row
        else None
    )

    # --------------------------------------------------------
    # CREATE
    # --------------------------------------------------------

    if role is None:

        role = await member.guild.create_role(
            name=f"COLOR • {member.display_name}"[:100],
            colour=discord.Colour.default(),
            reason="COLORS_SOK_2B personal color role"
        )

        db.execute(
            """
            INSERT OR REPLACE INTO roles(
                guild_id,
                user_id,
                role_id
            )
            VALUES(?,?,?)
            """,
            (
                member.guild.id,
                member.id,
                role.id
            )
        )

        db.commit()

    # --------------------------------------------------------
    # MOVE ROLE ABOVE MEMBER ROLES
    # --------------------------------------------------------

    me = member.guild.me

    if me and me.top_role > role:

        target_position = max(
            1,
            me.top_role.position - 1
        )

        try:
            await member.guild.edit_role_positions(
                positions={
                    role: target_position
                },
                reason="COLORS_SOK_2B color role position"
            )
        except discord.HTTPException:
            pass

    return role


# ============================================================
# LOG
# ============================================================

async def write_log(
    guild,
    member,
    old,
    new,
    who
):

    channel_id = get_log_channel(
        guild.id
    )

    if not channel_id:
        return

    channel = guild.get_channel(
        channel_id
    )

    if not channel:
        return

    now = datetime.now(
        timezone.utc
    ).astimezone()

    text = (
        "🎨 **COLORS_SOK_2B LOG**\n\n"
        f"👤 **العضو:**\n{member.display_name}\n\n"
        f"🆔 **ID:**\n{member.id}\n\n"
        f"🔴 **السابق:**\n{old}\n\n"
        f"🟢 **الجديد:**\n{new}\n\n"
        f"👮 **بواسطة:**\n{who}\n\n"
        f"🕒 **الوقت:**\n"
        f"{now.strftime('%Y/%m/%d %H:%M:%S')}"
    )

    try:
        await channel.send(
            text
        )
    except discord.HTTPException:
        pass


# ============================================================
# APPLY COLOR
# ============================================================

async def apply_color(
    member,
    value,
    who
):

    spec = parse_color(
        value
    )

    role = await color_role(
        member
    )

    old = role.name

    primary = spec["colors"][0]

    primary_int = hex_to_int(
        primary
    )

    # --------------------------------------------------------
    # SOLID
    # --------------------------------------------------------

    if spec["type"] == "solid":

        await role.edit(
            name=f"COLOR • {member.display_name}"[:100],
            colour=discord.Colour(
                primary_int
            ),
            secondary_colour=None,
            tertiary_colour=None,
            reason="COLORS_SOK_2B solid color"
        )

    # --------------------------------------------------------
    # GRADIENT
    # --------------------------------------------------------

    elif spec["type"] == "gradient":

        if "ENHANCED_ROLE_COLORS" not in member.guild.features:

            raise ValueError(
                "❌ السيرفر لا يدعم التدرجات حاليًا.\n\n"
                "يجب تفعيل Enhanced Role Styles في السيرفر "
                "حتى يستطيع Discord استخدام Gradient Roles."
            )

        secondary = spec["colors"][1]

        secondary_int = hex_to_int(
            secondary
        )

        await role.edit(
            name=f"COLOR • {member.display_name}"[:100],
            colour=discord.Colour(
                primary_int
            ),
            secondary_colour=discord.Colour(
                secondary_int
            ),
            tertiary_colour=None,
            reason="COLORS_SOK_2B gradient color"
        )

    # --------------------------------------------------------
    # ADD ROLE
    # --------------------------------------------------------

    if role not in member.roles:

        await member.add_roles(
            role,
            reason="COLORS_SOK_2B"
        )

    # --------------------------------------------------------
    # LOG
    # --------------------------------------------------------

    await write_log(
        member.guild,
        member,
        old,
        spec["label"],
        who
    )

    return spec


# ============================================================
# /colors
# ============================================================

@bot.tree.command(
    name="colors",
    description="عرض صورة الألوان وطريقة اختيار اللون"
)
async def colors_cmd(
    i: discord.Interaction
):

    if not i.guild:

        return await i.response.send_message(
            "❌ استخدمه داخل السيرفر.",
            ephemeral=True
        )

    if not get_bool(
        i.guild.id,
        "system_on"
    ):

        return await i.response.send_message(
            "⛔ النظام متوقف.",
            ephemeral=True
        )

    if not os.path.exists(IMAGE):

        return await i.response.send_message(
            "❌ colors.png غير موجود.",
            ephemeral=True
        )

    await i.response.send_message(
        "🎨 **نظام COLORS_SOK_2B**\n\n"
        "لون واحد:\n"
        "`27`\n"
        "`#C86BFF`\n"
        "`بنفسجي فاتح`\n\n"
        "تدرج بلونين:\n"
        "`#C86BFF #FFD900`\n"
        "`تدرج #C86BFF + #FFD900`\n"
        "`بنفسجي فاتح + أصفر ليموني`\n\n"
        "نيون:\n"
        "`نيون #C86BFF`\n"
        "`neon #39FF14`\n\n"
        "⚠️ التدرج المخصص يدعم لونين.",
        file=discord.File(IMAGE)
    )


# ============================================================
# /setcolor
# ============================================================

@bot.tree.command(
    name="setcolor",
    description="تغيير لون أو تدرج عضو - الإدارة"
)
@app_commands.describe(
    user_id="ID العضو المستهدف"
)
async def setcolor(
    i: discord.Interaction,
    user_id: str
):

    if not i.guild:

        return await i.response.send_message(
            "❌ داخل السيرفر فقط.",
            ephemeral=True
        )

    if not is_admin(i.user):

        return await i.response.send_message(
            "❌ هذا الأمر للإدارة فقط.",
            ephemeral=True
        )

    if not get_bool(
        i.guild.id,
        "admins_on"
    ):

        return await i.response.send_message(
            "⛔ إدارة البوت متوقفة.",
            ephemeral=True
        )

    if not user_id.isdigit():

        return await i.response.send_message(
            "❌ ID غير صحيح.",
            ephemeral=True
        )

    member = i.guild.get_member(
        int(user_id)
    )

    if member is None:

        try:

            member = await i.guild.fetch_member(
                int(user_id)
            )

        except discord.HTTPException:

            member = None

    if member is None:

        return await i.response.send_message(
            "❌ العضو غير موجود.",
            ephemeral=True
        )

    await i.response.send_message(
        f"👤 {member.mention}\n\n"
        "🎨 أرسل الآن اللون أو التدرج.\n\n"
        "**أمثلة:**\n"
        "`27`\n"
        "`#C86BFF`\n"
        "`#C86BFF #FFD900`\n"
        "`تدرج #C86BFF + #FFD900`\n"
        "`بنفسجي فاتح + أصفر ليموني`\n"
        "`نيون #39FF14`\n\n"
        "⏳ لديك 120 ثانية.",
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

        msg = await bot.wait_for(
            "message",
            timeout=120,
            check=check
        )

        spec = await apply_color(
            member,
            msg.content,
            i.user.display_name
        )

        try:

            await msg.delete()

        except discord.HTTPException:
            pass

        if spec["type"] == "gradient":

            colors_text = (
                f"`{spec['colors'][0]}`"
                f" → "
                f"`{spec['colors'][1]}`"
            )

            await i.followup.send(
                "🌈 **تم تطبيق التدرج بنجاح!**\n\n"
                f"👤 {member.mention}\n"
                f"🎨 {colors_text}",
                ephemeral=True
            )

        else:

            await i.followup.send(
                "✅ **تم تغيير اللون!**\n\n"
                f"👤 {member.mention}\n"
                f"🎨 `{spec['colors'][0]}`",
                ephemeral=True
            )

    except asyncio.TimeoutError:

        await i.followup.send(
            "⌛ انتهى الوقت.",
            ephemeral=True
        )

    except ValueError as e:

        await i.followup.send(
            f"{e}",
            ephemeral=True
        )

    except discord.Forbidden:

        await i.followup.send(
            "❌ البوت لا يملك صلاحية إدارة الرتب.\n\n"
            "تأكد من:\n"
            "• Manage Roles\n"
            "• وضع رتبة البوت فوق رتبة اللون.",
            ephemeral=True
        )

    except discord.HTTPException as e:

        logging.exception(
            "Discord HTTP error"
        )

        await i.followup.send(
            "❌ Discord رفض تعديل الرتبة.\n\n"
            f"الخطأ: `{e}`",
            ephemeral=True
        )

    except Exception:

        logging.exception(
            "setcolor error"
        )

        await i.followup.send(
            "❌ حدث خطأ أثناء تطبيق اللون.",
            ephemeral=True
        )


# ============================================================
# OWNER MODAL
# ============================================================

class OwnerModal(
    discord.ui.Modal,
    title="SOKO_IDMIN"
):

    code = discord.ui.TextInput(
        label="رمز المالك",
        required=True
    )

    async def on_submit(
        self,
        i: discord.Interaction
    ):

        if not is_owner(
            i.user.id
        ):

            return await i.response.send_message(
                "❌ غير مصرح.",
                ephemeral=True
            )

        if str(self.code) != OWNER_CODE:

            return await i.response.send_message(
                "❌ رمز غير صحيح.",
                ephemeral=True
            )

        if not i.guild:

            return await i.response.send_message(
                "❌ داخل السيرفر فقط.",
                ephemeral=True
            )

        await i.response.send_message(
            "👑 **لوحة تحكم COLORS_SOK_2B**",
            view=OwnerView(),
            ephemeral=True
        )


# ============================================================
# OWNER VIEW
# ============================================================

class OwnerView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=300
        )

    async def allowed(
        self,
        i
    ):

        if not is_owner(
            i.user.id
        ):

            await i.response.send_message(
                "❌ غير مصرح.",
                ephemeral=True
            )

            return False

        if not i.guild:

            await i.response.send_message(
                "❌ داخل السيرفر فقط.",
                ephemeral=True
            )

            return False

        return True

    @discord.ui.button(
        label="🎨 الأعضاء",
        style=discord.ButtonStyle.primary
    )
    async def members(
        self,
        i,
        button
    ):

        if not await self.allowed(i):
            return

        v = not get_bool(
            i.guild.id,
            "members_on"
        )

        put(
            i.guild.id,
            "members_on",
            v
        )

        await i.response.send_message(
            "🟢 تغيير الألوان للأعضاء مفعّل."
            if v
            else
            "🔴 تغيير الألوان للأعضاء متوقف.",
            ephemeral=True
        )

    @discord.ui.button(
        label="👑 الإدارة",
        style=discord.ButtonStyle.secondary
    )
    async def admins(
        self,
        i,
        button
    ):

        if not await self.allowed(i):
            return

        v = not get_bool(
            i.guild.id,
            "admins_on"
        )

        put(
            i.guild.id,
            "admins_on",
            v
        )

        await i.response.send_message(
            "🟢 أوامر الإدارة مفعّلة."
            if v
            else
            "🔴 أوامر الإدارة متوقفة.",
            ephemeral=True
        )

    @discord.ui.button(
        label="🤖 النظام",
        style=discord.ButtonStyle.success
    )
    async def system(
        self,
        i,
        button
    ):

        if not await self.allowed(i):
            return

        v = not get_bool(
            i.guild.id,
            "system_on"
        )

        put(
            i.guild.id,
            "system_on",
            v
        )

        await i.response.send_message(
            "🟢 النظام يعمل."
            if v
            else
            "🔴 النظام متوقف.",
            ephemeral=True
        )

    @discord.ui.button(
        label="📋 تعيين LOG",
        style=discord.ButtonStyle.secondary
    )
    async def log(
        self,
        i,
        button
    ):

        if not await self.allowed(i):
            return

        put(
            i.guild.id,
            "log_channel",
            i.channel.id
        )

        await i.response.send_message(
            "✅ تم تعيين هذه القناة للـLOG.\n"
            f"🆔 `{i.channel.id}`",
            ephemeral=True
        )

    @discord.ui.button(
        label="⛔ إيقاف البوت",
        style=discord.ButtonStyle.danger
    )
    async def stop(
        self,
        i,
        button
    ):

        if not await self.allowed(i):
            return

        await i.response.send_message(
            "⛔ سيتم إيقاف البوت.",
            ephemeral=True
        )

        await bot.close()


# ============================================================
# /soko_idmin
# ============================================================

@bot.tree.command(
    name="soko_idmin",
    description="لوحة تحكم المبرمج"
)
async def soko(
    i: discord.Interaction
):

    if not is_owner(
        i.user.id
    ):

        return await i.response.send_message(
            "❌ هذا الأمر خاص بمالك البوت.",
            ephemeral=True
        )

    await i.response.send_modal(
        OwnerModal()
    )


# ============================================================
# /help
# ============================================================

@bot.tree.command(
    name="help",
    description="مساعدة COLORS_SOK_2B"
)
async def help_cmd(
    i: discord.Interaction
):

    await i.response.send_message(
        "🎨 **COLORS_SOK_2B**\n\n"

        "🎨 `/colors`\n"
        "عرض نظام الألوان.\n\n"

        "🛠️ `/setcolor ID`\n"
        "تغيير لون عضو.\n\n"

        "👑 `/soko_idmin`\n"
        "لوحة المبرمج.\n\n"

        "━━━━━━━━━━━━━━━━━━\n\n"

        "**لون واحد:**\n"
        "`27`\n"
        "`#C86BFF`\n"
        "`بنفسجي فاتح`\n\n"

        "**تدرج:**\n"
        "`#C86BFF #FFD900`\n"
        "`تدرج #C86BFF + #FFD900`\n"
        "`بنفسجي فاتح + أصفر ليموني`\n\n"

        "**نيون:**\n"
        "`نيون #39FF14`\n"
        "`neon #B026FF`\n\n"

        "⚠️ التدرج المخصص = لونان.",
        ephemeral=True
    )


# ============================================================
# BOT JOIN GUILD
# ============================================================

@bot.event
async def on_guild_join(
    guild
):

    ensure(
        guild.id
    )

    logging.info(
        f"Bot joined guild: "
        f"{guild.name} ({guild.id})"
    )

    # محاولة إرسال رسالة ترحيب
    channel = guild.system_channel

    if channel is None:

        for ch in guild.text_channels:

            if ch.permissions_for(
                guild.me
            ).send_messages:

                channel = ch
                break

    if channel is not None:

        try:

            await channel.send(
                "🎨 **COLORS_SOK_2B متصل!**\n\n"
                "يمكن للأعضاء الآن إرسال:\n"
                "`27`\n"
                "`#C86BFF`\n"
                "`#C86BFF #FFD900`\n\n"
                "استخدم `/help` لمعرفة جميع الخيارات."
            )

        except discord.HTTPException:
            pass


# ============================================================
# ON MESSAGE
# ============================================================

@bot.event
async def on_message(
    message
):

    if message.author.bot:
        return

    # --------------------------------------------------------
    # COLOR SYSTEM
    # --------------------------------------------------------

    if (
        message.guild
        and get_bool(
            message.guild.id,
            "system_on"
        )
        and get_bool(
            message.guild.id,
            "members_on"
        )
    ):

        raw = message.content.strip()

        # لا نحاول معالجة الرسائل الطويلة جدًا
        if len(raw) <= 300:

            # نتحقق هل تحتوي الرسالة على لون
            possible_colors = find_colors_from_text(
                raw
            )

            if possible_colors:

                try:

                    spec = await apply_color(
                        message.author,
                        raw,
                        "Self"
                    )

                    try:
                        await message.delete()

                    except discord.HTTPException:
                        pass

                    if spec["type"] == "gradient":

                        await message.channel.send(
                            f"🌈 {message.author.mention} "
                            f"تم تطبيق التدرج:\n"
                            f"`{spec['colors'][0]}` → "
                            f"`{spec['colors'][1]}`",
                            delete_after=8
                        )

                    else:

                        await message.channel.send(
                            f"✅ {message.author.mention} "
                            f"تم تغيير لونك إلى "
                            f"`{spec['colors'][0]}`.",
                            delete_after=8
                        )

                    return

                except ValueError as e:

                    # رسائل 3 ألوان مثلًا
                    await message.channel.send(
                        f"{message.author.mention} {e}",
                        delete_after=10
                    )

                    return

                except discord.Forbidden:

                    await message.channel.send(
                        "❌ البوت لا يملك صلاحية إدارة الرتب.",
                        delete_after=8
                    )

                    return

                except discord.HTTPException:

                    logging.exception(
                        "Discord HTTP error"
                    )

                    await message.channel.send(
                        "❌ Discord رفض تعديل اللون.",
                        delete_after=8
                    )

                    return

                except Exception:

                    logging.exception(
                        "member color error"
                    )

                    await message.channel.send(
                        "❌ حدث خطأ أثناء تغيير اللون.",
                        delete_after=8
                    )

                    return

    # --------------------------------------------------------
    # COMMANDS
    # --------------------------------------------------------

    await bot.process_commands(
        message
    )


# ============================================================
# READY
# ============================================================

@bot.event
async def on_ready():

    init()

    logging.info(
        f"COLORS_SOK_2B online: "
        f"{bot.user}"
    )

    logging.info(
        f"Guilds: {len(bot.guilds)}"
    )

    try:

        synced = await bot.tree.sync()

        logging.info(
            f"Slash commands synced: "
            f"{len(synced)}"
        )

    except Exception:

        logging.exception(
            "Command sync failed"
        )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    init()

    if not TOKEN:

        raise RuntimeError(
            "DISCORD_TOKEN غير موجود في GitHub Secrets."
        )

    bot.run(
        TOKEN
    )
