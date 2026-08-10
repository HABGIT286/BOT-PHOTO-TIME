import os
import re
import sqlite3
import logging
import asyncio
from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands
from discord import app_commands


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB = os.path.join(
    BASE_DIR,
    "colors_sok_2b.sqlite3"
)

IMAGE = os.path.join(
    BASE_DIR,
    "colors.png"
)


# ============================================================
# OWNER
# ============================================================

OWNER_USER_ID = 1531577881548034100

OWNER_CODE = "uefoxe1436"


# ============================================================
# TOKEN
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")


# ============================================================
# SETTINGS
# ============================================================

MAX_USER_CHANGES_PER_HOUR = 5


# ============================================================
# RANKS
# ============================================================

RANKS = [
    "Owner",
    "Primary Developer",
    "Developer",
    "Manager",
    "Moderator",
    "Monitor",
    "Member"
]


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
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


# ============================================================
# DISCORD
# ============================================================

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


def column_exists(table, column):

    row = db.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    return any(
        r["name"] == column
        for r in row
    )


def add_column_if_missing(
    table,
    column,
    definition
):

    if not column_exists(
        table,
        column
    ):

        db.execute(
            f"ALTER TABLE {table} "
            f"ADD COLUMN {column} {definition}"
        )

        db.commit()


