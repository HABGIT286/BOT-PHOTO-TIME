# =========================================================
# Price Guess Pro
# Part 1
# Core / Config / Database / Models
# Miswag API Integration
# discord.py 2.x
# =========================================================

import discord
from discord.ext import commands
from discord import app_commands

import os
import json
import sqlite3
import asyncio
import random
import logging

from datetime import datetime
from pathlib import Path

import httpx


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).parent

CONFIG_FILE = BASE_DIR / "config.json"
SERVERS_FILE = BASE_DIR / "servers.json"

DATABASE_FILE = BASE_DIR / "price_guess.db"

LOGS_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"

LOGS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)


# =========================================================
# CONFIG LOADER
# =========================================================

def load_json(file_path, default=None):

    try:

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:

        return default if default is not None else {}


CONFIG = load_json(
    CONFIG_FILE,
    {}
)

SERVERS = load_json(
    SERVERS_FILE,
    {}
)


# =========================================================
# ENVIRONMENT
# =========================================================

DISCORD_TOKEN = os.getenv(
    "DISCORD_TOKEN"
)

OWNER_USER_ID = int(
    os.getenv(
        "OWNER_USER_ID",
        "0"
    )
)


# =========================================================
# MISWAG API
# =========================================================

MISWAG_API_URL = (
    "https://miswag.com/api/v1/search"
)

MISWAG_TOKEN = os.getenv(
    "MISWAG_TOKEN"
)

MISWAG_HEADERS = {

    "authority": "miswag.com",

    "accept": "application/json",

    "accept-language": "ar",

    "content-type": "application/json",

    "origin": "https://miswag.com",

    "referer": (
        "https://miswag.com/search"
        "?q=%D8%A7%D9%84%D8%AC%D9%85%D8%A7%D9%84"
        "%20%D9%88%D8%A7%D9%84%D8%B9%D9%86%D8%A7%D9%8A%D8%A9"
    ),

    "user-agent": (
        "Mozilla/5.0 "
        "(X11; Linux x86_64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/139.0.0.0 "
        "Safari/537.36"
    )
}

if MISWAG_TOKEN:

    MISWAG_HEADERS[
        "authorization"
    ] = f"Bearer {MISWAG_TOKEN}"


MISWAG_PAYLOAD = {

    "query": "الجمال والعناية",

    "activeFilters": {},

    "page": 1,

    "perPage": 24
}


# =========================================================
# LOGGER
# =========================================================

log_file = (
    LOGS_DIR /
    f"{datetime.utcnow().date()}.log"
)

logging.basicConfig(

    level=logging.INFO,

    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(message)s"
    ),

    handlers=[

        logging.FileHandler(
            log_file,
            encoding="utf-8"
        ),

        logging.StreamHandler()
    ]
)

logger = logging.getLogger(
    "PriceGuessBot"
)


# =========================================================
# DISCORD BOT
# =========================================================

intents = discord.Intents.default()

intents.message_content = True
intents.members = True
intents.guilds = True


bot = commands.Bot(

    command_prefix="!",

    intents=intents,

    help_command=None
)


# =========================================================
# SQLITE
# =========================================================

class Database:

    def __init__(self):

        self.db = sqlite3.connect(

            DATABASE_FILE,

            check_same_thread=False
        )

        self.db.row_factory = (
            sqlite3.Row
        )

        self.cursor = (
            self.db.cursor()
        )


    def execute(
        self,
        query,
        values=()
    ):

        self.cursor.execute(
            query,
            values
        )

        self.db.commit()


    def fetchone(
        self,
        query,
        values=()
    ):

        self.cursor.execute(
            query,
            values
        )

        return self.cursor.fetchone()


    def fetchall(
        self,
        query,
        values=()
    ):

        self.cursor.execute(
            query,
            values
        )

        return self.cursor.fetchall()


db = Database()


# =========================================================
# TABLES
# =========================================================

def create_tables():

    db.execute("""
    CREATE TABLE IF NOT EXISTS players(

        user_id INTEGER PRIMARY KEY,

        username TEXT,

        games_played INTEGER DEFAULT 0,

        wins INTEGER DEFAULT 0,

        second_places INTEGER DEFAULT 0,

        third_places INTEGER DEFAULT 0,

        total_points INTEGER DEFAULT 0,

        best_score INTEGER DEFAULT 0,

        correct_answers INTEGER DEFAULT 0,

        wrong_answers INTEGER DEFAULT 0,

        created_at TEXT
    )
    """)


    db.execute("""
    CREATE TABLE IF NOT EXISTS games(

        game_id INTEGER PRIMARY KEY AUTOINCREMENT,

        guild_id INTEGER,

        channel_id INTEGER,

        difficulty TEXT,

        total_players INTEGER,

        winner_id INTEGER,

        started_at TEXT,

        ended_at TEXT
    )
    """)


    db.execute("""
    CREATE TABLE IF NOT EXISTS rounds(

        round_id INTEGER PRIMARY KEY AUTOINCREMENT,

        game_id INTEGER,

        image_url TEXT,

        real_price REAL,

        round_number INTEGER,

        created_at TEXT
    )
    """)


    db.execute("""
    CREATE TABLE IF NOT EXISTS answers(

        answer_id INTEGER PRIMARY KEY AUTOINCREMENT,

        game_id INTEGER,

        round_id INTEGER,

        user_id INTEGER,

        answer REAL,

        difference REAL,

        points INTEGER,

        created_at TEXT
    )
    """)


    db.execute("""
    CREATE TABLE IF NOT EXISTS servers(

        guild_id INTEGER PRIMARY KEY,

        games_count INTEGER DEFAULT 0,

        last_game TEXT
    )
    """)


create_tables()


# =========================================================
# PLAYER MODEL
# =========================================================

class PlayerData:

    @staticmethod
    def ensure(
        user: discord.User
    ):

        exists = db.fetchone(

            "SELECT * FROM players "
            "WHERE user_id=?",

            (user.id,)
        )

        if exists:

            return


        db.execute(

            """
            INSERT INTO players(
                user_id,
                username,
                created_at
            )
            VALUES(?,?,?)
            """,

            (
                user.id,
                str(user),
                datetime.utcnow().isoformat()
            )
        )


    @staticmethod
    def get(
        user_id: int
    ):

        return db.fetchone(

            "SELECT * FROM players "
            "WHERE user_id=?",

            (user_id,)
        )


# =========================================================
# PRODUCT MODEL
# =========================================================

class Product:

    def __init__(

        self,

        title,

        image_url,

        real_price,

        category,

        brand=None,

        product_url=None,

        product_id=None
    ):

        self.title = title

        self.image_url = image_url

        self.real_price = real_price

        self.category = category

        self.brand = brand or "عام"

        self.product_url = product_url

        self.product_id = product_id


# =========================================================
# GAME MODEL
# =========================================================

class GameSession:

    def __init__(

        self,

        guild_id,

        channel_id,

        owner_id
    ):

        self.guild_id = guild_id

        self.channel_id = channel_id

        self.owner_id = owner_id

        self.players = {}

        self.difficulty = None

        self.started = False

        self.registration_open = False

        self.current_round = 0

        self.current_image = 0

        self.total_rounds = 3

        self.images_per_round = 5

        self.total_images = 15

        self.answers = {}

        self.scores = {}

        self.products = []

        self.used_product_ids = set()

        self.game_id = None

        self.created_at = datetime.utcnow()


