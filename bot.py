# =========================================================
# Price Guess Pro
# Part 1
# Core / Config / Database / Models
# discord.py 2.x
# =========================================================

import discord
from discord.ext import commands, tasks
from discord import app_commands

import os
import json
import sqlite3
import asyncio
import random
import logging
from datetime import datetime
from pathlib import Path

# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).parent

CONFIG_FILE = BASE_DIR / "config.json"
SERVERS_FILE = BASE_DIR / "servers.json"
IMAGES_API_FILE = BASE_DIR / "images_api.json"

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
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}

CONFIG = load_json(CONFIG_FILE, {})
SERVERS = load_json(SERVERS_FILE, {})
IMAGES_CONFIG = load_json(IMAGES_API_FILE, {})

# =========================================================
# ENV
# =========================================================

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_USER_ID = int(os.getenv("OWNER_USER_ID", "0"))

# =========================================================
# LOGGER
# =========================================================

log_file = LOGS_DIR / f"{datetime.utcnow().date()}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("PriceGuessBot")

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

        self.db.row_factory = sqlite3.Row

        self.cursor = self.db.cursor()

    def execute(self, query, values=()):
        self.cursor.execute(query, values)
        self.db.commit()

    def fetchone(self, query, values=()):
        self.cursor.execute(query, values)
        return self.cursor.fetchone()

    def fetchall(self, query, values=()):
        self.cursor.execute(query, values)
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
    def ensure(user: discord.User):

        exists = db.fetchone(
            "SELECT * FROM players WHERE user_id=?",
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
    def get(user_id: int):

        return db.fetchone(
            "SELECT * FROM players WHERE user_id=?",
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
        category
    ):
        self.title = title
        self.image_url = image_url
        self.real_price = real_price
        self.category = category

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

        self.game_id = None

        self.created_at = datetime.utcnow()

# =========================================================
# ACTIVE GAMES
# =========================================================

ACTIVE_GAMES = {}

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
# PRODUCT CONFIG
# =========================================================

PRODUCT_CATEGORIES = IMAGES_CONFIG.get(
    "categories",
    []
)

API_ENDPOINT = IMAGES_CONFIG.get(
    "api_url",
    ""
)

API_KEY = IMAGES_CONFIG.get(
    "api_key",
    ""
)

PRICE_MIN = IMAGES_CONFIG.get(
    "price_min",
    50
)

PRICE_MAX = IMAGES_CONFIG.get(
    "price_max",
    120
)

# =========================================================
# HELPERS
# =========================================================

def now():
    return datetime.utcnow().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

def log_event(message: str):

    logger.info(message)

def guild_has_game(guild_id: int):

    return guild_id in ACTIVE_GAMES

# =========================================================
# READY
# =========================================================

log_event("Core Loaded")
log_event("Database Loaded")
log_event("Config Loaded")
log_event("Part 1 Ready")


# =========================================================
# PART 2
# Lobby System
# Registration System
# Buttons
# Difficulty Selection
# =========================================================

class LobbyView(discord.ui.View):

    def __init__(self, session: GameSession):
        super().__init__(timeout=None)

        self.session = session

    async def update_message(
        self,
        interaction: discord.Interaction
    ):

        embed = discord.Embed(
            title="🎮 Price Guess Pro",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="📊 Difficulty",
            value=self.session.difficulty or "Not Selected",
            inline=False
        )

        embed.add_field(
            name="👥 Players",
            value=str(len(self.session.players)),
            inline=False
        )

        players_text = ""

        if self.session.players:
            players_text = "\n".join(
                f"• <@{pid}>"
                for pid in self.session.players
            )
        else:
            players_text = "No Players"

        embed.add_field(
            name="Participants",
            value=players_text,
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
                "❌ فقط منشئ اللعبة يستطيع اختيار الصعوبة.",
                ephemeral=True
            )

        self.session.difficulty = "easy"

        await interaction.response.defer()

        await self.update_message(interaction)

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
                "❌ فقط منشئ اللعبة يستطيع اختيار الصعوبة.",
                ephemeral=True
            )

        self.session.difficulty = "normal"

        await interaction.response.defer()

        await self.update_message(interaction)

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
                "❌ فقط منشئ اللعبة يستطيع اختيار الصعوبة.",
                ephemeral=True
            )

        self.session.difficulty = "hard"

        await interaction.response.defer()

        await self.update_message(interaction)

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

        if uid not in self.session.players:

            self.session.players[uid] = {
                "user": interaction.user,
                "points": 0,
                "correct": 0,
                "wrong": 0
            }

            PlayerData.ensure(interaction.user)

        await interaction.response.send_message(
            "✅ تم الانضمام.",
            ephemeral=True
        )

        await self.update_message(interaction)

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

        if uid in self.session.players:
            del self.session.players[uid]

        await interaction.response.send_message(
            "🚪 تم الخروج.",
            ephemeral=True
        )

        await self.update_message(interaction)

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
                "❌ فقط منشئ اللعبة يستطيع الإلغاء.",
                ephemeral=True
            )

        ACTIVE_GAMES.pop(
            self.session.guild_id,
            None
        )

        embed = discord.Embed(
            title="🛑 Game Cancelled",
            description="تم إلغاء اللعبة.",
            color=discord.Color.red()
        )

        await interaction.response.edit_message(
            embed=embed,
            view=None
        )