def init():

    db.execute("""
        CREATE TABLE IF NOT EXISTS settings(
            guild_id INTEGER PRIMARY KEY,
            members_on INTEGER DEFAULT 1,
            admins_on INTEGER DEFAULT 1,
            system_on INTEGER DEFAULT 1,
            bot_on INTEGER DEFAULT 1,
            log_on INTEGER DEFAULT 0,
            log_channel INTEGER,
            rate_limit_on INTEGER DEFAULT 1
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

    db.execute("""
        CREATE TABLE IF NOT EXISTS rank_roles(
            guild_id INTEGER,
            rank_name TEXT,
            role_id INTEGER,
            PRIMARY KEY(guild_id, rank_name)
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS color_usage(
            guild_id INTEGER,
            user_id INTEGER,
            used_at TEXT
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS color_bans(
            guild_id INTEGER,
            user_id INTEGER,
            until_at TEXT,
            PRIMARY KEY(guild_id, user_id)
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS color_history(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            user_id INTEGER,
            member_name TEXT,
            old_color TEXT,
            new_color TEXT,
            changed_by TEXT,
            changed_at TEXT,
            daily_changes INTEGER,
            was_locked INTEGER DEFAULT 0,
            member_rank TEXT,
            role_id INTEGER
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS member_name_history(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            user_id INTEGER,
            old_username TEXT,
            new_username TEXT,
            old_display_name TEXT,
            new_display_name TEXT,
            changed_at TEXT
        )
    """)

    # --------------------------------------------------------
    # MIGRATION FOR OLD DATABASE
    # --------------------------------------------------------

    add_column_if_missing(
        "settings",
        "bot_on",
        "INTEGER DEFAULT 1"
    )

    add_column_if_missing(
        "settings",
        "log_on",
        "INTEGER DEFAULT 0"
    )

    add_column_if_missing(
        "settings",
        "rate_limit_on",
        "INTEGER DEFAULT 1"
    )

    db.commit()


def ensure(guild_id):

    init()

    db.execute(
        """
        INSERT OR IGNORE INTO settings(
            guild_id
        )
        VALUES(?)
        """,
        (
            guild_id,
        )
    )

    db.commit()


def get_setting(
    guild_id,
    key
):

    allowed = {
        "members_on",
        "admins_on",
        "system_on",
        "bot_on",
        "log_on",
        "log_channel",
        "rate_limit_on"
    }

    if key not in allowed:
        raise ValueError(
            "Invalid setting"
        )

    ensure(
        guild_id
    )

    row = db.execute(
        f"""
        SELECT {key}
        FROM settings
        WHERE guild_id=?
        """,
        (
            guild_id,
        )
    ).fetchone()

    return row[key]


def get_bool(
    guild_id,
    key
):

    return bool(
        get_setting(
            guild_id,
            key
        )
    )


def put(
    guild_id,
    key,
    value
):

    allowed = {
        "members_on",
        "admins_on",
        "system_on",
        "bot_on",
        "log_on",
        "log_channel",
        "rate_limit_on"
    }

    if key not in allowed:
        raise ValueError(
            "Invalid setting"
        )

    ensure(
        guild_id
    )

    db.execute(
        f"""
        UPDATE settings
        SET {key}=?
        WHERE guild_id=?
        """,
        (
            int(value),
            guild_id
        )
    )

    db.commit()


def get_log_channel(
    guild_id
):

    return get_setting(
        guild_id,
        "log_channel"
    )


# ============================================================
# PERMISSIONS
# ============================================================

def is_admin(member):

    return (
        isinstance(
            member,
            discord.Member
        )
        and (
            member.guild.owner_id == member.id
            or member.guild_permissions.administrator
        )
    )


def is_owner(
    user_id
):

    return user_id == OWNER_USER_ID


def can_manage_colors(
    member
):

    return is_admin(
        member
    )


# ============================================================
# RANK
# ============================================================

def get_member_rank(
    member
):

    if member.guild.owner_id == member.id:
        return "Owner"

    for rank in RANKS:

        if any(
            role.name == f"SOKO • {rank}"
            for role in member.roles
        ):

            return rank

    return "Member"


async def get_or_create_rank_role(
    guild,
    rank_name
):

    if rank_name not in RANKS:
        raise ValueError(
            "رتبة غير صحيحة."
        )

    row = db.execute(
        """
        SELECT role_id
        FROM rank_roles
        WHERE guild_id=? AND rank_name=?
        """,
        (
            guild.id,
            rank_name
        )
    ).fetchone()

    role = None

    if row:
        role = guild.get_role(
            row["role_id"]
        )

    if role is None:

        role = discord.utils.get(
            guild.roles,
            name=f"SOKO • {rank_name}"
        )

    if role is None:

        role = await guild.create_role(
            name=f"SOKO • {rank_name}",
            colour=discord.Colour.default(),
            reason="COLORS_SOK_2B rank role"
        )

    db.execute(
        """
        INSERT OR REPLACE INTO rank_roles(
            guild_id,
            rank_name,
            role_id
        )
        VALUES(?,?,?)
        """,
        (
            guild.id,
            rank_name,
            role.id
        )
    )

    db.commit()

    return role


async def assign_rank(
    member,
    rank_name
):

    if rank_name not in RANKS:
        raise ValueError(
            "رتبة غير صحيحة."
        )

    # Member تعني إزالة جميع رتب SOKO وإعادته عضوًا عاديًا.
    if rank_name == "Member":
        remove_roles = [
            role
            for role in member.roles
            if role.name.startswith("SOKO • ")
        ]

        if remove_roles:
            await member.remove_roles(
                *remove_roles,
                reason="COLORS_SOK_2B demote to Member"
            )

        db.execute(
            "DELETE FROM rank_roles WHERE guild_id=? AND rank_name=?",
            (member.guild.id, "Member")
        )
        db.commit()
        return None

    role = await get_or_create_rank_role(
        member.guild,
        rank_name
    )

    remove_roles = [
        r
        for r in member.roles
        if r.name.startswith("SOKO • ") and r.id != role.id
    ]

    if remove_roles:
        await member.remove_roles(
            *remove_roles,
            reason="COLORS_SOK_2B rank change"
        )

    if role not in member.roles:
        await member.add_roles(
            role,
            reason="COLORS_SOK_2B rank assignment"
        )

    return role


# ============================================================
# HEX
# ============================================================

def valid_hex(
    value
):

    value = value.strip().upper()

    if not value.startswith("#"):
        value = "#" + value

    if re.fullmatch(
        r"#[0-9A-F]{6}",
        value
    ):
        return value

    if re.fullmatch(
        r"#[0-9A-F]{3}",
        value
    ):

        return "#" + "".join(
            c * 2
            for c in value[1:]
        )

    return None


def hex_to_int(
    value
):

    return int(
        value.replace(
            "#",
            ""
        ),
        16
    )


# ============================================================
# COLOR PARSER
# ============================================================

def find_colors_from_text(
    value
):

    text = value.strip()

    lower = text.lower()

    found = []

    # --------------------------------------------------------
    # HEX
    # --------------------------------------------------------

    hex_matches = re.findall(
        r"(?<![0-9A-Fa-f])#?[0-9A-Fa-f]{6}(?![0-9A-Fa-f])",
        text
    )

    for item in hex_matches:

        h = valid_hex(
            item
        )

        if h and h not in found:

            found.append(h)

    # --------------------------------------------------------
    # NUMBERS
    # --------------------------------------------------------

    number_matches = re.findall(
        r"(?<!\d)(100|[1-9]\d?)(?!\d)",
        text
    )

    for item in number_matches:

        number = int(
            item
        )

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
    # NAMES
    # --------------------------------------------------------

    aliases = sorted(
        COLOR_ALIASES.items(),
        key=lambda x: len(x[0]),
        reverse=True
    )

    for name, h in aliases:

        pattern = re.escape(
            name.lower()
        )

        if re.search(
            rf"(?<!\w){pattern}(?!\w)",
            lower
        ):

            if h not in found:

                found.append(h)

    return found


def parse_color(
    value
):

    if not value or not value.strip():

        raise ValueError(
            "❌ اكتب لونًا."
        )

    raw = value.strip()

    lower = raw.lower()

    colors = find_colors_from_text(
        raw
    )

    if not colors:

        raise ValueError(
            "❌ لم أتعرف على اللون.\n\n"
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

    # --------------------------------------------------------
    # ONE
    # --------------------------------------------------------

    if len(colors) == 1:

        h = colors[0]

        return {
            "type": "solid",
            "colors": [h],
            "label": (
                f"NEON {h}"
                if is_neon
                else h
            ),
            "description": (
                "لون نيون"
                if is_neon
                else "لون واحد"
            )
        }

    # --------------------------------------------------------
    # TWO
    # --------------------------------------------------------

    if len(colors) == 2:

        return {
            "type": "gradient",
            "colors": colors,
            "label": (
                f"GRADIENT "
                f"{colors[0]} → {colors[1]}"
            ),
            "description": "تدرج بلونين"
        }

    # --------------------------------------------------------
    # THREE
    # --------------------------------------------------------

    if len(colors) == 3:

        raise ValueError(
            "⚠️ تم التعرف على 3 ألوان، "
            "لكن Discord لا يسمح بتدرج مخصص من 3 ألوان.\n\n"
            f"الألوان:\n"
            f"`{colors[0]}`\n"
            f"`{colors[1]}`\n"
            f"`{colors[2]}`\n\n"
            "التدرج المخصص في Discord يستخدم لونين."
        )

    raise ValueError(
        "❌ تعذر تحليل اللون."
    )


# ============================================================
# GRADIENT SUPPORT
# ============================================================

def gradient_available(
    guild
):

    return (
        "ENHANCED_ROLE_COLORS"
        in guild.features
    )


def gradient_help_text():

    return (
        "🌈 **التدرج غير مفعّل في هذا السيرفر.**\n\n"
        "لتفعيل Gradient Roles:\n\n"
        "1️⃣ افتح Discord من الكمبيوتر أو المتصفح.\n"
        "2️⃣ ادخل إلى إعدادات السيرفر.\n"
        "3️⃣ افتح **Server Boosts**.\n"
        "4️⃣ ابحث عن **Enhanced Role Styles**.\n"
        "5️⃣ فعّل الميزة باستخدام الـ Boosts المتاحة.\n"
        "6️⃣ بعدها افتح Roles وتأكد أن Gradient متاح.\n\n"
        "بعد التفعيل اضغط **تحقق الآن**.\n\n"
        "💡 البوت لا يستطيع تجاوز متطلبات Discord نفسها."
    )


# ============================================================
# PERSONAL COLOR ROLE
# ============================================================

async def color_role(
    member
):

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

    role = None

    if row:

        role = member.guild.get_role(
            row["role_id"]
        )

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
    # ROLE POSITION
    # --------------------------------------------------------

    me = member.guild.me

    if me and me.top_role > role:

        try:

            position = max(
                1,
                me.top_role.position - 1
            )

            await member.guild.edit_role_positions(
                positions={
                    role: position
                },
                reason="COLORS_SOK_2B color role position"
            )

        except discord.HTTPException:

            pass

    return role


# ============================================================
# RATE LIMIT
# ============================================================

def cleanup_old_usage():

    cutoff = (
        datetime.now(
            timezone.utc
        )
        - timedelta(days=2)
    ).isoformat()

    db.execute(
        """
        DELETE FROM color_usage
        WHERE used_at < ?
        """,
        (
            cutoff,
        )
    )

    db.commit()


def get_hourly_usage(
    guild_id,
    user_id
):

    since = (
        datetime.now(
            timezone.utc
        )
        - timedelta(hours=1)
    ).isoformat()

    row = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM color_usage
        WHERE guild_id=?
        AND user_id=?
        AND used_at>=?
        """,
        (
            guild_id,
            user_id,
            since
        )
    ).fetchone()

    return int(
        row["total"]
    )


def get_daily_usage(
    guild_id,
    user_id
):

    today = datetime.now(
        timezone.utc
    ).date().isoformat()

    row = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM color_usage
        WHERE guild_id=?
        AND user_id=?
        AND substr(used_at,1,10)=?
        """,
        (
            guild_id,
            user_id,
            today
        )
    ).fetchone()

    return int(
        row["total"]
    )


def get_color_lock(
    guild_id,
    user_id
):

    row = db.execute(
        """
        SELECT until_at
        FROM color_bans
        WHERE guild_id=? AND user_id=?
        """,
        (
            guild_id,
            user_id
        )
    ).fetchone()

    if not row:
        return None

    try:

        until = datetime.fromisoformat(
            row["until_at"]
        )

    except Exception:

        db.execute(
            """
            DELETE FROM color_bans
            WHERE guild_id=? AND user_id=?
            """,
            (
                guild_id,
                user_id
            )
        )

        db.commit()

        return None

    if until <= datetime.now(
        timezone.utc
    ):

        db.execute(
            """
            DELETE FROM color_bans
            WHERE guild_id=? AND user_id=?
            """,
            (
                guild_id,
                user_id
            )
        )

        db.commit()

        return None

    return until


def lock_user_until_tomorrow(
    guild_id,
    user_id
):

    now = datetime.now(
        timezone.utc
    )

    tomorrow = (
        now.date()
        + timedelta(days=1)
    )

    until = datetime.combine(
        tomorrow,
        datetime.min.time(),
        tzinfo=timezone.utc
    )

    db.execute(
        """
        INSERT OR REPLACE INTO color_bans(
            guild_id,
            user_id,
            until_at
        )
        VALUES(?,?,?)
        """,
        (
            guild_id,
            user_id,
            until.isoformat()
        )
    )

    db.commit()

    return until


def register_color_usage(
    guild_id,
    user_id
):

    now = datetime.now(
        timezone.utc
    )

    db.execute(
        """
        INSERT INTO color_usage(
            guild_id,
            user_id,
            used_at
        )
        VALUES(?,?,?)
        """,
        (
            guild_id,
            user_id,
            now.isoformat()
        )
    )

    db.commit()


# ============================================================
# LOG
# ============================================================

async def write_log(
    guild,
    member,
    old,
    new,
    who,
    was_locked=False
):

    if not get_bool(
        guild.id,
        "log_on"
    ):
        return

    channel_id = get_log_channel(
        guild.id
    )

    if not channel_id:
        return

    channel = guild.get_channel(
        channel_id
    )

    if channel is None:
        return

    now = datetime.now(
        timezone.utc
    )

    daily_count = get_daily_usage(
        guild.id,
        member.id
    )

    rank = get_member_rank(
        member
    )

    role_id = None

    row = db.execute(
        """
        SELECT role_id
        FROM roles
        WHERE guild_id=? AND user_id=?
        """,
        (
            guild.id,
            member.id
        )
    ).fetchone()

    if row:
        role_id = row["role_id"]

    history_text = (
        f"🎨 **COLORS_SOK_2B LOG**\n\n"
        f"👤 **العضو:**\n"
        f"{member.display_name}\n\n"
        f"🆔 **ID:**\n"
        f"{member.id}\n\n"
        f"🏷️ **رتبته:**\n"
        f"{rank}\n\n"
        f"🔴 **اللون السابق:**\n"
        f"{old}\n\n"
        f"🟢 **اللون الجديد:**\n"
        f"{new}\n\n"
        f"👮 **بواسطة:**\n"
        f"{who}\n\n"
        f"🔢 **تغييرات اليوم:**\n"
        f"{daily_count}\n\n"
        f"🚫 **تم قفل العضو:**\n"
        f"{'نعم' if was_locked else 'لا'}\n\n"
        f"🕒 **التاريخ:**\n"
        f"{now.strftime('%Y/%m/%d %H:%M:%S UTC')}"
    )

    db.execute(
        """
        INSERT INTO color_history(
            guild_id,
            user_id,
            member_name,
            old_color,
            new_color,
            changed_by,
            changed_at,
            daily_changes,
            was_locked,
            member_rank,
            role_id
        )
        VALUES(?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            guild.id,
            member.id,
            member.display_name,
            str(old),
            str(new),
            str(who),
            now.isoformat(),
            daily_count,
            int(was_locked),
            rank,
            role_id
        )
    )

    db.commit()

    try:

        await channel.send(
            history_text
        )

    except discord.HTTPException:

        pass


# ============================================================
# MEMBER HISTORY
# ============================================================

def get_member_history(guild_id, user_id, limit=20):

    return db.execute(
        """
        SELECT * FROM color_history
        WHERE guild_id=? AND user_id=?
        ORDER BY id DESC
        LIMIT ?
        """,
        (guild_id, user_id, limit)
    ).fetchall()


def get_member_change_count(guild_id, user_id):

    row = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM color_history
        WHERE guild_id=? AND user_id=?
        """,
        (guild_id, user_id)
    ).fetchone()

    return int(row["total"] or 0)


def get_username_change_count(guild_id, user_id):

    row = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM member_name_history
        WHERE guild_id=? AND user_id=?
        """,
        (guild_id, user_id)
    ).fetchone()

    return int(row["total"] or 0)


def format_member_history(member, rows):

    guild_id = member.guild.id
    user_id = member.id
    lock = get_color_lock(guild_id, user_id)
    rank = get_member_rank(member)
    total = get_member_change_count(guild_id, user_id)
    username_changes = get_username_change_count(guild_id, user_id)

    if lock:
        locked = f"🔴 محظور حتى: `{lock.strftime('%Y/%m/%d %H:%M UTC')}`"
    else:
        locked = "🟢 غير محظور"

    text = (
        "📋 **سجل العضو**\n\n"
        f"👤 **الاسم:** {member.display_name}\n"
        f"🆔 **ID:** `{member.id}`\n"
        f"🏷️ **اليوزر:** `{member.name}`\n"
        f"🏆 **الرتبة:** `{rank}`\n"
        f"🔢 **عدد تغييرات اللون:** `{total}`\n"
        f"🔤 **عدد مرات تغيير اليوزر:** `{username_changes}`\n"
        f"🚫 **الحظر:** {locked}\n\n"
    )

    name_rows = db.execute(
        """
        SELECT * FROM member_name_history
        WHERE guild_id=? AND user_id=?
        ORDER BY id DESC
        LIMIT 10
        """,
        (guild_id, user_id)
    ).fetchall()

    if name_rows:
        text += "🔤 **تغييرات اليوزر الأخيرة:**\n\n"
        for row in name_rows:
            text += (
                f"`{row['changed_at']}` — "
                f"`{row['old_username']}` → `{row['new_username']}`\n"
            )
        text += "\n"

    if not rows:
        return text + "📭 لا توجد تغييرات لون مسجلة لهذا العضو."

    text += "🕘 **آخر تغييرات اللون:**\n\n"

    for index, row in enumerate(rows, 1):
        text += (
            f"**#{index}** — `{row['changed_at']}`\n"
            f"🎨 السابق: `{row['old_color']}`\n"
            f"🟢 الجديد: `{row['new_color']}`\n"
            f"👮 بواسطة: `{row['changed_by']}`\n"
            f"📊 تغييرات الساعة/السجل: `{row['daily_changes']}`\n"
            f"{'🔒 تم القفل' if row['was_locked'] else '🔓 بدون قفل'}\n\n"
        )

    return text[:3900]


# ============================================================
# APPLY COLOR
# ============================================================

async def apply_color(
    member,
    value,
    who,
    bypass_limit=False
):

    guild = member.guild

    ensure(
        guild.id
    )

    # --------------------------------------------------------
    # GLOBAL SYSTEM
    # --------------------------------------------------------

    if not get_bool(
        guild.id,
        "bot_on"
    ):
        raise ValueError(
            "⛔ البوت متوقف حاليًا من لوحة التحكم."
        )

    if not get_bool(
        guild.id,
        "system_on"
    ):

        raise ValueError(
            "⛔ نظام الألوان متوقف حاليًا."
        )

    # التغيير الذاتي للأعضاء يخضع لحالة قسم الأعضاء.
    if not bypass_limit and not get_bool(
        guild.id,
        "members_on"
    ):
        raise ValueError(
            "⛔ تم إيقاف تغيير الألوان للأعضاء من لوحة التحكم."
        )

    # --------------------------------------------------------
    # USER LIMIT
    # --------------------------------------------------------

    privileged = (
        bypass_limit
        or is_owner(member.id)
        or is_admin(member)
    )

    if (
        not privileged
        and get_bool(
            guild.id,
            "rate_limit_on"
        )
    ):

        locked_until = get_color_lock(
            guild.id,
            member.id
        )

        if locked_until:

            raise ValueError(
                "🚫 تم إيقاف تغيير الألوان لك مؤقتًا.\n\n"
                f"⏰ يعود النظام:\n"
                f"`{locked_until.strftime('%Y/%m/%d %H:%M UTC')}`\n\n"
                "المالك والإدارة غير خاضعين لهذا الحد."
            )

        usage = get_hourly_usage(
            guild.id,
            member.id
        )

        if usage >= MAX_USER_CHANGES_PER_HOUR:

            until = lock_user_until_tomorrow(
                guild.id,
                member.id
            )

            daily = get_daily_usage(
                guild.id,
                member.id
            )

            await write_log(
                guild,
                member,
                "N/A",
                "RATE LIMIT",
                who,
                was_locked=True
            )

            raise ValueError(
                "🚫 تم تجاوز الحد المسموح.\n\n"
                f"استخدمت **{usage}** تغييرات خلال آخر ساعة.\n"
                f"تم قفل تغيير الألوان حتى:\n"
                f"`{until.strftime('%Y/%m/%d %H:%M UTC')}`\n\n"
                f"📊 تغييرات اليوم: `{daily}`"
            )

    # --------------------------------------------------------
    # PARSE
    # --------------------------------------------------------

    spec = parse_color(
        value
    )

    # --------------------------------------------------------
    # GRADIENT CHECK
    # --------------------------------------------------------

    if spec["type"] == "gradient":

        if not gradient_available(
            guild
        ):

            raise GradientNotEnabled()

    # --------------------------------------------------------
    # ROLE
    # --------------------------------------------------------

    role = await color_role(
        member
    )

    old_color = (
        f"{role.colour}"
    )

    # --------------------------------------------------------
    # SOLID
    # --------------------------------------------------------

    if spec["type"] == "solid":

        primary = hex_to_int(
            spec["colors"][0]
        )

        await role.edit(
            name=f"COLOR • {member.display_name}"[:100],
            colour=discord.Colour(
                primary
            ),
            secondary_colour=None,
            tertiary_colour=None,
            reason="COLORS_SOK_2B solid color"
        )

    # --------------------------------------------------------
    # GRADIENT
    # --------------------------------------------------------

    elif spec["type"] == "gradient":

        primary = hex_to_int(
            spec["colors"][0]
        )

        secondary = hex_to_int(
            spec["colors"][1]
        )

        await role.edit(
            name=f"COLOR • {member.display_name}"[:100],
            colour=discord.Colour(
                primary
            ),
            secondary_colour=discord.Colour(
                secondary
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
            reason="COLORS_SOK_2B color role"
        )

    # --------------------------------------------------------
    # USAGE
    # --------------------------------------------------------

    if not privileged:

        register_color_usage(
            guild.id,
            member.id
        )

    # --------------------------------------------------------
    # LOG
    # --------------------------------------------------------

    await write_log(
        guild,
        member,
        old_color,
        spec["label"],
        who
    )

    return spec


# ============================================================
# GRADIENT ERROR
# ============================================================

class GradientNotEnabled(
    Exception
):
    pass


# ============================================================
# GRADIENT CHECK VIEW
# ============================================================

class GradientCheckView(
    discord.ui.View
):

    def __init__(
        self,
        guild_id
    ):

        super().__init__(
            timeout=180
        )

        self.guild_id = guild_id

    @discord.ui.button(
        label="🔄 تحقق الآن",
        style=discord.ButtonStyle.success
    )
    async def check(
        self,
        interaction,
        button
    ):

        if not interaction.guild:

            return await interaction.response.send_message(
                "❌ داخل السيرفر فقط.",
                ephemeral=True
            )

        if gradient_available(
            interaction.guild
        ):

            await interaction.response.edit_message(
                content=(
                    "✅ **تم اكتشاف Enhanced Role Colors!**\n\n"
                    "يمكن الآن استخدام التدرجات بلونين.\n\n"
                    "مثال:\n"
                    "`#C86BFF #FFD900`"
                ),
                view=None
            )

        else:

            await interaction.response.send_message(
                "❌ ما زالت الميزة غير متاحة في السيرفر.",
                ephemeral=True
            )

    @discord.ui.button(
        label="📖 طريقة التفعيل",
        style=discord.ButtonStyle.secondary
    )
    async def guide(
        self,
        interaction,
        button
    ):

        await interaction.response.send_message(
            gradient_help_text(),
            ephemeral=True
        )


# ============================================================
# MAIN OWNER VIEW
# ============================================================

class OwnerView(
    discord.ui.View
):

    def __init__(
        self
    ):

        super().__init__(
            timeout=None
        )

    async def allowed(
        self,
        interaction
    ):

        if not is_owner(
            interaction.user.id
        ):

            await interaction.response.send_message(
                "❌ غير مصرح.",
                ephemeral=True
            )

            return False

        if not interaction.guild:

            await interaction.response.send_message(
                "❌ داخل السيرفر فقط.",
                ephemeral=True
            )

            return False

        return True

    @discord.ui.button(
        label="🎨 الأعضاء",
        style=discord.ButtonStyle.primary,
        row=0
    )
    async def members(
        self,
        interaction,
        button
    ):

        if not await self.allowed(
            interaction
        ):
            return

        await interaction.response.edit_message(
            content=dashboard_text(
                interaction.guild,
                "members"
            ),
            view=MembersView()
        )

    @discord.ui.button(
        label="👑 الإدارة",
        style=discord.ButtonStyle.secondary,
        row=0
    )
    async def admins(
        self,
        interaction,
        button
    ):

        if not await self.allowed(
            interaction
        ):
            return

        await interaction.response.edit_message(
            content=dashboard_text(
                interaction.guild,
                "admins"
            ),
            view=AdminsView()
        )

    @discord.ui.button(
        label="🤖 النظام",
        style=discord.ButtonStyle.success,
        row=0
    )
    async def system(
        self,
        interaction,
        button
    ):

        if not await self.allowed(
            interaction
        ):
            return

        await interaction.response.edit_message(
            content=dashboard_text(
                interaction.guild,
                "system"
            ),
            view=SystemView()
        )

    @discord.ui.button(
        label="📋 LOG",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def log(
        self,
        interaction,
        button
    ):

        if not await self.allowed(
            interaction
        ):
            return

        await interaction.response.edit_message(
            content=dashboard_text(
                interaction.guild,
                "log"
            ),
            view=LogView()
        )

    @discord.ui.button(
        label="⛔ إيقاف البوت",
        style=discord.ButtonStyle.danger,
        row=1
    )
    async def stop(
        self,
        interaction,
        button
    ):

        if not await self.allowed(
            interaction
        ):
            return

        await interaction.response.edit_message(
            content=(
                "⛔ **إيقاف البوت**\n\n"
                "هل أنت متأكد من إيقاف وظائف البوت في هذا السيرفر؟\n\n"
                "سيبقى البوت متصلًا، ويمكن تشغيله مباشرة من نفس اللوحة."
            ),
            view=StopView()
        )

    @discord.ui.button(
        label="🎨 تعيين لون لعضو",
        style=discord.ButtonStyle.primary,
        row=2
    )
    async def manual_color(
        self,
        interaction,
        button
    ):

        if not await self.allowed(
            interaction
        ):
            return

        await interaction.response.send_modal(
            ManualColorModal(
                interaction.guild.id
            )
        )

    @discord.ui.button(
        label="🏆 رفع عضو",
        style=discord.ButtonStyle.secondary,
        row=2
    )
    async def rank_user(
        self,
        interaction,
        button
    ):

        if not await self.allowed(
            interaction
        ):
            return

        await interaction.response.send_modal(
            RankUserModal()
        )


    @discord.ui.button(
        label="🟢 تشغيل البوت",
        style=discord.ButtonStyle.success,
        row=3
    )
    async def start_bot(
        self,
        interaction,
        button
    ):

        if not await self.allowed(interaction):
            return

        put(
            interaction.guild.id,
            "bot_on",
            True
        )

        await interaction.response.edit_message(
            content=dashboard_text(interaction.guild),
            view=self
        )

        await interaction.followup.send(
            "🟢 تم تشغيل وظائف البوت في هذا السيرفر مباشرة.",
            ephemeral=True
        )


# ============================================================
# DASHBOARD TEXT
# ============================================================

def status(
    value
):

    return "🟢 مفعّل" if value else "🔴 متوقف"


def dashboard_text(
    guild,
    section=None
):

    ensure(
        guild.id
    )

    members = status(
        get_bool(
            guild.id,
            "members_on"
        )
    )

    admins = status(
        get_bool(
            guild.id,
            "admins_on"
        )
    )

    system = status(
        get_bool(
            guild.id,
            "system_on"
        )
    )

    log = status(
        get_bool(
            guild.id,
            "log_on"
        )
    )

    bot_status = status(
        get_bool(
            guild.id,
            "bot_on"
        )
    )

    rate = status(
        get_bool(
            guild.id,
            "rate_limit_on"
        )
    )

    channel_id = get_log_channel(
        guild.id
    )

    gradient = (
        "🟢 متاح"
        if gradient_available(guild)
        else "🔴 غير متاح"
    )

    if section == "members":

        return (
            "🎨 **قسم الأعضاء**\n\n"
            f"حالة تغيير الألوان للأعضاء: {members}\n\n"
            "عند الإيقاف لن يستطيع العضو تغيير لونه بنفسه.\n"
            "المالك والإدارة يستطيعون الاستمرار باستخدام لوحة التحكم."
        )

    if section == "admins":

        return (
            "👑 **قسم الإدارة**\n\n"
            f"حالة أوامر الإدارة: {admins}\n\n"
            "الإدارة تستطيع تعيين لون لأي عضو.\n"
            "الإدارة والمالك غير خاضعين لحد التغييرات."
        )

    if section == "system":

        return (
            "🤖 **قسم النظام**\n\n"
            f"النظام: {system}\n\n"
            f"حد التغييرات: {rate}\n"
            f"التدرجات: {gradient}\n\n"
            "الحد الافتراضي:\n"
            "5 تغييرات خلال ساعة للعضو العادي.\n"
            "عند تجاوز الحد يتم قفل تغيير اللون حتى اليوم التالي."
        )

    if section == "log":

        return (
            "📋 **قسم LOG**\n\n"
            f"حالة LOG: {log}\n\n"
            f"القناة الحالية: "
            f"{f'<#{channel_id}>' if channel_id else 'غير محددة'}\n\n"
            "يسجل:\n"
            "• اسم العضو\n"
            "• ID\n"
            "• الرتبة\n"
            "• اللون السابق\n"
            "• اللون الجديد\n"
            "• من قام بالتغيير\n"
            "• عدد تغييرات اليوم\n"
            "• هل تم قفل العضو\n"
            "• التاريخ والوقت"
        )

    return (
        "👑 **لوحة تحكم COLORS_SOK_2B**\n\n"
        f"🎨 الأعضاء: {members}\n"
        f"👑 الإدارة: {admins}\n"
        f"🤖 البوت: {bot_status}\n"
        f"⚙️ النظام: {system}\n"
        f"📋 LOG: {log}\n"
        f"🌈 التدرج: {gradient}\n\n"
        "🛠️ الأدوات:\n"
        "• تعيين لون لعضو\n"
        "• رفع عضو لرتبة\n"
        "• إدارة الحد اليومي\n"
        "• إدارة LOG\n\n"
        "اختر القسم الذي تريد التحكم به."
    )


# ============================================================
# BACK BUTTON
# ============================================================

class BackButton:

    @staticmethod
    async def back(
        interaction
    ):

        await interaction.response.edit_message(
            content=dashboard_text(
                interaction.guild
            ),
            view=OwnerView()
        )


# ============================================================
# MEMBERS VIEW
# ============================================================

class MembersView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="🟢 تفعيل",
        style=discord.ButtonStyle.success
    )
    async def enable(
        self,
        interaction,
        button
    ):

        if not is_owner(
            interaction.user.id
        ):
            return await interaction.response.send_message(
                "❌ غير مصرح.",
                ephemeral=True
            )

        put(
            interaction.guild.id,
            "members_on",
            True
        )

        await interaction.response.edit_message(
            content=dashboard_text(
                interaction.guild,
                "members"
            ),
            view=self
        )

        await interaction.followup.send(
            "🟢 تم تفعيل قسم الأعضاء. يستطيع الأعضاء تغيير ألوانهم الآن.",
            ephemeral=True
        )

    @discord.ui.button(
        label="🔴 إيقاف",
        style=discord.ButtonStyle.danger
    )
    async def disable(
        self,
        interaction,
        button
    ):

        if not is_owner(
            interaction.user.id
        ):
            return await interaction.response.send_message(
                "❌ غير مصرح.",
                ephemeral=True
            )

        put(
            interaction.guild.id,
            "members_on",
            False
        )

        await interaction.response.edit_message(
            content=dashboard_text(
                interaction.guild,
                "members"
            ),
            view=self
        )

        await interaction.followup.send(
            "🔴 تم إيقاف قسم الأعضاء. تم منع تغيير الألوان الذاتي فورًا.",
            ephemeral=True
        )

    @discord.ui.button(
        label="↩️ رجوع",
        style=discord.ButtonStyle.secondary
    )
    async def back(
        self,
        interaction,
        button
    ):

        await BackButton.back(
            interaction
        )


# ============================================================
# ADMINS VIEW
# ============================================================

class AdminsView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="🟢 تفعيل",
        style=discord.ButtonStyle.success
    )
    async def enable(
        self,
        interaction,
        button
    ):

        if not is_owner(
            interaction.user.id
        ):
            return await interaction.response.send_message(
                "❌ غير مصرح.",
                ephemeral=True
            )

        put(
            interaction.guild.id,
            "admins_on",
            True
        )

        await interaction.response.edit_message(
            content=dashboard_text(
                interaction.guild,
                "admins"
            ),
            view=self
        )

        await interaction.followup.send(
            "🟢 تم تفعيل أوامر الإدارة.",
            ephemeral=True
        )

    @discord.ui.button(
        label="🔴 إيقاف",
        style=discord.ButtonStyle.danger
    )
    async def disable(
        self,
        interaction,
        button
    ):

        if not is_owner(
            interaction.user.id
        ):
            return await interaction.response.send_message(
                "❌ غير مصرح.",
                ephemeral=True
            )

        put(
            interaction.guild.id,
            "admins_on",
            False
        )

        await interaction.response.edit_message(
            content=dashboard_text(
                interaction.guild,
                "admins"
            ),
            view=self
        )

        await interaction.followup.send(
            "🔴 تم إيقاف أوامر الإدارة.",
            ephemeral=True
        )

    @discord.ui.button(
        label="↩️ رجوع",
        style=discord.ButtonStyle.secondary
    )
    async def back(
        self,
        interaction,
        button
    ):

        await BackButton.back(
            interaction
        )


# ============================================================
# SYSTEM VIEW
# ============================================================

class SystemView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="🟢 تفعيل النظام",
        style=discord.ButtonStyle.success,
        row=0
    )
    async def enable_system(
        self,
        interaction,
        button
    ):

        if not is_owner(
            interaction.user.id
        ):
            return await interaction.response.send_message(
                "❌ غير مصرح.",
                ephemeral=True
            )

        put(
            interaction.guild.id,
            "system_on",
            True
        )

        await interaction.response.edit_message(
            content=dashboard_text(
                interaction.guild,
                "system"
            ),
            view=self
        )

        await interaction.followup.send(
            "🟢 تم تفعيل نظام الألوان.",
            ephemeral=True
        )

    @discord.ui.button(
        label="🔴 إيقاف النظام",
        style=discord.ButtonStyle.danger,
        row=0
    )
    async def disable_system(
        self,
        interaction,
        button
    ):

        if not is_owner(
            interaction.user.id
        ):
            return await interaction.response.send_message(
                "❌ غير مصرح.",
                ephemeral=True
            )

        put(
            interaction.guild.id,
            "system_on",
            False
        )

        await interaction.response.edit_message(
            content=dashboard_text(
                interaction.guild,
                "system"
            ),
            view=self
        )

        await interaction.followup.send(
            "🔴 تم إيقاف نظام الألوان بالكامل.",
            ephemeral=True
        )

    @discord.ui.button(
        label="🛡️ الحد 5/ساعة",
        style=discord.ButtonStyle.primary,
        row=1
    )
    async def rate(
        self,
        interaction,
        button
    ):

        if not is_owner(
            interaction.user.id
        ):
            return await interaction.response.send_message(
                "❌ غير مصرح.",
                ephemeral=True
            )

        v = not get_bool(
            interaction.guild.id,
            "rate_limit_on"
        )

        put(
            interaction.guild.id,
            "rate_limit_on",
            v
        )

        await interaction.response.edit_message(
            content=dashboard_text(
                interaction.guild,
                "system"
            ),
            view=self
        )

        await interaction.followup.send(
            "🟢 تم تفعيل حد 5 تغييرات/ساعة." if v else "🔴 تم إيقاف حد 5 تغييرات/ساعة.",
            ephemeral=True
        )

    @discord.ui.button(
        label="↩️ رجوع",
        style=discord.ButtonStyle.secondary,
        row=2
    )
    async def back(
        self,
        interaction,
        button
    ):

        await BackButton.back(
            interaction
        )


# ============================================================
# LOG VIEW
# ============================================================

class LogView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="🟢 تفعيل LOG",
        style=discord.ButtonStyle.success,
        row=0
    )
    async def enable(
        self,
        interaction,
        button
    ):

        if not is_owner(
            interaction.user.id
        ):
            return await interaction.response.send_message(
                "❌ غير مصرح.",
                ephemeral=True
            )

        put(
            interaction.guild.id,
            "log_on",
            True
        )

        await interaction.response.edit_message(
            content=dashboard_text(
                interaction.guild,
                "log"
            ),
            view=self
        )

        await interaction.followup.send(
            "🟢 تم تفعيل LOG.",
            ephemeral=True
        )

    @discord.ui.button(
        label="🔴 إيقاف LOG",
        style=discord.ButtonStyle.danger,
        row=0
    )
    async def disable(
        self,
        interaction,
        button
    ):

        if not is_owner(
            interaction.user.id
        ):
            return await interaction.response.send_message(
                "❌ غير مصرح.",
                ephemeral=True
            )

        put(
            interaction.guild.id,
            "log_on",
            False
        )

        await interaction.response.edit_message(
            content=dashboard_text(
                interaction.guild,
                "log"
            ),
            view=self
        )

        await interaction.followup.send(
            "🔴 تم إيقاف LOG.",
            ephemeral=True
        )

    @discord.ui.button(
        label="📋 تعيين هذه القناة",
        style=discord.ButtonStyle.primary,
        row=1
    )
    async def set_channel(
        self,
        interaction,
        button
    ):

        if not is_owner(
            interaction.user.id
        ):
            return await interaction.response.send_message(
                "❌ غير مصرح.",
                ephemeral=True
            )

        put(
            interaction.guild.id,
            "log_channel",
            interaction.channel.id
        )

        await interaction.response.edit_message(
            content=dashboard_text(
                interaction.guild,
                "log"
            ),
            view=self
        )


    @discord.ui.button(
        label="👤 عرض سجل عضو",
        style=discord.ButtonStyle.primary,
        row=2
    )
    async def member_history(
        self,
        interaction,
        button
    ):

        if not is_owner(interaction.user.id):
            return await interaction.response.send_message(
                "❌ غير مصرح.",
                ephemeral=True
            )

        await interaction.response.send_modal(
            MemberHistoryModal()
        )


    @discord.ui.button(
        label="↩️ رجوع",
        style=discord.ButtonStyle.secondary,
        row=3
    )
    async def back(
        self,
        interaction,
        button
    ):

        await BackButton.back(
            interaction
        )