# =========================================================
# ACTIVE GAMES
# =========================================================

ACTIVE_GAMES = {}


# =========================================================
# CURRENT QUESTIONS
# =========================================================

CURRENT_QUESTION = {}


# =========================================================
# SETTINGS
# =========================================================

DIFFICULTIES = {

    "easy": {

        "name": "Easy",

        "min": 0,

        "max": 100
    },

    "normal": {

        "name": "Normal",

        "min": 0,

        "max": 300
    },

    "hard": {

        "name": "Hard",

        "min": 0,

        "max": 500
    }
}


MIN_PLAYERS = 2

REGISTRATION_TIME = 20

ANSWER_TIME = 20


POINTS_TABLE = [

    10,

    7,

    5,

    3
]


# =========================================================
# HELPERS
# =========================================================

def now():

    return datetime.utcnow().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def log_event(
    message: str
):

    logger.info(message)


def guild_has_game(
    guild_id: int
):

    return guild_id in ACTIVE_GAMES


# =========================================================
# MISWAG HELPERS
# =========================================================

def extract_price(
    product
):

    price = product.get(
        "price"
    )

    if isinstance(
        price,
        dict
    ):

        value = price.get(
            "value"
        )

    else:

        value = price


    try:

        return float(value)

    except Exception:

        return None


def extract_title(
    product
):

    title = product.get(
        "title"
    )

    if isinstance(
        title,
        dict
    ):

        return (
            title.get("AR")
            or title.get("ar")
            or title.get("EN")
            or title.get("en")
            or "منتج بدون اسم"
        )

    if title:

        return str(title)

    return "منتج بدون اسم"


def extract_product_id(
    product
):

    for key in (
        "id",
        "_id",
        "productId",
        "product_id"
    ):

        value = product.get(key)

        if value is not None:

            return str(value)

    url = product.get(
        "url"
    )

    if url:

        return str(url)

    return None


def product_from_api(
    item
):

    price = extract_price(
        item
    )

    if price is None:

        return None


    title = extract_title(
        item
    )


    image = (
        item.get("image")
        or item.get("imageUrl")
        or item.get("image_url")
    )


    if not image:

        return None


    brand = (
        item.get("brand")
        or "عام"
    )


    product_url = item.get(
        "url"
    )


    product_id = (
        extract_product_id(
            item
        )
    )


    category = (
        item.get("category")
        or "الجمال والعناية"
    )


    return Product(

        title=title,

        image_url=image,

        real_price=price,

        category=category,

        brand=brand,

        product_url=product_url,

        product_id=product_id
    )


# =========================================================
# READY
# =========================================================

log_event(
    "Core Loaded"
)

log_event(
    "Database Loaded"
)

log_event(
    "Miswag API Configured"
)

log_event(
    "Part 1 Ready"
)
# =========================================================
# Price Guess Pro
# Part 2
# Lobby System
# Registration System
# Buttons
# Difficulty Selection
# Miswag Product Game
# =========================================================


# =========================================================
# LOBBY VIEW
# =========================================================