# =========================================================
# REGISTRATION TIMER
# =========================================================

async def registration_countdown(
    message,
    session: GameSession
):

    session.registration_open = True

    for remaining in range(
        REGISTRATION_TIME,
        0,
        -1
    ):

        if session.guild_id not in ACTIVE_GAMES:
            return

        embed = discord.Embed(
            title="🎮 Price Guess Pro",
            color=discord.Color.green()
        )

        embed.add_field(
            name="Difficulty",
            value=session.difficulty or "Not Selected",
            inline=False
        )

        embed.add_field(
            name="Players",
            value=str(len(session.players)),
            inline=False
        )

        embed.add_field(
            name="Time Remaining",
            value=f"{remaining}s",
            inline=False
        )

        await message.edit(embed=embed)

        await asyncio.sleep(1)

    session.registration_open = False

    if len(session.players) < MIN_PLAYERS:

        embed = discord.Embed(
            title="❌ Game Cancelled",
            description=(
                f"Minimum players required: "
                f"{MIN_PLAYERS}"
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

    if not session.difficulty:

        embed = discord.Embed(
            title="❌ Game Cancelled",
            description="لم يتم اختيار الصعوبة.",
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

    start_embed = discord.Embed(
        title="🚀 Starting Game",
        description=(
            f"Players: {len(session.players)}\n"
            f"Difficulty: {session.difficulty}"
        ),
        color=discord.Color.gold()
    )

    await message.edit(
        embed=start_embed,
        view=None
    )

    await asyncio.sleep(2)

    await start_game(session, message.channel)

# =========================================================
# CREATE GAME
# =========================================================

async def create_game(
    ctx,
    slash=False
):

    guild_id = ctx.guild.id

    if guild_has_game(guild_id):

        text = "❌ توجد لعبة تعمل بالفعل."

        if slash:
            return await ctx.response.send_message(
                text,
                ephemeral=True
            )
        else:
            return await ctx.send(text)

    session = GameSession(
        guild_id=guild_id,
        channel_id=ctx.channel.id,
        owner_id=ctx.user.id if slash else ctx.author.id
    )

    ACTIVE_GAMES[guild_id] = session

    owner = (
        ctx.user
        if slash
        else ctx.author
    )

    session.players[owner.id] = {
        "user": owner,
        "points": 0,
        "correct": 0,
        "wrong": 0
    }

    view = LobbyView(session)

    embed = discord.Embed(
        title="🎮 Price Guess Pro",
        description=(
            "اختر الصعوبة ثم دع اللاعبين ينضمون.\n\n"
            f"⏳ التسجيل: {REGISTRATION_TIME} ثانية\n"
            f"👥 الحد الأدنى: {MIN_PLAYERS}"
        ),
        color=discord.Color.blurple()
    )

    if slash:

        await ctx.response.send_message(
            embed=embed,
            view=view
        )

        message = await ctx.original_response()

    else:

        message = await ctx.send(
            embed=embed,
            view=view
        )

    asyncio.create_task(
        registration_countdown(
            message,
            session
        )
    )

# =========================================================
# PART 2 END
# =========================================================
# =========================================================
# PART 3
# GAME ENGINE
# =========================================================

CURRENT_QUESTION = {}

# =========================================================
# PRODUCT FETCHER
# =========================================================

async def get_random_product():

    category = random.choice(
        PRODUCT_CATEGORIES
    ) if PRODUCT_CATEGORIES else "general"

    fake_products = [

        {
            "title": "Nivea Cream",
            "price": random.randint(50,120),
            "image": "https://i.ebayimg.com/thumbs/images/g/j4UAAeSw7Vho00sl/s-l500.jpg",
            "category": category
        },

        {
            "title": "Chocolate Box",
            "price": random.randint(50,120),
            "image": "https://i.ebayimg.com/thumbs/images/g/j4UAAeSw7Vho00sl/s-l500.jpg",
            "category": category
        },

        {
            "title": "Perfume",
            "price": random.randint(50,120),
            "image": "https://i.ebayimg.com/thumbs/images/g/j4UAAeSw7Vho00sl/s-l500.jpg",
            "category": category
        }
    ]

    item = random.choice(fake_products)

    return Product(
        title=item["title"],
        image_url=item["image"],
        real_price=item["price"],
        category=item["category"]
    )

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

    session.answers = {}

    embed = discord.Embed(
        title=f"🛒 Product #{image_number}",
        description=(
            "اكتب السعر المتوقع للمنتج\n\n"
            f"⏳ {ANSWER_TIME} ثانية"
        ),
        color=discord.Color.orange()
    )

    embed.add_field(
        name="Category",
        value=product.category,
        inline=False
    )

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
        "message": message
    }

    for sec in range(
        ANSWER_TIME,
        0,
        -1
    ):

        players_count = len(
            session.players
        )

        answers_count = len(
            session.answers
        )

        if answers_count >= players_count:

            break

        await asyncio.sleep(1)

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

    for uid in session.answers:

        answer = session.answers[uid]

        difference = abs(
            answer - real_price
        )

        results.append({
            "user_id": uid,
            "answer": answer,
            "difference": difference
        })

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

    for idx, row in enumerate(results):

        uid = row["user_id"]

        pts = gained.get(
            uid,
            1
        )

        session.players[uid][
            "points"
        ] += pts

        if idx < len(medals):
            medal = medals[idx]
        else:
            medal = "🎖️"

        result_text += (
            f"{medal} "
            f"<@{uid}> "
            f"(+{pts})\n"
            f"Difference: "
            f"{row['difference']}\n\n"
        )

    for uid in session.players:

        if uid not in session.answers:

            result_text += (
                f"❌ <@{uid}> "
                f"(No Answer)\n\n"
            )

    embed = discord.Embed(
        title="📊 Round Results",
        color=discord.Color.green()
    )

    embed.add_field(
        name="Real Price",
        value=f"${real_price}",
        inline=False
    )

    embed.add_field(
        name="Ranking",
        value=result_text[:1024],
        inline=False
    )

    await channel.send(
        embed=embed
    )

    await asyncio.sleep(3)

# =========================================================
# PLAY ALL PRODUCTS
# =========================================================

async def start_game(
    session,
    channel
):

    log_event(
        f"Game Started "
        f"{session.guild_id}"
    )

    total_images = 15

    current = 1

    while current <= total_images:

        product = await get_random_product()

        await question_timer(
            session,
            channel,
            product,
            current
        )

        current += 1

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

    text = ""

    medals = [
        "🏆",
        "🥈",
        "🥉"
    ]

    for index, data in enumerate(
        ranking
    ):

        uid = data[0]

        points = data[1][
            "points"
        ]

        if index < 3:
            medal = medals[index]
        else:
            medal = "🎖️"

        text += (
            f"{medal} "
            f"<@{uid}> "
            f"- {points} pts\n"
        )

    embed = discord.Embed(
        title="🏁 Final Results",
        description=text,
        color=discord.Color.gold()
    )

    await channel.send(
        embed=embed
    )

    ACTIVE_GAMES.pop(
        session.guild_id,
        None
    )

    CURRENT_QUESTION.pop(
        session.guild_id,
        None
    )

    log_event(
        f"Game Finished "
        f"{session.guild_id}"
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

            if (
                message.author.id
                in session.players
            ):

                try:

                    value = float(
                        message.content
                    )

                    if (
                        message.author.id
                        not in session.answers
                    ):

                        session.answers[
                            message.author.id
                        ] = value

                        await message.add_reaction(
                            "✅"
                        )

                except:
                    pass

    await bot.process_commands(
        message
    )

# =========================================================
# PART 3 END
# =========================================================

# =========================================================
# PART 4
# Commands
# Profile
# Top
# Stats
# Stop
# Ready
# =========================================================

# ---------------------------------------------------------
# PROFILE
# ---------------------------------------------------------

async def profile_embed(user):

    PlayerData.ensure(user)

    data = PlayerData.get(user.id)

    embed = discord.Embed(
        title=f"👤 {user}",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="🎮 Games",
        value=data["games_played"],
        inline=True
    )

    embed.add_field(
        name="🏆 Wins",
        value=data["wins"],
        inline=True
    )

    embed.add_field(
        name="🥈 Seconds",
        value=data["second_places"],
        inline=True
    )

    embed.add_field(
        name="🥉 Thirds",
        value=data["third_places"],
        inline=True
    )

    embed.add_field(
        name="⭐ Points",
        value=data["total_points"],
        inline=True
    )

    embed.add_field(
        name="🔥 Best Score",
        value=data["best_score"],
        inline=True
    )

    embed.add_field(
        name="✅ Correct",
        value=data["correct_answers"],
        inline=True
    )

    embed.add_field(
        name="❌ Wrong",
        value=data["wrong_answers"],
        inline=True
    )

    return embed

# ---------------------------------------------------------
# SLASH GAME
# ---------------------------------------------------------

@bot.tree.command(
    name="game",
    description="Start a game"
)
async def slash_game(
    interaction: discord.Interaction
):

    await create_game(
        interaction,
        slash=True
    )

# ---------------------------------------------------------
# PREFIX GAME
# ---------------------------------------------------------

@bot.command(name="game")
async def prefix_game(ctx):

    await create_game(
        ctx,
        slash=False
    )

# ---------------------------------------------------------
# STOP
# ---------------------------------------------------------

@bot.tree.command(
    name="stop",
    description="Stop game"
)
async def slash_stop(
    interaction: discord.Interaction
):

    guild_id = interaction.guild.id

    if guild_id not in ACTIVE_GAMES:

        return await interaction.response.send_message(
            "❌ لا توجد لعبة.",
            ephemeral=True
        )

    ACTIVE_GAMES.pop(
        guild_id,
        None
    )

    await interaction.response.send_message(
        "🛑 تم إيقاف اللعبة."
    )

@bot.command(name="stop")
async def prefix_stop(ctx):

    guild_id = ctx.guild.id

    if guild_id not in ACTIVE_GAMES:

        return await ctx.send(
            "❌ لا توجد لعبة."
        )

    ACTIVE_GAMES.pop(
        guild_id,
        None
    )

    await ctx.send(
        "🛑 تم إيقاف اللعبة."
    )

# ---------------------------------------------------------
# PROFILE
# ---------------------------------------------------------

@bot.tree.command(
    name="profile",
    description="Player profile"
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

@bot.command(name="profile")
async def prefix_profile(ctx):

    embed = await profile_embed(
        ctx.author
    )

    await ctx.send(
        embed=embed
    )

# ---------------------------------------------------------
# TOP
# ---------------------------------------------------------

@bot.tree.command(
    name="top",
    description="Top players"
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

    text = ""

    rank = 1

    for row in rows:

        text += (
            f"{rank}. "
            f"{row['username']} "
            f"({row['total_points']})\n"
        )

        rank += 1

    embed = discord.Embed(
        title="🏆 Top 10 Players",
        description=text or "No Data",
        color=discord.Color.gold()
    )

    await interaction.response.send_message(
        embed=embed
    )

@bot.command(name="top")
async def prefix_top(ctx):

    rows = db.fetchall(
        """
        SELECT *
        FROM players
        ORDER BY total_points DESC
        LIMIT 10
        """
    )

    text = ""

    rank = 1

    for row in rows:

        text += (
            f"{rank}. "
            f"{row['username']} "
            f"({row['total_points']})\n"
        )

        rank += 1

    embed = discord.Embed(
        title="🏆 Top 10 Players",
        description=text or "No Data",
        color=discord.Color.gold()
    )

    await ctx.send(
        embed=embed
    )

# ---------------------------------------------------------
# STATS
# ---------------------------------------------------------

@bot.tree.command(
    name="stats",
    description="Bot stats"
)
async def slash_stats(
    interaction: discord.Interaction
):

    players = db.fetchone(
        "SELECT COUNT(*) c FROM players"
    )["c"]

    games = db.fetchone(
        "SELECT COUNT(*) c FROM games"
    )["c"]

    embed = discord.Embed(
        title="📊 Statistics",
        color=discord.Color.green()
    )

    embed.add_field(
        name="Players",
        value=str(players)
    )

    embed.add_field(
        name="Games",
        value=str(games)
    )

    embed.add_field(
        name="Servers",
        value=str(len(bot.guilds))
    )

    await interaction.response.send_message(
        embed=embed
    )

@bot.command(name="stats")
async def prefix_stats(ctx):

    players = db.fetchone(
        "SELECT COUNT(*) c FROM players"
    )["c"]

    games = db.fetchone(
        "SELECT COUNT(*) c FROM games"
    )["c"]

    embed = discord.Embed(
        title="📊 Statistics",
        color=discord.Color.green()
    )

    embed.add_field(
        name="Players",
        value=str(players)
    )

    embed.add_field(
        name="Games",
        value=str(games)
    )

    embed.add_field(
        name="Servers",
        value=str(len(bot.guilds))
    )

    await ctx.send(
        embed=embed
    )

# ---------------------------------------------------------
# HELP
# ---------------------------------------------------------

HELP_TEXT = """
🎮 Price Guess Pro

/game
!game

/stop
!stop

/profile
!profile

/top
!top

/stats
!stats

/help
!help
"""

@bot.tree.command(
    name="help",
    description="Help menu"
)
async def slash_help(
    interaction: discord.Interaction
):

    embed = discord.Embed(
        title="📖 Help",
        description=HELP_TEXT,
        color=discord.Color.blurple()
    )

    await interaction.response.send_message(
        embed=embed
    )

@bot.command(name="help")
async def prefix_help(ctx):

    embed = discord.Embed(
        title="📖 Help",
        description=HELP_TEXT,
        color=discord.Color.blurple()
    )

    await ctx.send(
        embed=embed
    )

# ---------------------------------------------------------
# READY
# ---------------------------------------------------------

@bot.event
async def on_ready():

    try:

        synced = await bot.tree.sync()

        print(
            f"Synced {len(synced)} commands"
        )

    except Exception as e:

        print(e)

    print(
        f"Logged as {bot.user}"
    )

    log_event(
        "Bot Ready"
    )

# ---------------------------------------------------------
# START
# ---------------------------------------------------------

if not DISCORD_TOKEN:

    raise RuntimeError(
        "DISCORD_TOKEN missing"
    )

bot.run(DISCORD_TOKEN)

# =========================================================
# END OF FILE
# =========================================================