# ============================================================
# STOP VIEW
# ============================================================

class StopView(
    discord.ui.View
):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="⛔ إيقاف البوت الآن",
        style=discord.ButtonStyle.danger
    )
    async def confirm(
        self,
        interaction,
        button
    ):

        if not is_owner(
            interaction.user.id
        ):
            return await interaction.response.send_message(
                "❌ غير مصرح.",
                ephemeral=True
            )

        put(
            interaction.guild.id,
            "bot_on",
            False
        )

        await interaction.response.edit_message(
            content=dashboard_text(interaction.guild),
            view=OwnerView()
        )

        await interaction.followup.send(
            "🔴 تم إيقاف وظائف البوت في هذا السيرفر مباشرة.\n"
            "يمكنك تشغيله من زر **🟢 تشغيل البوت**.",
            ephemeral=True
        )

    @discord.ui.button(
        label="↩️ إلغاء",
        style=discord.ButtonStyle.secondary
    )
    async def cancel(
        self,
        interaction,
        button
    ):

        await interaction.response.edit_message(
            content=dashboard_text(
                interaction.guild
            ),
            view=OwnerView()
        )


# ============================================================
# MANUAL COLOR MODAL
# ============================================================

class ManualColorModal(
    discord.ui.Modal,
    title="🎨 تعيين لون لعضو"
):

    user_id = discord.ui.TextInput(
        label="ID العضو",
        placeholder="1531577881548034100",
        required=True,
        max_length=25
    )

    color = discord.ui.TextInput(
        label="اللون / التدرج",
        placeholder="#7A00FF #FF00A8",
        required=True,
        max_length=300
    )

    async def on_submit(
        self,
        interaction
    ):

        if not is_owner(
            interaction.user.id
        ):

            return await interaction.response.send_message(
                "❌ غير مصرح.",
                ephemeral=True
            )

        if not self.user_id.value.isdigit():

            return await interaction.response.send_message(
                "❌ ID غير صحيح.",
                ephemeral=True
            )

        member = interaction.guild.get_member(
            int(
                self.user_id.value
            )
        )

        if member is None:

            try:

                member = await interaction.guild.fetch_member(
                    int(
                        self.user_id.value
                    )
                )

            except discord.HTTPException:

                member = None

        if member is None:

            return await interaction.response.send_message(
                "❌ العضو غير موجود.",
                ephemeral=True
            )

        await interaction.response.defer(
            ephemeral=True
        )

        try:

            spec = await apply_color(
                member,
                self.color.value,
                interaction.user.display_name,
                bypass_limit=True
            )

            await interaction.followup.send(
                "✅ **تم تعيين اللون بنجاح.**\n\n"
                f"👤 {member.mention}\n"
                f"🎨 {spec['label']}",
                ephemeral=True
            )

        except GradientNotEnabled:

            await interaction.followup.send(
                gradient_help_text(),
                view=GradientCheckView(
                    interaction.guild.id
                ),
                ephemeral=True
            )

        except ValueError as e:

            await interaction.followup.send(
                str(e),
                ephemeral=True
            )

        except discord.Forbidden:

            await interaction.followup.send(
                "❌ البوت لا يملك صلاحية إدارة الرتب.\n\n"
                "تأكد أن:\n"
                "• Manage Roles مفعلة للبوت.\n"
                "• رتبة البوت أعلى من رتبة COLOR.",
                ephemeral=True
            )

        except Exception:

            logging.exception(
                "Manual color error"
            )

            await interaction.followup.send(
                "❌ حدث خطأ أثناء تطبيق اللون.",
                ephemeral=True
            )