class LobbyView(discord.ui.View):

    def __init__(self, session: GameSession):

        super().__init__(
            timeout=None
        )

        self.session = session

    # =====================================================
    # UPDATE LOBBY
    # =====================================================

    async def update_message(
        self,
        interaction: discord.Interaction
    ):

        difficulty_text = (
            self.session.difficulty
            or "Not Selected"
        )

        if self.session.players:

            players_text = "\n".join(
                f"• <@{pid}>"
                for pid in self.session.players
            )

        else:

            players_text = "No Players"

        embed = discord.Embed(
            title="🎮 Price Guess Pro",
            description=(
                "خمن سعر المنتجات الحقيقية "
                "من Miswag 🛍️"
            ),
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="📊 Difficulty",
            value=difficulty_text,
            inline=False
        )

        embed.add_field(
            name="👥 Players",
            value=str(
                len(self.session.players)
            ),
            inline=False
        )

        embed.add_field(
            name="👤 Participants",
            value=players_text,
            inline=False
        )

        embed.add_field(
            name="⏳ Registration",
            value=f"{REGISTRATION_TIME} seconds",
            inline=False
        )

        await interaction.message.edit(
            embed=embed,
            view=self
        )

    # =====================================================
    # EASY
    # =====================================================

    @discord.ui.button(
        label="Easy",
        emoji="🟢",
        style=discord.ButtonStyle.success,
        row=0
    )
    async def easy_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.user.id != self.session.owner_id:

            return await interaction.response.send_message(
                "❌ فقط منشئ اللعبة يستطيع اختيار مستوى الصعوبة.",
                ephemeral=True
            )

        self.session.difficulty = "easy"

        await interaction.response.defer()

        await self.update_message(
            interaction
        )

    # =====================================================
    # NORMAL
    # =====================================================

    @discord.ui.button(
        label="Normal",
        emoji="🟡",
        style=discord.ButtonStyle.primary,
        row=0
    )
    async def normal_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.user.id != self.session.owner_id:

            return await interaction.response.send_message(
                "❌ فقط منشئ اللعبة يستطيع اختيار مستوى الصعوبة.",
                ephemeral=True
            )

        self.session.difficulty = "normal"

        await interaction.response.defer()

        await self.update_message(
            interaction
        )

    # =====================================================
    # HARD
    # =====================================================

    @discord.ui.button(
        label="Hard",
        emoji="🔴",
        style=discord.ButtonStyle.danger,
        row=0
    )
    async def hard_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.user.id != self.session.owner_id:

            return await interaction.response.send_message(
                "❌ فقط منشئ اللعبة يستطيع اختيار مستوى الصعوبة.",
                ephemeral=True
            )

        self.session.difficulty = "hard"

        await interaction.response.defer()

        await self.update_message(
            interaction
        )

    # =====================================================
    # JOIN
    # =====================================================

    @discord.ui.button(
        label="Join",
        emoji="✅",
        style=discord.ButtonStyle.success,
        row=1
    )
    async def join_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        uid = interaction.user.id

        if not self.session.registration_open:

            return await interaction.response.send_message(
                "❌ انتهى وقت التسجيل.",
                ephemeral=True
            )

        if uid in self.session.players:

            return await interaction.response.send_message(
                "ℹ️ أنت منضم للعبة بالفعل.",
                ephemeral=True
            )

        self.session.players[uid] = {
            "user": interaction.user,
            "points": 0,
            "correct": 0,
            "wrong": 0
        }

        PlayerData.ensure(
            interaction.user
        )

        await interaction.response.send_message(
            "✅ تم انضمامك إلى اللعبة.",
            ephemeral=True
        )

        await self.update_message(
            interaction
        )

    # =====================================================
    # LEAVE
    # =====================================================

    @discord.ui.button(
        label="Leave",
        emoji="❌",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def leave_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        uid = interaction.user.id

        if not self.session.registration_open:

            return await interaction.response.send_message(
                "❌ لا يمكنك الخروج الآن.",
                ephemeral=True
            )

        if uid == self.session.owner_id:

            return await interaction.response.send_message(
                "❌ منشئ اللعبة لا يمكنه الخروج من اللعبة.\n"
                "استخدم Cancel لإلغاء اللعبة.",
                ephemeral=True
            )

        if uid not in self.session.players:

            return await interaction.response.send_message(
                "ℹ️ أنت غير منضم للعبة.",
                ephemeral=True
            )

        del self.session.players[uid]

        await interaction.response.send_message(
            "🚪 تم خروجك من اللعبة.",
            ephemeral=True
        )

        await self.update_message(
            interaction
        )

    # =====================================================
    # CANCEL
    # =====================================================

    @discord.ui.button(
        label="Cancel",
        emoji="🛑",
        style=discord.ButtonStyle.danger,
        row=1
    )
    async def cancel_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.user.id != self.session.owner_id:

            return await interaction.response.send_message(
                "❌ فقط منشئ اللعبة يستطيع إلغاء اللعبة.",
                ephemeral=True
            )

        ACTIVE_GAMES.pop(
            self.session.guild_id,
            None
        )

        embed = discord.Embed(
            title="🛑 Game Cancelled",
            description="تم إلغاء اللعبة بنجاح.",
            color=discord.Color.red()
        )

        await interaction.response.edit_message(
            embed=embed,
            view=None
        )

        log_event(
            f"Game Cancelled | "
            f"Guild: {self.session.guild_id}"
        )


# =========================================================
# REGISTRATION EMBED
# =========================================================

def build_lobby_embed(
    session: GameSession,
    remaining=None
):

    difficulty = (
        session.difficulty
        or "Not Selected"
    )

    if session.players:

        players_text = "\n".join(
            f"• <@{uid}>"
            for uid in session.players
        )

    else:

        players_text = "No Players"

    embed = discord.Embed(
        title="🎮 Price Guess Pro",
        description=(
            "🛍️ لعبة تخمين أسعار المنتجات "
            "الحقيقية من Miswag\n\n"
            "اختر مستوى الصعوبة ثم اضغط "
            "Join للانضمام."
        ),
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="📊 Difficulty",
        value=difficulty,
        inline=True
    )

    embed.add_field(
        name="👥 Players",
        value=str(
            len(session.players)
        ),
        inline=True
    )

    if remaining is not None:

        embed.add_field(
            name="⏳ Time",
            value=f"{remaining}s",
            inline=True
        )

    embed.add_field(
        name="👤 Participants",
        value=players_text,
        inline=False
    )

    embed.set_footer(
        text=(
            f"Minimum players: "
            f"{MIN_PLAYERS}"
        )
    )

    return embed


# =========================================================
# REGISTRATION TIMER
# =========================================================

async def registration_countdown(
    message,
    session: GameSession
):

    session.registration_open = True

    try:

        for remaining in range(
            REGISTRATION_TIME,
            0,
            -1
        ):

            if session.guild_id not in ACTIVE_GAMES:

                return

            embed = build_lobby_embed(
                session,
                remaining
            )

            try:

                await message.edit(
                    embed=embed,
                    view=LobbyView(session)
                )

            except discord.NotFound:

                return

            except discord.HTTPException:

                pass

            await asyncio.sleep(1)

        session.registration_open = False

        # =================================================
        # CHECK MINIMUM PLAYERS
        # =================================================

        if len(session.players) < MIN_PLAYERS:

            embed = discord.Embed(
                title="❌ Game Cancelled",
                description=(
                    "لم يبدأ اللعب لأن عدد "
                    "اللاعبين غير كافٍ.\n\n"
                    f"👥 المطلوب: {MIN_PLAYERS}\n"
                    f"👥 الموجود: "
                    f"{len(session.players)}"
                ),
                color=discord.Color.red()
            )

            ACTIVE_GAMES.pop(
                session.guild_id,
                None
            )

            return await message.edit(
                embed=embed,
                view=None
            )

        # =================================================
        # CHECK DIFFICULTY
        # =================================================

        if not session.difficulty:

            embed = discord.Embed(
                title="❌ Game Cancelled",
                description=(
                    "لم يتم اختيار مستوى "
                    "الصعوبة."
                ),
                color=discord.Color.red()
            )

            ACTIVE_GAMES.pop(
                session.guild_id,
                None
            )

            return await message.edit(
                embed=embed,
                view=None
            )

        # =================================================
        # STARTING
        # =================================================

        start_embed = discord.Embed(
            title="🚀 Starting Game",
            description=(
                f"👥 Players: "
                f"{len(session.players)}\n"
                f"📊 Difficulty: "
                f"{session.difficulty}\n\n"
                "🛍️ جاري تحميل المنتجات "
                "من Miswag..."
            ),
            color=discord.Color.gold()
        )

        await message.edit(
            embed=start_embed,
            view=None
        )

        await asyncio.sleep(2)

        await start_game(
            session,
            message.channel
        )

    except asyncio.CancelledError:

        return

    except Exception as e:

        logger.exception(
            "Registration error: %s",
            e
        )

        ACTIVE_GAMES.pop(
            session.guild_id,
            None
        )


# =========================================================
# CREATE GAME
# =========================================================

async def create_game(
    ctx,
    slash=False
):

    # =====================================================
    # CHECK GUILD
    # =====================================================

    guild = ctx.guild

    if guild is None:

        text = (
            "❌ اللعبة تعمل داخل السيرفرات فقط."
        )

        if slash:

            return await ctx.response.send_message(
                text,
                ephemeral=True
            )

        return await ctx.send(
            text
        )

    guild_id = guild.id

    # =====================================================
    # CHECK ACTIVE GAME
    # =====================================================

    if guild_has_game(
        guild_id
    ):

        text = (
            "❌ توجد لعبة تعمل بالفعل "
            "في هذا السيرفر."
        )

        if slash:

            return await ctx.response.send_message(
                text,
                ephemeral=True
            )

        return await ctx.send(
            text
        )

    # =====================================================
    # OWNER
    # =====================================================

    if slash:

        owner = ctx.user

    else:

        owner = ctx.author

    # =====================================================
    # CREATE SESSION
    # =====================================================

    session = GameSession(
        guild_id=guild_id,
        channel_id=ctx.channel.id,
        owner_id=owner.id
    )

    ACTIVE_GAMES[
        guild_id
    ] = session

    # =====================================================
    # ADD OWNER
    # =====================================================

    session.players[
        owner.id
    ] = {
        "user": owner,
        "points": 0,
        "correct": 0,
        "wrong": 0
    }

    PlayerData.ensure(
        owner
    )

    # =====================================================
    # LOBBY
    # =====================================================

    view = LobbyView(
        session
    )

    embed = build_lobby_embed(
        session,
        REGISTRATION_TIME
    )

    embed.description = (
        "🛍️ **Price Guess Pro**\n\n"
        "خمن أسعار المنتجات الحقيقية "
        "من Miswag.\n\n"
        "🟢 Easy\n"
        "🟡 Normal\n"
        "🔴 Hard\n\n"
        f"⏳ التسجيل: "
        f"{REGISTRATION_TIME} ثانية\n"
        f"👥 الحد الأدنى: "
        f"{MIN_PLAYERS} لاعبين"
    )

    if slash:

        await ctx.response.send_message(
            embed=embed,
            view=view
        )

        message = (
            await ctx.original_response()
        )

    else:

        message = await ctx.send(
            embed=embed,
            view=view
        )

    # =====================================================
    # START TIMER
    # =====================================================

    asyncio.create_task(
        registration_countdown(
            message,
            session
        )
    )

    log_event(
        f"Lobby Created | "
        f"Guild: {guild_id} | "
        f"Owner: {owner.id}"
    )


# =========================================================
# PART 2 END
# =========================================================
# =========================================================
# Price Guess Pro
# Part 3
# GAME ENGINE
# Miswag API Products
# 20 Second Answer Timer
# Scoring / Rounds / Final Results
# =========================================================

CURRENT_QUESTION = {}

# =========================================================
# MISWAG PRODUCT FETCHER
# =========================================================

async def get_random_product():
    """
    جلب المنتجات مباشرة من Miswag API.
    كل مرة يتم جلب مجموعة منتجات حقيقية،
    ثم يتم اختيار منتج عشوائي منها.
    """

    try:

        import httpx

        payload = {
            "query": "الجمال والعناية",
            "activeFilters": {},
            "page": random.randint(1, 5),
            "perPage": 24
        }

        headers = {
            "accept": "application/json",
            "accept-language": "ar",
            "authorization": (
                "Bearer "
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
                "eyJpYXQiOjE3ODY4NzkyMTYsInVpZCI6"
                "Im0tMTUyMzY2ODU4IiwidG9rIjoiZTc4NGNi"
                "NDktZjE1Ny00NzI1LThmZjUtYmU1Njg5M2Qy"
                "NjIyIiwiaGlkIjoiTlh3NU16UXpOamMwTm"
                "kwNFltRmtMVFF4WlRZdE9EUTRPUzFsTkRZNU"
                "5HRTJabUU1WXpSOGNISnZaQT09IiwiaXNzIj"
                "oibWlzd2FnLmFwaSIsInNjIjoiMCJ9."
                "NxOb_Efg1G_EDXuwICBUnV1UNE-5MhOLuS2wQMo0FiE"
            ),
            "content-type": "application/json",
            "origin": "https://miswag.com",
            "referer": "https://miswag.com/",
            "user-agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/139.0.0.0 Safari/537.36"
            )
        }

        async with httpx.AsyncClient(
            timeout=30.0
        ) as client:

            response = await client.post(
                "https://miswag.com/api/v1/search",
                json=payload,
                headers=headers
            )

            response.raise_for_status()

            data = response.json()

        if not data.get("success"):
            log_event("Miswag API returned unsuccessful response")
            return None

        hits = (
            data
            .get("data", {})
            .get("hits", [])
        )

        if not hits:
            log_event("Miswag API returned no products")
            return None

        # اختيار منتج عشوائي من المنتجات الحقيقية
        product_data = random.choice(hits)

        # -------------------------------------------------
        # TITLE
        # -------------------------------------------------

        title_data = product_data.get(
            "title",
            {}
        )

        if isinstance(title_data, dict):

            title = (
                title_data.get("AR")
                or title_data.get("ar")
                or title_data.get("EN")
                or title_data.get("en")
                or "منتج بدون اسم"
            )

        else:

            title = str(
                title_data
                or "منتج بدون اسم"
            )

        # -------------------------------------------------
        # PRICE
        # -------------------------------------------------

        price_data = product_data.get(
            "price",
            {}
        )

        if isinstance(price_data, dict):

            price_value = price_data.get(
                "value",
                0
            )

            currency = price_data.get(
                "currency",
                "IQD"
            )

        else:

            price_value = price_data or 0
            currency = "IQD"

        try:

            real_price = float(
                price_value
            )

        except Exception:

            real_price = 0.0

        # -------------------------------------------------
        # BRAND
        # -------------------------------------------------

        brand = (
            product_data.get("brand")
            or "عام"
        )

        # -------------------------------------------------
        # IMAGE
        # -------------------------------------------------

        image_url = (
            product_data.get("image")
            or product_data.get("imageUrl")
            or product_data.get("image_url")
        )

        # -------------------------------------------------
        # PRODUCT URL
        # -------------------------------------------------

        product_url = (
            product_data.get("url")
            or "https://miswag.com"
        )

        # -------------------------------------------------
        # CATEGORY
        # -------------------------------------------------

        category = (
            product_data.get("category")
            or "الجمال والعناية"
        )

        if isinstance(category, dict):

            category = (
                category.get("name")
                or category.get("title")
                or "الجمال والعناية"
            )

        # -------------------------------------------------
        # VALIDATE PRICE
        # -------------------------------------------------

        if real_price <= 0:

            log_event(
                f"Invalid product price: {title}"
            )

            return None

        return Product(
            title=title,
            image_url=image_url,
            real_price=real_price,
            category=str(category)
        )

    except Exception as e:

        logger.exception(
            f"Miswag product fetch error: {e}"
        )

        return None


