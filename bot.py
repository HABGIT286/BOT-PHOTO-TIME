import os
import json
import sqlite3
import random
import asyncio
import aiohttp
from datetime import datetime

import discord
from discord.ext import commands
from discord import app_commands

# =====================================================
# CONFIG
# =====================================================

with open("config.json", "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

TOKEN = os.getenv("DISCORD_TOKEN")

PREFIX = CONFIG.get("prefix", "!")
BOT_NAME = CONFIG.get("bot_name", "Price Guess Pro")

DATABASE = "price_guess.db"

# =====================================================
# DISCORD
# =====================================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None
)

tree = bot.tree

# =====================================================
# ACTIVE GAMES
# =====================================================

active_games = {}

# =====================================================
# SQLITE
# =====================================================

db = sqlite3.connect(
    DATABASE,
    check_same_thread=False
)

cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS players(
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    games_played INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    second_places INTEGER DEFAULT 0,
    third_places INTEGER DEFAULT 0,
    total_points INTEGER DEFAULT 0,
    correct_answers INTEGER DEFAULT 0,
    wrong_answers INTEGER DEFAULT 0,
    best_score INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS games(
    game_id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    started_at TEXT,
    ended_at TEXT,
    difficulty TEXT,
    players_count INTEGER
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS rounds(
    round_id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER,
    round_number INTEGER,
    product_name TEXT,
    real_price REAL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS answers(
    answer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER,
    round_number INTEGER,
    user_id INTEGER,
    answer REAL,
    difference REAL
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS servers(
    guild_id INTEGER PRIMARY KEY,
    total_games INTEGER DEFAULT 0
)
""")

db.commit()

# =====================================================
# DATABASE HELPERS
# =====================================================

def ensure_player(user: discord.Member):

    cursor.execute(
        "SELECT user_id FROM players WHERE user_id=?",
        (user.id,)
    )

    if cursor.fetchone():
        return

    cursor.execute("""
    INSERT INTO players(
        user_id,
        username
    )
    VALUES (?,?)
    """, (
        user.id,
        str(user)
    ))

    db.commit()


def add_points(user_id: int, points: int):

    cursor.execute("""
    UPDATE players
    SET total_points = total_points + ?
    WHERE user_id = ?
    """, (
        points,
        user_id
    ))

    db.commit()


def add_game_played(user_id: int):

    cursor.execute("""
    UPDATE players
    SET games_played = games_played + 1
    WHERE user_id = ?
    """, (
        user_id,
    ))

    db.commit()


# =====================================================
# PRODUCT API
# =====================================================

class ProductFetcher:

    def __init__(self):
        self.url = "https://www.ebay.com/deals/tech"

    async def get_random_product(self):

        products = [
            {
                "name": "Headphones",
                "price": random.randint(20, 150),
                "image": "https://i.imgur.com/0Z8FQ8P.png"
            },
            {
                "name": "Smart Watch",
                "price": random.randint(40, 300),
                "image": "https://i.imgur.com/3jLPB46.png"
            },
            {
                "name": "Perfume",
                "price": random.randint(10, 90),
                "image": "https://i.imgur.com/Z6X1K8X.png"
            },
            {
                "name": "Chocolate Box",
                "price": random.randint(5, 40),
                "image": "https://i.imgur.com/sF5JY2m.png"
            },
            {
                "name": "Shampoo",
                "price": random.randint(3, 35),
                "image": "https://i.imgur.com/5g0g8nK.png"
            },
            {
                "name": "Coffee Pack",
                "price": random.randint(5, 50),
                "image": "https://i.imgur.com/90E4g7P.png"
            }
        ]

        return random.choice(products)

fetcher = ProductFetcher()

# =====================================================
# GAME CLASS
# =====================================================

class PriceGuessGame:

    def __init__(
        self,
        guild_id,
        host_id,
        difficulty
    ):

        self.guild_id = guild_id
        self.host_id = host_id

        self.difficulty = difficulty

        self.players = {}

        self.answers = {}

        self.started = False

        self.rounds_total = 3
        self.images_per_round = 3

        self.current_round = 0

        self.current_image = 0

        self.game_points = {}

        self.game_id = None
        # =====================================================
# LOBBY BUTTONS
# =====================================================

class LobbyView(discord.ui.View):

    def __init__(self, game):
        super().__init__(timeout=20)

        self.game = game

        self.message = None

    async def update_embed(self):

        if not self.message:
            return

        players_text = "\n".join(
            [f"• <@{uid}>" for uid in self.game.players]
        )

        if not players_text:
            players_text = "لا يوجد لاعبين"

        embed = discord.Embed(
            title="🎮 Price Guess Pro",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="📊 الصعوبة",
            value=self.game.difficulty,
            inline=False
        )

        embed.add_field(
            name="👥 اللاعبين",
            value=players_text,
            inline=False
        )

        embed.add_field(
            name="📈 العدد",
            value=f"{len(self.game.players)} لاعب",
            inline=False
        )

        embed.set_footer(
            text="التسجيل يغلق خلال 20 ثانية"
        )

        await self.message.edit(
            embed=embed,
            view=self
        )

    # =================================================
    # JOIN
    # =================================================

    @discord.ui.button(
        label="انضمام",
        emoji="✅",
        style=discord.ButtonStyle.green
    )
    async def join_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        ensure_player(interaction.user)

        if interaction.user.id not in self.game.players:

            self.game.players[
                interaction.user.id
            ] = interaction.user

            self.game.game_points[
                interaction.user.id
            ] = 0

        await interaction.response.send_message(
            "✅ تم الانضمام",
            ephemeral=True
        )

        await self.update_embed()

    # =================================================
    # LEAVE
    # =================================================

    @discord.ui.button(
        label="مغادرة",
        emoji="❌",
        style=discord.ButtonStyle.red
    )
    async def leave_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.user.id in self.game.players:

            del self.game.players[
                interaction.user.id
            ]

        if interaction.user.id in self.game.game_points:

            del self.game.game_points[
                interaction.user.id
            ]

        await interaction.response.send_message(
            "❌ غادرت اللعبة",
            ephemeral=True
        )

        await self.update_embed()

    # =================================================
    # CANCEL
    # =================================================

    @discord.ui.button(
        label="إلغاء",
        emoji="🛑",
        style=discord.ButtonStyle.gray
    )
    async def cancel_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.user.id != self.game.host_id:

            return await interaction.response.send_message(
                "❌ فقط منشئ اللعبة يستطيع الإلغاء",
                ephemeral=True
            )

        if self.game.guild_id in active_games:
            del active_games[self.game.guild_id]

        embed = discord.Embed(
            title="🛑 تم إلغاء اللعبة",
            color=discord.Color.red()
        )

        await interaction.response.edit_message(
            embed=embed,
            view=None
        )

        self.stop()


# =====================================================
# START LOBBY
# =====================================================

async def start_lobby(ctx, difficulty):

    guild_id = ctx.guild.id

    if guild_id in active_games:

        embed = discord.Embed(
            title="❌",
            description="يوجد لعبة تعمل بالفعل",
            color=discord.Color.red()
        )

        return await ctx.send(embed=embed)

    game = PriceGuessGame(
        guild_id=guild_id,
        host_id=ctx.author.id,
        difficulty=difficulty
    )

    active_games[guild_id] = game

    ensure_player(ctx.author)

    game.players[ctx.author.id] = ctx.author
    game.game_points[ctx.author.id] = 0

    view = LobbyView(game)

    embed = discord.Embed(
        title="🎮 Price Guess Pro",
        description=(
            "اضغط انضمام للمشاركة\n\n"
            f"📊 الصعوبة: **{difficulty}**\n"
            "⏳ التسجيل: 20 ثانية\n"
            "👥 الحد الأدنى: 2 لاعبين"
        ),
        color=discord.Color.blurple()
    )

    msg = await ctx.send(
        embed=embed,
        view=view
    )

    view.message = msg

    await asyncio.sleep(20)

    if guild_id not in active_games:
        return

    if len(game.players) < 2:

        embed = discord.Embed(
            title="❌ تم إلغاء اللعبة",
            description="لم يكتمل الحد الأدنى للاعبين",
            color=discord.Color.red()
        )

        await msg.edit(
            embed=embed,
            view=None
        )

        del active_games[guild_id]

        return

    game.started = True

    embed = discord.Embed(
        title="🚀 بدأت اللعبة",
        description=(
            f"عدد اللاعبين: {len(game.players)}\n"
            f"الصعوبة: {difficulty}"
        ),
        color=discord.Color.green()
    )

    await msg.edit(
        embed=embed,
        view=None
    )

    await run_game(
        ctx.channel,
        game
    )


# =====================================================
# DIFFICULTY BUTTONS
# =====================================================

class DifficultyView(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(
        label="Easy",
        emoji="🟢",
        style=discord.ButtonStyle.green
    )
    async def easy(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.defer()

        fake_ctx = await bot.get_context(
            interaction.message
        )

        fake_ctx.author = interaction.user

        await start_lobby(
            fake_ctx,
            "Easy"
        )

    @discord.ui.button(
        label="Normal",
        emoji="🟡",
        style=discord.ButtonStyle.blurple
    )
    async def normal(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.defer()

        fake_ctx = await bot.get_context(
            interaction.message
        )

        fake_ctx.author = interaction.user

        await start_lobby(
            fake_ctx,
            "Normal"
        )

    @discord.ui.button(
        label="Hard",
        emoji="🔴",
        style=discord.ButtonStyle.red
    )
    async def hard(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.defer()

        fake_ctx = await bot.get_context(
            interaction.message
        )

        fake_ctx.author = interaction.user

        await start_lobby(
            fake_ctx,
            "Hard"
        )

        # =====================================================
# GAME ENGINE
# =====================================================

async def wait_for_answers(channel, game, product):

    game.answers = {}

    time_limit = 20

    def check(message):

        if message.channel.id != channel.id:
            return False

        if message.author.bot:
            return False

        if message.author.id not in game.players:
            return False

        try:
            float(message.content)
            return True
        except:
            return False

    start_time = asyncio.get_event_loop().time()

    while True:

        remaining = time_limit - (
            asyncio.get_event_loop().time() - start_time
        )

        if remaining <= 0:
            break

        try:

            msg = await bot.wait_for(
                "message",
                timeout=remaining,
                check=check
            )

            if msg.author.id not in game.answers:

                game.answers[msg.author.id] = float(
                    msg.content
                )

                if len(game.answers) >= len(game.players):
                    break

        except asyncio.TimeoutError:
            break

    results = []

    real_price = float(product["price"])

    for uid in game.players:

        if uid not in game.answers:

            results.append({
                "user_id": uid,
                "answer": None,
                "difference": 999999999
            })

            continue

        answer = game.answers[uid]

        diff = abs(real_price - answer)

        results.append({
            "user_id": uid,
            "answer": answer,
            "difference": diff
        })

    results.sort(
        key=lambda x: x["difference"]
    )

    return results


# =====================================================
# SCORE SYSTEM
# =====================================================

def calculate_points(position):

    table = {
        1: 10,
        2: 7,
        3: 5,
        4: 3
    }

    return table.get(position, 1)


# =====================================================
# ROUND RESULT
# =====================================================

async def show_round_result(
    channel,
    game,
    product,
    results
):

    embed = discord.Embed(
        title="📊 نتائج الصورة",
        color=discord.Color.gold()
    )

    embed.add_field(
        name="💰 السعر الحقيقي",
        value=f"${product['price']}",
        inline=False
    )

    text = ""

    position = 0

    for row in results:

        uid = row["user_id"]

        if row["answer"] is None:

            text += (
                f"❌ <@{uid}> "
                f"(لم يجب)\n"
            )

            continue

        position += 1

        points = calculate_points(
            position
        )

        game.game_points[uid] += points

        text += (
            f"#{position} "
            f"<@{uid}> "
            f"(+{points}) | "
            f"فرق: {row['difference']:.2f}\n"
        )

    embed.add_field(
        name="🏆 الترتيب",
        value=text[:1024],
        inline=False
    )

    await channel.send(
        embed=embed
    )


# =====================================================
# PRODUCT DISPLAY
# =====================================================

async def send_product(
    channel,
    game,
    product,
    current_index,
    total_images
):

    embed = discord.Embed(
        title="🛒 تخمين السعر",
        color=discord.Color.blue()
    )

    embed.description = (
        f"الصورة {current_index}/{total_images}\n"
        f"⏳ لديك 20 ثانية\n\n"
        f"اكتب السعر المتوقع في الشات"
    )

    embed.set_image(
        url=product["image"]
    )

    await channel.send(
        embed=embed
    )


# =====================================================
# GAME LOOP
# =====================================================

async def run_game(
    channel,
    game
):

    total_images = (
        game.rounds_total *
        game.images_per_round
    )

    image_number = 0

    for round_number in range(
        1,
        game.rounds_total + 1
    ):

        game.current_round = round_number

        round_embed = discord.Embed(
            title=f"🎯 الجولة {round_number}",
            description=(
                f"{game.images_per_round} صور"
            ),
            color=discord.Color.green()
        )

        await channel.send(
            embed=round_embed
        )

        for image_index in range(
            1,
            game.images_per_round + 1
        ):

            image_number += 1

            product = await fetcher.get_random_product()

            await send_product(
                channel,
                game,
                product,
                image_number,
                total_images
            )

            results = await wait_for_answers(
                channel,
                game,
                product
            )

            await show_round_result(
                channel,
                game,
                product,
                results
            )

            await asyncio.sleep(2)

    await finish_game(
        channel,
        game
                )




# =====================================================
# FINAL RESULTS
# =====================================================

async def finish_game(channel, game):

    ranking = sorted(
        game.game_points.items(),
        key=lambda x: x[1],
        reverse=True
    )

    embed = discord.Embed(
        title="🏆 النتائج النهائية",
        color=discord.Color.gold()
    )

    result_text = ""

    medals = [
        "🥇",
        "🥈",
        "🥉"
    ]

    for index, (user_id, score) in enumerate(ranking, start=1):

        medal = (
            medals[index - 1]
            if index <= 3
            else "🏅"
        )

        result_text += (
            f"{medal} <@{user_id}> "
            f"— {score} نقطة\n"
        )

        add_game_played(user_id)

        add_points(
            user_id,
            score
        )

    embed.description = result_text

    await channel.send(embed=embed)

    if game.guild_id in active_games:
        del active_games[game.guild_id]


# =====================================================
# PROFILE
# =====================================================

async def profile_embed(user):

    ensure_player(user)

    cursor.execute("""
    SELECT
    games_played,
    wins,
    second_places,
    third_places,
    total_points,
    correct_answers,
    wrong_answers,
    best_score
    FROM players
    WHERE user_id=?
    """, (
        user.id,
    ))

    row = cursor.fetchone()

    embed = discord.Embed(
        title=f"👤 {user}",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="🎮 الألعاب",
        value=row[0]
    )

    embed.add_field(
        name="🏆 الانتصارات",
        value=row[1]
    )

    embed.add_field(
        name="🥈 المركز الثاني",
        value=row[2]
    )

    embed.add_field(
        name="🥉 المركز الثالث",
        value=row[3]
    )

    embed.add_field(
        name="⭐ النقاط",
        value=row[4]
    )

    embed.add_field(
        name="✅ الصحيحة",
        value=row[5]
    )

    embed.add_field(
        name="❌ الخاطئة",
        value=row[6]
    )

    embed.add_field(
        name="🔥 أفضل نتيجة",
        value=row[7]
    )

    return embed


# =====================================================
# PREFIX COMMANDS
# =====================================================

@bot.command(name="game")
async def game_prefix(ctx):

    view = DifficultyView()

    embed = discord.Embed(
        title="🎮 Price Guess Pro",
        description="اختر مستوى الصعوبة",
        color=discord.Color.green()
    )

    await ctx.send(
        embed=embed,
        view=view
    )


@bot.command(name="stop")
async def stop_prefix(ctx):

    gid = ctx.guild.id

    if gid not in active_games:
        return await ctx.send(
            "❌ لا توجد لعبة"
        )

    del active_games[gid]

    await ctx.send(
        "🛑 تم إيقاف اللعبة"
    )


@bot.command(name="profile")
async def profile_prefix(ctx):

    embed = await profile_embed(
        ctx.author
    )

    await ctx.send(embed=embed)


@bot.command(name="top")
async def top_prefix(ctx):

    cursor.execute("""
    SELECT
    username,
    total_points
    FROM players
    ORDER BY total_points DESC
    LIMIT 10
    """)

    rows = cursor.fetchall()

    embed = discord.Embed(
        title="🏆 أفضل 10 لاعبين",
        color=discord.Color.gold()
    )

    text = ""

    for i, row in enumerate(rows, start=1):

        text += (
            f"{i}. "
            f"{row[0]} "
            f"({row[1]})\n"
        )

    embed.description = text

    await ctx.send(embed=embed)


@bot.command(name="stats")
async def stats_prefix(ctx):

    cursor.execute(
        "SELECT COUNT(*) FROM players"
    )

    players_count = cursor.fetchone()[0]

    embed = discord.Embed(
        title="📊 إحصائيات البوت",
        color=discord.Color.blurple()
    )

    embed.add_field(
        name="👥 اللاعبين",
        value=players_count
    )

    embed.add_field(
        name="🎮 الألعاب النشطة",
        value=len(active_games)
    )

    await ctx.send(embed=embed)


@bot.command(name="help")
async def help_prefix(ctx):

    embed = discord.Embed(
        title="📖 المساعدة",
        color=discord.Color.green()
    )

    embed.description = (
        "!game\n"
        "!stop\n"
        "!profile\n"
        "!top\n"
        "!stats\n"
        "!help"
    )

    await ctx.send(embed=embed)


# =====================================================
# SLASH COMMANDS
# =====================================================

@tree.command(
    name="game",
    description="بدء لعبة"
)
async def slash_game(
    interaction: discord.Interaction
):

    view = DifficultyView()

    embed = discord.Embed(
        title="🎮 Price Guess Pro",
        description="اختر مستوى الصعوبة"
    )

    await interaction.response.send_message(
        embed=embed,
        view=view
    )


@tree.command(
    name="stop",
    description="إيقاف اللعبة"
)
async def slash_stop(
    interaction: discord.Interaction
):

    gid = interaction.guild.id

    if gid in active_games:
        del active_games[gid]

    await interaction.response.send_message(
        "🛑 تم إيقاف اللعبة"
    )


@tree.command(
    name="profile",
    description="ملف اللاعب"
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


@tree.command(
    name="top",
    description="المتصدرون"
)
async def slash_top(
    interaction: discord.Interaction
):

    cursor.execute("""
    SELECT username,total_points
    FROM players
    ORDER BY total_points DESC
    LIMIT 10
    """)

    rows = cursor.fetchall()

    text = ""

    for i, row in enumerate(rows, start=1):

        text += (
            f"{i}. {row[0]}"
            f" ({row[1]})\n"
        )

    embed = discord.Embed(
        title="🏆 Top 10",
        description=text
    )

    await interaction.response.send_message(
        embed=embed
    )


@tree.command(
    name="stats",
    description="إحصائيات البوت"
)
async def slash_stats(
    interaction: discord.Interaction
):

    cursor.execute(
        "SELECT COUNT(*) FROM players"
    )

    count = cursor.fetchone()[0]

    await interaction.response.send_message(
        f"👥 اللاعبين: {count}\n"
        f"🎮 الألعاب النشطة: {len(active_games)}"
    )


@tree.command(
    name="help",
    description="المساعدة"
)
async def slash_help(
    interaction: discord.Interaction
):

    await interaction.response.send_message(
        "/game\n"
        "/stop\n"
        "/profile\n"
        "/top\n"
        "/stats\n"
        "/help"
    )


# =====================================================
# READY
# =====================================================

@bot.event
async def on_ready():

    try:
        synced = await tree.sync()

        print(
            f"Synced {len(synced)} commands"
        )

    except Exception as e:
        print(e)

    print(
        f"Logged in as {bot.user}"
    )


# =====================================================
# RUN
# =====================================================

bot.run(TOKEN)
    




    
        