# ============================================================
# MEMBER HISTORY MODAL
# ============================================================

class MemberHistoryModal(
    discord.ui.Modal,
    title="📋 عرض سجل عضو"
):

    user_id = discord.ui.TextInput(
        label="ID العضو",
        placeholder="ضع ID العضو هنا",
        required=True,
        max_length=25
    )

    async def on_submit(self, interaction):

        if not is_owner(interaction.user.id):
            return await interaction.response.send_message(
                "❌ غير مصرح.",
                ephemeral=True
            )

        if not self.user_id.value.isdigit():
            return await interaction.response.send_message(
                "❌ ID غير صحيح.",
                ephemeral=True
            )

        user_id = int(self.user_id.value)
        member = interaction.guild.get_member(user_id)

        if member is None:
            try:
                member = await interaction.guild.fetch_member(user_id)
            except discord.HTTPException:
                member = None

        if member is None:
            return await interaction.response.send_message(
                "❌ العضو غير موجود في السيرفر.",
                ephemeral=True
            )

        rows = get_member_history(
            interaction.guild.id,
            member.id,
            20
        )

        await interaction.response.send_message(
            format_member_history(member, rows),
            ephemeral=True
        )


# ============================================================
# RANK USER MODAL
# ============================================================

class RankUserModal(
    discord.ui.Modal,
    title="🏆 رفع عضو"
):

    user_id = discord.ui.TextInput(
        label="ID العضو",
        placeholder="ضع ID العضو",
        required=True,
        max_length=25
    )

    async def on_submit(
        self,
        interaction
    ):

        if not is_owner(
            interaction.user.id
        ):

            return await interaction.response.send_message(
                "❌ غير مصرح.",
                ephemeral=True
            )

        if not self.user_id.value.isdigit():

            return await interaction.response.send_message(
                "❌ ID غير صحيح.",
                ephemeral=True
            )

        member = interaction.guild.get_member(
            int(
                self.user_id.value
            )
        )

        if member is None:

            try:

                member = await interaction.guild.fetch_member(
                    int(
                        self.user_id.value
                    )
                )

            except discord.HTTPException:

                member = None

        if member is None:

            return await interaction.response.send_message(
                "❌ العضو غير موجود.",
                ephemeral=True
            )

        await interaction.response.send_message(
            f"👤 **العضو:** {member.mention}\n\n"
            "🏆 اختر الرتبة التي تريد إعطاءها له:",
            view=RankSelectView(
                member
            ),
            ephemeral=True
        )