# =========================================================
# PRODUCT RETRY
# =========================================================

async def get_valid_product():

    for attempt in range(5):

        product = await get_random_product()

        if product is not None:

            return product

        await asyncio.sleep(1)

    return None


# =========================================================
# SCORE CALCULATOR
# =========================================================

def calculate_points(results):

    scores = {}

    for index, row in enumerate(results):

        uid = row["user_id"]

        if index == 0:

            scores[uid] = 10

        elif index == 1:

            scores[uid] = 7

        elif index == 2:

            scores[uid] = 5

        elif index == 3:

            scores[uid] = 3

        else:

            scores[uid] = 1

    return scores


# =========================================================
# QUESTION TIMER
# =========================================================

async def question_timer(
    session,
    channel,
    product,
    image_number
):

    # تصفير إجابات الجولة الحالية
    session.answers = {}

    embed = discord.Embed(
        title=f"🛒 المنتج رقم {image_number}",
        description=(
            "💰 خمن سعر المنتج الحقيقي\n\n"
            "✍️ أرسل السعر كرقم في الشات\n"
            f"⏳ لديك {ANSWER_TIME} ثانية للإجابة"
        ),
        color=discord.Color.orange()
    )

    embed.add_field(
        name="🏷️ المنتج",
        value=product.title[:1024],
        inline=False
    )

    embed.add_field(
        name="🏢 الفئة",
        value=product.category,
        inline=False
    )

    if product.image_url:

        embed.set_image(
            url=product.image_url
        )

    message = await channel.send(
        embed=embed
    )

    CURRENT_QUESTION[
        session.guild_id
    ] = {
        "product": product,
        "message": message,
        "image_number": image_number
    }

    # -----------------------------------------------------
    # الانتظار
    # -----------------------------------------------------

    for remaining in range(
        ANSWER_TIME,
        0,
        -1
    ):

        # إذا توقفت اللعبة
        if session.guild_id not in ACTIVE_GAMES:

            return

        players_count = len(
            session.players
        )

        answers_count = len(
            session.answers
        )

        # إذا كل اللاعبين أجابوا
        if (
            players_count > 0
            and answers_count >= players_count
        ):

            break

        # تحديث الوقت كل ثانية
        try:

            timer_embed = discord.Embed(
                title=f"🛒 المنتج رقم {image_number}",
                description=(
                    "💰 خمن سعر المنتج الحقيقي\n\n"
                    f"⏳ الوقت المتبقي: **{remaining} ثانية**"
                ),
                color=discord.Color.orange()
            )

            timer_embed.add_field(
                name="🏷️ المنتج",
                value=product.title[:1024],
                inline=False
            )

            timer_embed.add_field(
                name="🏢 الفئة",
                value=product.category,
                inline=False
            )

            timer_embed.add_field(
                name="👥 الإجابات",
                value=(
                    f"{answers_count}/"
                    f"{players_count}"
                ),
                inline=False
            )

            if product.image_url:

                timer_embed.set_image(
                    url=product.image_url
                )

            await message.edit(
                embed=timer_embed
            )

        except Exception as e:

            logger.warning(
                f"Timer message update failed: {e}"
            )

        await asyncio.sleep(1)

    # -----------------------------------------------------
    # نهاية السؤال
    # -----------------------------------------------------

    if session.guild_id not in ACTIVE_GAMES:

        return

    await finish_question(
        session,
        channel,
        product
    )


# =========================================================
# FINISH QUESTION
# =========================================================

async def finish_question(
    session,
    channel,
    product
):

    real_price = product.real_price

    results = []

    # -----------------------------------------------------
    # حساب الفروقات
    # -----------------------------------------------------

    for uid, answer in session.answers.items():

        difference = abs(
            float(answer) - real_price
        )

        results.append({
            "user_id": uid,
            "answer": answer,
            "difference": difference
        })

    # الأقرب للسعر أولاً
    results.sort(
        key=lambda x: x["difference"]
    )

    gained = calculate_points(
        results
    )

    result_text = ""

    medals = [
        "🥇",
        "🥈",
        "🥉",
        "🏅"
    ]

    # -----------------------------------------------------
    # اللاعبين الذين أجابوا
    # -----------------------------------------------------

    for index, row in enumerate(results):

        uid = row["user_id"]

        pts = gained.get(
            uid,
            1
        )

        # إضافة النقاط
        if uid in session.players:

            session.players[uid][
                "points"
            ] += pts

            session.players[uid][
                "correct"
            ] += 1

        if index < len(medals):

            medal = medals[index]

        else:

            medal = "🎖️"

        answer_value = row["answer"]

        if float(answer_value).is_integer():

            answer_display = str(
                int(answer_value)
            )

        else:

            answer_display = f"{answer_value:.2f}"

        difference = row["difference"]

        if float(difference).is_integer():

            difference_display = str(
                int(difference)
            )

        else:

            difference_display = f"{difference:.2f}"

        result_text += (
            f"{medal} <@{uid}>\n"
            f"💰 إجابته: **{answer_display} IQD**\n"
            f"📏 الفرق: **{difference_display} IQD**\n"
            f"⭐ النقاط: **+{pts}**\n\n"
        )

    # -----------------------------------------------------
    # اللاعبين الذين لم يجيبوا
    # -----------------------------------------------------

    for uid in session.players:

        if uid not in session.answers:

            session.players[uid][
                "wrong"
            ] += 1

            result_text += (
                f"❌ <@{uid}>\n"
                f"لم يرسل إجابة\n"
                f"⭐ النقاط: **+0**\n\n"
            )

    # -----------------------------------------------------
    # عرض السعر الحقيقي
    # -----------------------------------------------------

    if float(real_price).is_integer():

        real_price_display = str(
            int(real_price)
        )

    else:

        real_price_display = f"{real_price:.2f}"

    embed = discord.Embed(
        title="📊 نتائج الجولة",
        color=discord.Color.green()
    )

    embed.add_field(
        name="🛍️ المنتج",
        value=product.title[:1024],
        inline=False
    )

    embed.add_field(
        name="💰 السعر الحقيقي",
        value=(
            f"**{real_price_display} IQD**"
        ),
        inline=False
    )

    if result_text:

        embed.add_field(
            name="🏆 الترتيب",
            value=result_text[:1024],
            inline=False
        )

    else:

        embed.add_field(
            name="🏆 الترتيب",
            value="لم يرسل أي لاعب إجابة.",
            inline=False
        )

    if product.image_url:

        embed.set_thumbnail(
            url=product.image_url
        )

    await channel.send(
        embed=embed
    )

    # -----------------------------------------------------
    # تحديث قاعدة البيانات
    # -----------------------------------------------------

    for uid, player in session.players.items():

        PlayerData.ensure(
            player["user"]
        )

        data = PlayerData.get(uid)

        if data:

            new_points = (
                data["total_points"]
                + player["points"]
            )

            best_score = max(
                data["best_score"],
                player["points"]
            )

            db.execute(
                """
                UPDATE players
                SET total_points=?,
                    best_score=?,
                    correct_answers=correct_answers+?,
                    wrong_answers=wrong_answers+?
                WHERE user_id=?
                """,
                (
                    new_points,
                    best_score,
                    player["correct"],
                    player["wrong"],
                    uid
                )
            )

    await asyncio.sleep(3)

    CURRENT_QUESTION.pop(
        session.guild_id,
        None
    )


# =========================================================
# PLAY ALL PRODUCTS
# =========================================================

async def start_game(
    session,
    channel
):

    session.started = True

    log_event(
        f"Game Started | Guild={session.guild_id}"
    )

    # -----------------------------------------------------
    # إنشاء اللعبة في DB
    # -----------------------------------------------------

    db.execute(
        """
        INSERT INTO games(
            guild_id,
            channel_id,
            difficulty,
            total_players,
            started_at
        )
        VALUES(?,?,?,?,?)
        """,
        (
            session.guild_id,
            session.channel_id,
            session.difficulty,
            len(session.players),
            now()
        )
    )

    row = db.fetchone(
        "SELECT last_insert_rowid() AS id"
    )

    if row:

        session.game_id = row["id"]

    # -----------------------------------------------------
    # 3 جولات × 5 منتجات = 15 منتج
    # -----------------------------------------------------

    total_rounds = 3

    images_per_round = 5

    total_images = (
        total_rounds
        * images_per_round
    )

    session.total_rounds = total_rounds

    session.images_per_round = (
        images_per_round
    )

    session.total_images = total_images

    current_image = 1

    # -----------------------------------------------------
    # الجولات
    # -----------------------------------------------------

    for round_number in range(
        1,
        total_rounds + 1
    ):

        if session.guild_id not in ACTIVE_GAMES:

            return

        session.current_round = (
            round_number
        )

        # -------------------------------------------------
        # إعلان الجولة
        # -------------------------------------------------

        round_embed = discord.Embed(
            title=(
                f"🎯 الجولة {round_number}"
            ),
            description=(
                f"الصور: "
                f"{images_per_round}\n"
                f"الوقت لكل تخمين: "
                f"{ANSWER_TIME} ثانية"
            ),
            color=discord.Color.blurple()
        )

        await channel.send(
            embed=round_embed
        )

        await asyncio.sleep(2)

        # -------------------------------------------------
        # منتجات الجولة
        # -------------------------------------------------

        for image_index in range(
            1,
            images_per_round + 1
        ):

            if (
                session.guild_id
                not in ACTIVE_GAMES
            ):

                return

            product = await get_valid_product()

            if product is None:

                await channel.send(
                    "⚠️ تعذر جلب المنتج من Miswag، "
                    "سيتم تجاوز هذا السؤال."
                )

                continue

            session.products.append(
                product
            )

            session.current_image = (
                current_image
            )

            # -------------------------------------------------
            # حفظ الجولة
            # -------------------------------------------------

            db.execute(
                """
                INSERT INTO rounds(
                    game_id,
                    image_url,
                    real_price,
                    round_number,
                    created_at
                )
                VALUES(?,?,?,?,?)
                """,
                (
                    session.game_id,
                    product.image_url,
                    product.real_price,
                    current_image,
                    now()
                )
            )

            await question_timer(
                session,
                channel,
                product,
                current_image
            )

            current_image += 1

            await asyncio.sleep(1)

    # -----------------------------------------------------
    # نهاية اللعبة
    # -----------------------------------------------------

    if session.guild_id in ACTIVE_GAMES:

        await finish_game(
            session,
            channel
        )