# ============================================================
# RANK SELECT VIEW
# ============================================================

class RankSelectView(
    discord.ui.View
):

    def __init__(
        self,
        member
    ):

        super().__init__(
            timeout=300
        )

        self.member = member

        options = []

        for rank in RANKS:

            options.append(
                discord.SelectOption(
                    label=rank,
                    value=rank
                )
            )

        self.select = discord.ui.Select(
            placeholder="اختر الرتبة",
            options=options
        )

        self.select.callback = self.select_callback

        self.add_item(
            self.select
        )

    async def select_callback(
        self,
        interaction
    ):

        if not is_owner(
            interaction.user.id
        ):

            return await interaction.response.send_message(
                "❌ غير مصرح.",
                ephemeral=True
            )

        rank = self.select.values[0]

        try:

            role = await assign_rank(
                self.member,
                rank
            )

            if role is None:
                content = (
                    "✅ **تم تنزيل العضو بنجاح.**\n\n"
                    f"👤 {self.member.mention}\n"
                    "🏆 الرتبة الحالية: `Member`\n"
                    "تمت إزالة جميع رتب SOKO السابقة."
                )
            else:
                content = (
                    "✅ **تم رفع العضو بنجاح.**\n\n"
                    f"👤 {self.member.mention}\n"
                    f"🏆 الرتبة: `{rank}`\n"
                    f"🎭 {role.mention}"
                )

            await interaction.response.edit_message(
                content=content,
                view=None
            )

        except discord.Forbidden:

            await interaction.response.send_message(
                "❌ البوت لا يستطيع إدارة هذه الرتبة.\n\n"
                "ضع رتبة البوت فوق رتب SOKO.",
                ephemeral=True
            )

        except Exception:

            logging.exception(
                "Rank assignment error"
            )

            await interaction.response.send_message(
                "❌ حدث خطأ أثناء إعطاء الرتبة.",
                ephemeral=True
            )