# =========================================================
# GAME END
# =========================================================

async def finish_game(
    session,
    channel
):

    ranking = sorted(
        session.players.items(),
        key=lambda x: x[1]["points"],
        reverse=True
    )

    if not ranking:

        ACTIVE_GAMES.pop(
            session.guild_id,
            None
        )

        return

    text = ""

    medals = [
        "🏆",
        "🥈",
        "🥉"
    ]

    # -----------------------------------------------------
    # النتائج النهائية
    # -----------------------------------------------------

    for index, data in enumerate(
        ranking
    ):

        uid = data[0]

        points = data[1]["points"]

        if index < len(medals):

            medal = medals[index]

        else:

            medal = "🎖️"

        text += (
            f"{medal} <@{uid}> "
            f"— **{points} نقطة**\n"
        )

    winner_id = ranking[0][0]

    # -----------------------------------------------------
    # تحديث إحصائيات اللاعبين
    # -----------------------------------------------------

    for index, data in enumerate(
        ranking
    ):

        uid = data[0]

        player = data[1]

        PlayerData.ensure(
            player["user"]
        )

        row = PlayerData.get(uid)

        if not row:
            continue

        games_played = (
            row["games_played"] + 1
        )

        wins = row["wins"]

        second_places = (
            row["second_places"]
        )

        third_places = (
            row["third_places"]
        )

        if index == 0:

            wins += 1

        elif index == 1:

            second_places += 1

        elif index == 2:

            third_places += 1

        db.execute(
            """
            UPDATE players
            SET games_played=?,
                wins=?,
                second_places=?,
                third_places=?
            WHERE user_id=?
            """,
            (
                games_played,
                wins,
                second_places,
                third_places,
                uid
            )
        )

    # -----------------------------------------------------
    # تحديث اللعبة
    # -----------------------------------------------------

    if session.game_id:

        db.execute(
            """
            UPDATE games
            SET winner_id=?,
                ended_at=?
            WHERE game_id=?
            """,
            (
                winner_id,
                now(),
                session.game_id
            )
        )

    # -----------------------------------------------------
    # تحديث السيرفر
    # -----------------------------------------------------

    server = db.fetchone(
        """
        SELECT *
        FROM servers
        WHERE guild_id=?
        """,
        (
            session.guild_id,
        )
    )

    if server:

        db.execute(
            """
            UPDATE servers
            SET games_count=games_count+1,
                last_game=?
            WHERE guild_id=?
            """,
            (
                now(),
                session.guild_id
            )
        )

    else:

        db.execute(
            """
            INSERT INTO servers(
                guild_id,
                games_count,
                last_game
            )
            VALUES(?,?,?)
            """,
            (
                session.guild_id,
                1,
                now()
            )
        )

    # -----------------------------------------------------
    # Final Embed
    # -----------------------------------------------------

    embed = discord.Embed(
        title="🏁 انتهت اللعبة!",
        description=(
            "🎉 النتائج النهائية\n\n"
            f"{text}"
        ),
        color=discord.Color.gold()
    )

    embed.add_field(
        name="🎯 عدد الجولات",
        value=str(
            session.total_rounds
        ),
        inline=True
    )

    embed.add_field(
        name="🛍️ عدد المنتجات",
        value=str(
            session.total_images
        ),
        inline=True
    )

    embed.add_field(
        name="👥 اللاعبين",
        value=str(
            len(session.players)
        ),
        inline=True
    )

    await channel.send(
        embed=embed
    )

    # -----------------------------------------------------
    # تنظيف اللعبة
    # -----------------------------------------------------

    ACTIVE_GAMES.pop(
        session.guild_id,
        None
    )

    CURRENT_QUESTION.pop(
        session.guild_id,
        None
    )

    log_event(
        f"Game Finished | Guild={session.guild_id}"
    )


# =========================================================
# MESSAGE ANSWERS
# =========================================================

@bot.event
async def on_message(message):

    if message.author.bot:

        return

    guild = message.guild

    if guild:

        if guild.id in ACTIVE_GAMES:

            session = ACTIVE_GAMES[
                guild.id
            ]

            # ---------------------------------------------
            # يجب أن تكون اللعبة بدأت
            # ---------------------------------------------

            if not session.started:

                await bot.process_commands(
                    message
                )

                return

            # ---------------------------------------------
            # يجب أن يكون اللاعب مشاركاً
            # ---------------------------------------------

            if (
                message.author.id
                in session.players
            ):

                # -----------------------------------------
                # يجب أن يكون هناك سؤال فعال
                # -----------------------------------------

                question = CURRENT_QUESTION.get(
                    guild.id
                )

                if question:

                    # -------------------------------------
                    # لا يسمح بإجابة ثانية
                    # -------------------------------------

                    if (
                        message.author.id
                        not in session.answers
                    ):

                        content = (
                            message.content
                            .strip()
                            .replace(",", "")
                            .replace("٬", "")
                        )

                        try:

                            value = float(
                                content
                            )

                            # ---------------------------------
                            # منع الأسعار السالبة
                            # ---------------------------------

                            if value < 0:

                                raise ValueError

                            session.answers[
                                message.author.id
                            ] = value

                            await message.add_reaction(
                                "✅"
                            )

                        except Exception:

                            pass

    await bot.process_commands(
        message
    )


# =========================================================
# PART 3 END
# =========================================================
# =========================================================
# Price Guess Pro
# Part 4
# Commands / Profile / Top / Stats / Help / Ready
# =========================================================

# =========================================================
# PROFILE EMBED
# =========================================================

async def profile_embed(user):

    PlayerData.ensure(user)

    data = PlayerData.get(user.id)

    if not data:

        return discord.Embed(
            title="❌ خطأ",
            description="تعذر تحميل بيانات اللاعب.",
            color=discord.Color.red()
        )

    embed = discord.Embed(
        title=f"👤 ملف اللاعب {user.display_name}",
        color=discord.Color.blurple()
    )

    if user.avatar:

        embed.set_thumbnail(
            url=user.avatar.url
        )

    embed.add_field(
        name="🎮 الألعاب",
        value=str(data["games_played"]),
        inline=True
    )

    embed.add_field(
        name="🏆 الانتصارات",
        value=str(data["wins"]),
        inline=True
    )

    embed.add_field(
        name="🥈 المركز الثاني",
        value=str(data["second_places"]),
        inline=True
    )

    embed.add_field(
        name="🥉 المركز الثالث",
        value=str(data["third_places"]),
        inline=True
    )

    embed.add_field(
        name="⭐ مجموع النقاط",
        value=str(data["total_points"]),
        inline=True
    )

    embed.add_field(
        name="🔥 أفضل نتيجة",
        value=str(data["best_score"]),
        inline=True
    )

    embed.add_field(
        name="✅ الإجابات",
        value=str(data["correct_answers"]),
        inline=True
    )

    embed.add_field(
        name="❌ الأخطاء",
        value=str(data["wrong_answers"]),
        inline=True
    )

    embed.set_footer(
        text="Price Guess Pro"
    )

    return embed