# ============================================================
# /COLORS
# ============================================================

@bot.tree.command(
    name="colors",
    description="عرض نظام الألوان"
)
async def colors_cmd(
    interaction
):

    if not interaction.guild:

        return await interaction.response.send_message(
            "❌ استخدم الأمر داخل السيرفر.",
            ephemeral=True
        )

    if not get_bool(
        interaction.guild.id,
        "bot_on"
    ):

        return await interaction.response.send_message(
            "⛔ تم إيقاف البوت في هذا السيرفر بواسطة لوحة التحكم.",
            ephemeral=True
        )

    if not get_bool(
        interaction.guild.id,
        "system_on"
    ):

        return await interaction.response.send_message(
            "⛔ تم إيقاف نظام الألوان بواسطة لوحة التحكم.",
            ephemeral=True
        )

    if not get_bool(
        interaction.guild.id,
        "members_on"
    ):

        return await interaction.response.send_message(
            "⛔ تم إيقاف قسم الأعضاء. تغيير اللون الذاتي غير متاح حاليًا.",
            ephemeral=True
        )

    gradient_status = (
        "🟢 متاح"
        if gradient_available(
            interaction.guild
        )
        else "🔴 غير متاح - يحتاج Enhanced Role Styles"
    )

    text = (
        "🎨 **COLORS_SOK_2B**\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        "🎨 **لون واحد**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "`27`\n"
        "`#C86BFF`\n"
        "`بنفسجي فاتح`\n"
        "`نيون #39FF14`\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        "🌈 **تدرج بلونين**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "`#C86BFF #FFD900`\n"
        "`تدرج #C86BFF + #FFD900`\n"
        "`بنفسجي فاتح + أصفر ليموني`\n\n"

        f"حالة التدرج: {gradient_status}\n\n"

        "━━━━━━━━━━━━━━━━━━\n"
        "⏱️ **حد العضو**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "العضو العادي يستطيع تغيير اللون "
        "حتى 5 مرات خلال ساعة.\n"
        "بعد تجاوز الحد يتم قفل تغيير اللون "
        "حتى اليوم التالي.\n\n"

        "👑 المالك والإدارة مستثنون من الحد."
    )

    if not os.path.exists(
        IMAGE
    ):

        return await interaction.response.send_message(
            text,
            ephemeral=True
        )

    await interaction.response.send_message(
        text,
        file=discord.File(
            IMAGE
        ),
        ephemeral=True
    )