# =========================================================
# /GAME
# =========================================================

@bot.tree.command(
    name="game",
    description="بدء لعبة تخمين أسعار المنتجات"
)
async def slash_game(
    interaction: discord.Interaction
):

    if interaction.guild is None:

        return await interaction.response.send_message(
            "❌ هذا الأمر يعمل داخل السيرفر فقط.",
            ephemeral=True
        )

    await create_game(
        interaction,
        slash=True
    )


# =========================================================
# !GAME
# =========================================================

@bot.command(
    name="game"
)
async def prefix_game(
    ctx
):

    if ctx.guild is None:

        return

    await create_game(
        ctx,
        slash=False
    )


# =========================================================
# /STOP
# =========================================================

@bot.tree.command(
    name="stop",
    description="إيقاف اللعبة الحالية"
)
async def slash_stop(
    interaction: discord.Interaction
):

    if interaction.guild is None:

        return await interaction.response.send_message(
            "❌ هذا الأمر يعمل داخل السيرفر فقط.",
            ephemeral=True
        )

    guild_id = interaction.guild.id

    session = ACTIVE_GAMES.get(
        guild_id
    )

    if session is None:

        return await interaction.response.send_message(
            "❌ لا توجد لعبة تعمل حالياً.",
            ephemeral=True
        )

    # -----------------------------------------------------
    # يسمح لمنشئ اللعبة أو صاحب البوت بإيقافها
    # -----------------------------------------------------

    if (
        interaction.user.id != session.owner_id
        and interaction.user.id != OWNER_USER_ID
    ):

        return await interaction.response.send_message(
            "❌ فقط منشئ اللعبة أو صاحب البوت يستطيع إيقافها.",
            ephemeral=True
        )

    ACTIVE_GAMES.pop(
        guild_id,
        None
    )

    CURRENT_QUESTION.pop(
        guild_id,
        None
    )

    session.started = False
    session.registration_open = False

    log_event(
        f"Game Stopped | Guild={guild_id} | "
        f"User={interaction.user.id}"
    )

    await interaction.response.send_message(
        "🛑 تم إيقاف اللعبة بنجاح."
    )


# =========================================================
# !STOP
# =========================================================

@bot.command(
    name="stop"
)
async def prefix_stop(
    ctx
):

    if ctx.guild is None:

        return

    guild_id = ctx.guild.id

    session = ACTIVE_GAMES.get(
        guild_id
    )

    if session is None:

        return await ctx.send(
            "❌ لا توجد لعبة تعمل حالياً."
        )

    if (
        ctx.author.id != session.owner_id
        and ctx.author.id != OWNER_USER_ID
    ):

        return await ctx.send(
            "❌ فقط منشئ اللعبة أو صاحب البوت يستطيع إيقافها."
        )

    ACTIVE_GAMES.pop(
        guild_id,
        None
    )

    CURRENT_QUESTION.pop(
        guild_id,
        None
    )

    session.started = False
    session.registration_open = False

    log_event(
        f"Game Stopped | Guild={guild_id} | "
        f"User={ctx.author.id}"
    )

    await ctx.send(
        "🛑 تم إيقاف اللعبة بنجاح."
    )


# =========================================================
# /PROFILE
# =========================================================

@bot.tree.command(
    name="profile",
    description="عرض ملف اللاعب"
)
async def slash_profile(
    interaction: discord.Interaction
):

    embed = await profile_embed(
        interaction.user
    )

    await interaction.response.send_message(
        embed=embed
    )


# =========================================================
# !PROFILE
# =========================================================

@bot.command(
    name="profile"
)
async def prefix_profile(
    ctx
):

    embed = await profile_embed(
        ctx.author
    )

    await ctx.send(
        embed=embed
    )


# =========================================================
# /TOP
# =========================================================

@bot.tree.command(
    name="top",
    description="عرض أفضل 10 لاعبين"
)
async def slash_top(
    interaction: discord.Interaction
):

    rows = db.fetchall(
        """
        SELECT *
        FROM players
        ORDER BY total_points DESC
        LIMIT 10
        """
    )

    if not rows:

        return await interaction.response.send_message(
            "📊 لا توجد بيانات لاعبين حتى الآن.",
            ephemeral=True
        )

    text = ""

    medals = [
        "🥇",
        "🥈",
        "🥉"
    ]

    for index, row in enumerate(rows):

        if index < 3:

            medal = medals[index]

        else:

            medal = f"**{index + 1}.**"

        username = (
            row["username"]
            or f"User {row['user_id']}"
        )

        text += (
            f"{medal} "
            f"{username} — "
            f"**{row['total_points']} نقطة**\n"
        )

    embed = discord.Embed(
        title="🏆 أفضل 10 لاعبين",
        description=text,
        color=discord.Color.gold()
    )

    embed.set_footer(
        text="Price Guess Pro"
    )

    await interaction.response.send_message(
        embed=embed
    )


# =========================================================
# !TOP
# =========================================================

@bot.command(
    name="top"
)
async def prefix_top(
    ctx
):

    rows = db.fetchall(
        """
        SELECT *
        FROM players
        ORDER BY total_points DESC
        LIMIT 10
        """
    )

    if not rows:

        return await ctx.send(
            "📊 لا توجد بيانات لاعبين حتى الآن."
        )

    text = ""

    medals = [
        "🥇",
        "🥈",
        "🥉"
    ]

    for index, row in enumerate(rows):

        if index < 3:

            medal = medals[index]

        else:

            medal = f"**{index + 1}.**"

        username = (
            row["username"]
            or f"User {row['user_id']}"
        )

        text += (
            f"{medal} "
            f"{username} — "
            f"**{row['total_points']} نقطة**\n"
        )

    embed = discord.Embed(
        title="🏆 أفضل 10 لاعبين",
        description=text,
        color=discord.Color.gold()
    )

    embed.set_footer(
        text="Price Guess Pro"
    )

    await ctx.send(
        embed=embed
    )


# =========================================================
# /STATS
# =========================================================

@bot.tree.command(
    name="stats",
    description="إحصائيات البوت"
)
async def slash_stats(
    interaction: discord.Interaction
):

    players_row = db.fetchone(
        "SELECT COUNT(*) AS c FROM players"
    )

    games_row = db.fetchone(
        "SELECT COUNT(*) AS c FROM games"
    )

    answers_row = db.fetchone(
        "SELECT COUNT(*) AS c FROM answers"
    )

    rounds_row = db.fetchone(
        "SELECT COUNT(*) AS c FROM rounds"
    )

    players_count = (
        players_row["c"]
        if players_row
        else 0
    )

    games_count = (
        games_row["c"]
        if games_row
        else 0
    )

    answers_count = (
        answers_row["c"]
        if answers_row
        else 0
    )

    rounds_count = (
        rounds_row["c"]
        if rounds_row
        else 0
    )

    embed = discord.Embed(
        title="📊 إحصائيات Price Guess Pro",
        color=discord.Color.green()
    )

    embed.add_field(
        name="👥 اللاعبين",
        value=str(players_count),
        inline=True
    )

    embed.add_field(
        name="🎮 الألعاب",
        value=str(games_count),
        inline=True
    )

    embed.add_field(
        name="🎯 الجولات",
        value=str(rounds_count),
        inline=True
    )

    embed.add_field(
        name="💬 الإجابات",
        value=str(answers_count),
        inline=True
    )

    embed.add_field(
        name="🌐 السيرفرات",
        value=str(len(bot.guilds)),
        inline=True
    )

    embed.add_field(
        name="🎮 ألعاب حالية",
        value=str(len(ACTIVE_GAMES)),
        inline=True
    )

    await interaction.response.send_message(
        embed=embed
    )