# ============================================================
# /SETCOLOR
# ============================================================

@bot.tree.command(
    name="setcolor",
    description="تغيير لون عضو - الإدارة"
)
@app_commands.describe(
    user_id="ID العضو"
)
async def setcolor(
    interaction,
    user_id: str
):

    if not interaction.guild:

        return await interaction.response.send_message(
            "❌ داخل السيرفر فقط.",
            ephemeral=True
        )

    if not is_admin(
        interaction.user
    ):

        return await interaction.response.send_message(
            "❌ هذا الأمر للإدارة فقط.",
            ephemeral=True
        )

    if not get_bool(
        interaction.guild.id,
        "bot_on"
    ):
        return await interaction.response.send_message(
            "⛔ تم إيقاف البوت في هذا السيرفر.",
            ephemeral=True
        )

    if not get_bool(
        interaction.guild.id,
        "system_on"
    ):
        return await interaction.response.send_message(
            "⛔ نظام الألوان متوقف حاليًا.",
            ephemeral=True
        )

    if not get_bool(
        interaction.guild.id,
        "admins_on"
    ):

        return await interaction.response.send_message(
            "⛔ أوامر الإدارة متوقفة.",
            ephemeral=True
        )

    if not user_id.isdigit():

        return await interaction.response.send_message(
            "❌ ID غير صحيح.",
            ephemeral=True
        )

    member = interaction.guild.get_member(
        int(user_id)
    )

    if member is None:

        try:

            member = await interaction.guild.fetch_member(
                int(user_id)
            )

        except discord.HTTPException:

            member = None

    if member is None:

        return await interaction.response.send_message(
            "❌ العضو غير موجود.",
            ephemeral=True
        )

    await interaction.response.send_message(
        f"👤 {member.mention}\n\n"
        "🎨 أرسل اللون أو التدرج في نفس القناة.\n\n"
        "أمثلة:\n"
        "`27`\n"
        "`#7A00FF`\n"
        "`#7A00FF #FF00A8`\n"
        "`بنفسجي فاتح + وردي نيون`\n\n"
        "⏳ لديك 120 ثانية.",
        ephemeral=True
    )

    def check(
        message
    ):

        return (
            message.author.id
            == interaction.user.id
            and message.channel.id
            == interaction.channel.id
            and message.guild
            and message.guild.id
            == interaction.guild.id
        )

    try:

        message = await bot.wait_for(
            "message",
            timeout=120,
            check=check
        )

        try:

            spec = await apply_color(
                member,
                message.content,
                interaction.user.display_name,
                bypass_limit=True
            )

        except GradientNotEnabled:

            await interaction.followup.send(
                gradient_help_text(),
                view=GradientCheckView(
                    interaction.guild.id
                ),
                ephemeral=True
            )

            return

        try:

            await message.delete()

        except discord.HTTPException:

            pass

        await interaction.followup.send(
            "✅ **تم تطبيق اللون.**\n\n"
            f"👤 {member.mention}\n"
            f"🎨 {spec['label']}",
            ephemeral=True
        )

    except asyncio.TimeoutError:

        await interaction.followup.send(
            "⌛ انتهى الوقت.",
            ephemeral=True
        )

    except ValueError as e:

        await interaction.followup.send(
            str(e),
            ephemeral=True
        )

    except discord.Forbidden:

        await interaction.followup.send(
            "❌ البوت لا يملك صلاحية إدارة الرتب.",
            ephemeral=True
        )

    except Exception:

        logging.exception(
            "setcolor error"
        )

        await interaction.followup.send(
            "❌ حدث خطأ.",
            ephemeral=True
        )


# ============================================================
# /SOKO_IDMIN
# ============================================================

@bot.tree.command(
    name="soko_idmin",
    description="لوحة تحكم COLORS_SOK_2B"
)
async def soko_idmin(
    interaction
):

    if not is_owner(
        interaction.user.id
    ):

        return await interaction.response.send_message(
            "❌ هذا الأمر خاص بمالك البوت.",
            ephemeral=True
        )

    if not interaction.guild:

        return await interaction.response.send_message(
            "❌ داخل السيرفر فقط.",
            ephemeral=True
        )

    await interaction.response.send_modal(
        OwnerModal()
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
        required=True,
        max_length=100
    )

    async def on_submit(
        self,
        interaction
    ):

        if not is_owner(
            interaction.user.id
        ):

            return await interaction.response.send_message(
                "❌ غير مصرح.",
                ephemeral=True
            )

        if str(
            self.code
        ) != OWNER_CODE:

            return await interaction.response.send_message(
                "❌ رمز غير صحيح.",
                ephemeral=True
            )

        if not interaction.guild:

            return await interaction.response.send_message(
                "❌ داخل السيرفر فقط.",
                ephemeral=True
            )

        await interaction.response.send_message(
            dashboard_text(
                interaction.guild
            ),
            view=OwnerView(),
            ephemeral=True
        )


# ============================================================
# /HELP
# ============================================================

@bot.tree.command(
    name="help",
    description="مساعدة COLORS_SOK_2B"
)
async def help_cmd(
    interaction
):

    await interaction.response.send_message(
        "🎨 **COLORS_SOK_2B**\n\n"

        "🎨 `/colors`\n"
        "عرض نظام الألوان.\n\n"

        "🛠️ `/setcolor ID`\n"
        "تغيير لون عضو للإدارة.\n\n"

        "👑 `/soko_idmin`\n"
        "لوحة تحكم المالك.\n\n"

        "━━━━━━━━━━━━━━━━━━\n\n"

        "**لون واحد:**\n"
        "`27`\n"
        "`#C86BFF`\n"
        "`بنفسجي فاتح`\n\n"

        "**لونان:**\n"
        "`#C86BFF #FFD900`\n"
        "`بنفسجي فاتح + أصفر ليموني`\n\n"

        "**نيون:**\n"
        "`نيون #39FF14`\n"
        "`neon #B026FF`",
        ephemeral=True
    )


# ============================================================
# MEMBER PROFILE / USERNAME HISTORY
# ============================================================

@bot.event
async def on_member_update(before, after):

    if before.name == after.name and before.display_name == after.display_name:
        return

    ensure(after.guild.id)

    now = datetime.now(timezone.utc).isoformat()

    db.execute(
        """
        INSERT INTO member_name_history(
            guild_id, user_id, old_username, new_username,
            old_display_name, new_display_name, changed_at
        ) VALUES(?,?,?,?,?,?,?)
        """,
        (
            after.guild.id,
            after.id,
            before.name,
            after.name,
            before.display_name,
            after.display_name,
            now
        )
    )
    db.commit()


# ============================================================
# ON GUILD JOIN
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

    channel = guild.system_channel

    if channel is None:

        for ch in guild.text_channels:

            try:

                if ch.permissions_for(
                    guild.me
                ).send_messages:

                    channel = ch
                    break

            except Exception:

                continue

    if channel is not None:

        try:

            await channel.send(
                "🎨 **COLORS_SOK_2B متصل الآن!**\n\n"
                "استخدم `/colors` لمعرفة طريقة الألوان.\n"
                "استخدم `/help` للمساعدة.\n"
                "استخدم `/soko_idmin` للوحة المالك."
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

    if not message.guild:

        return await bot.process_commands(
            message
        )

    guild = message.guild

    ensure(
        guild.id
    )

    # --------------------------------------------------------
    # BOT / SYSTEM
    # --------------------------------------------------------

    if not get_bool(
        guild.id,
        "bot_on"
    ):

        return await bot.process_commands(
            message
        )

    if not get_bool(
        guild.id,
        "system_on"
    ):

        return await bot.process_commands(
            message
        )

    # --------------------------------------------------------
    # MEMBER COLOR SYSTEM
    # --------------------------------------------------------

    if get_bool(
        guild.id,
        "members_on"
    ):

        raw = message.content.strip()

        if len(raw) <= 300:

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
                            f"🌈 {message.author.mention}\n"
                            f"تم تطبيق التدرج:\n"
                            f"`{spec['colors'][0]}` → "
                            f"`{spec['colors'][1]}`",
                            delete_after=8
                        )

                    else:

                        await message.channel.send(
                            f"✅ {message.author.mention}\n"
                            f"تم تغيير لونك إلى "
                            f"`{spec['colors'][0]}`.",
                            delete_after=8
                        )

                    return

                except GradientNotEnabled:

                    await message.channel.send(
                        f"{message.author.mention}\n\n"
                        "🌈 **التدرج غير مفعّل في هذا السيرفر.**\n\n"
                        "يجب على مالك/إدارة السيرفر تفعيل "
                        "**Enhanced Role Styles** أولًا.\n\n"
                        "بعدها يمكن استخدام:\n"
                        "`#C86BFF #FFD900`",
                        delete_after=15
                    )

                    return

                except ValueError as e:

                    await message.channel.send(
                        f"{message.author.mention}\n"
                        f"{e}",
                        delete_after=12
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
                        "Member color error"
                    )

                    await message.channel.send(
                        "❌ حدث خطأ أثناء تغيير اللون.",
                        delete_after=8
                    )

                    return

    await bot.process_commands(
        message
    )


# ============================================================
# READY
# ============================================================

@bot.event
async def on_ready():

    init()

    cleanup_old_usage()

    logging.info(
        "===================================="
    )

    logging.info(
        f"COLORS_SOK_2B ONLINE: {bot.user}"
    )

    logging.info(
        f"Guilds: {len(bot.guilds)}"
    )

    for guild in bot.guilds:

        ensure(
            guild.id
        )

        logging.info(
            f"Guild: {guild.name} | "
            f"Gradient: "
            f"{gradient_available(guild)}"
        )

    logging.info(
        "===================================="
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