# =========================================================
# !STATS
# =========================================================

@bot.command(
    name="stats"
)
async def prefix_stats(
    ctx
):

    players_row = db.fetchone(
        "SELECT COUNT(*) AS c FROM players"
    )

    games_row = db.fetchone(
        "SELECT COUNT(*) AS c FROM games"
    )

    answers_row = db.fetchone(
        "SELECT COUNT(*) AS c FROM answers"
    )

    rounds_row = db.fetchone(
        "SELECT COUNT(*) AS c FROM rounds"
    )

    players_count = (
        players_row["c"]
        if players_row
        else 0
    )

    games_count = (
        games_row["c"]
        if games_row
        else 0
    )

    answers_count = (
        answers_row["c"]
        if answers_row
        else 0
    )

    rounds_count = (
        rounds_row["c"]
        if rounds_row
        else 0
    )

    embed = discord.Embed(
        title="📊 إحصائيات Price Guess Pro",
        color=discord.Color.green()
    )

    embed.add_field(
        name="👥 اللاعبين",
        value=str(players_count),
        inline=True
    )

    embed.add_field(
        name="🎮 الألعاب",
        value=str(games_count),
        inline=True
    )

    embed.add_field(
        name="🎯 الجولات",
        value=str(rounds_count),
        inline=True
    )

    embed.add_field(
        name="💬 الإجابات",
        value=str(answers_count),
        inline=True
    )

    embed.add_field(
        name="🌐 السيرفرات",
        value=str(len(bot.guilds)),
        inline=True
    )

    embed.add_field(
        name="🎮 ألعاب حالية",
        value=str(len(ACTIVE_GAMES)),
        inline=True
    )

    await ctx.send(
        embed=embed
    )


# =========================================================
# HELP
# =========================================================

HELP_TEXT = """
🎮 **Price Guess Pro**

━━━━━━━━━━━━━━━━━━━━

🎯 **اللعبة**

`/game`
`!game`

بدء لعبة جديدة لتخمين أسعار المنتجات.

━━━━━━━━━━━━━━━━━━━━

🛑 **إيقاف اللعبة**

`/stop`
`!stop`

إيقاف اللعبة الحالية.

━━━━━━━━━━━━━━━━━━━━

👤 **الملف الشخصي**

`/profile`
`!profile`

عرض إحصائيات اللاعب.

━━━━━━━━━━━━━━━━━━━━

🏆 **أفضل اللاعبين**

`/top`
`!top`

عرض أفضل 10 لاعبين.

━━━━━━━━━━━━━━━━━━━━

📊 **الإحصائيات**

`/stats`
`!stats`

عرض إحصائيات البوت.

━━━━━━━━━━━━━━━━━━━━

📖 **المساعدة**

`/help`
`!help`

عرض قائمة الأوامر.

━━━━━━━━━━━━━━━━━━━━

💡 **طريقة اللعب**

1️⃣ اختر مستوى الصعوبة.

2️⃣ انضم إلى اللعبة.

3️⃣ سيظهر منتج حقيقي من Miswag.

4️⃣ أرسل السعر الذي تتوقعه.

5️⃣ لديك 20 ثانية للإجابة.

6️⃣ الأقرب للسعر يحصل على أعلى نقاط.

7️⃣ اللعبة تحتوي على 3 جولات.

8️⃣ كل جولة تحتوي على 5 منتجات.

🎯 المجموع: **15 منتج**
"""


# =========================================================
# /HELP
# =========================================================

@bot.tree.command(
    name="help",
    description="عرض تعليمات اللعبة"
)
async def slash_help(
    interaction: discord.Interaction
):

    embed = discord.Embed(
        title="📖 Price Guess Pro",
        description=HELP_TEXT,
        color=discord.Color.blurple()
    )

    await interaction.response.send_message(
        embed=embed
    )


# =========================================================
# !HELP
# =========================================================

@bot.command(
    name="help"
)
async def prefix_help(
    ctx
):

    embed = discord.Embed(
        title="📖 Price Guess Pro",
        description=HELP_TEXT,
        color=discord.Color.blurple()
    )

    await ctx.send(
        embed=embed
    )


# =========================================================
# ERROR HANDLER
# =========================================================

@bot.event
async def on_command_error(
    ctx,
    error
):

    if isinstance(
        error,
        commands.CommandNotFound
    ):

        return

    if isinstance(
        error,
        commands.MissingPermissions
    ):

        return await ctx.send(
            "❌ لا تملك الصلاحيات المطلوبة."
        )

    if isinstance(
        error,
        commands.CommandOnCooldown
    ):

        return await ctx.send(
            "⏳ حاول مرة أخرى بعد قليل."
        )

    logger.exception(
        f"Command Error: {error}"
    )


# =========================================================
# GUILD JOIN
# =========================================================

@bot.event
async def on_guild_join(
    guild
):

    log_event(
        f"Bot Joined Guild | "
        f"{guild.id} | "
        f"{guild.name}"
    )

    existing = db.fetchone(
        """
        SELECT *
        FROM servers
        WHERE guild_id=?
        """,
        (
            guild.id,
        )
    )

    if not existing:

        db.execute(
            """
            INSERT INTO servers(
                guild_id,
                games_count,
                last_game
            )
            VALUES(?,?,?)
            """,
            (
                guild.id,
                0,
                None
            )
        )


# =========================================================
# GUILD REMOVE
# =========================================================

@bot.event
async def on_guild_remove(
    guild
):

    log_event(
        f"Bot Left Guild | "
        f"{guild.id} | "
        f"{guild.name}"
    )

    ACTIVE_GAMES.pop(
        guild.id,
        None
    )

    CURRENT_QUESTION.pop(
        guild.id,
        None
    )


# =========================================================
# READY
# =========================================================

@bot.event
async def on_ready():

    log_event(
        f"Logged in as "
        f"{bot.user} "
        f"({bot.user.id})"
    )

    try:

        synced = await bot.tree.sync()

        log_event(
            f"Slash Commands Synced: "
            f"{len(synced)}"
        )

    except Exception as e:

        logger.exception(
            f"Slash Sync Error: {e}"
        )

    # تحديث أسماء اللاعبين
    for guild in bot.guilds:

        for member in guild.members:

            if member.bot:

                continue

            PlayerData.ensure(
                member
            )

    print(
        "================================="
    )

    print(
        f"🤖 Logged in as: {bot.user}"
    )

    print(
        f"🌐 Servers: {len(bot.guilds)}"
    )

    print(
        "🎮 Price Guess Pro is ONLINE"
    )

    print(
        "================================="
    )


# =========================================================
# START BOT
# =========================================================

if not DISCORD_TOKEN:

    raise RuntimeError(
        "❌ DISCORD_TOKEN environment variable is missing."
    )

bot.run(
    DISCORD_TOKEN
)


# =========================================================
# END OF PART 4
# =========================================================
