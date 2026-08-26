import os
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp


# ============================================================
# CONFIG
# ============================================================

TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

MAX_RESULTS = 8


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("MusicBot")


# ============================================================
# INTENTS
# ============================================================

intents = discord.Intents.default()


# ============================================================
# SONG
# ============================================================

@dataclass
class Song:

    title: str
    url: str
    webpage_url: str
    duration: int
    thumbnail: Optional[str]
    requester_id: int

    @property
    def duration_text(self):

        if not self.duration:
            return "LIVE"

        minutes = self.duration // 60
        seconds = self.duration % 60

        return f"{minutes}:{seconds:02d}"


# ============================================================
# MUSIC PLAYER
# ============================================================

@dataclass
class MusicPlayer:

    guild_id: int

    queue: list[Song] = field(default_factory=list)

    current: Optional[Song] = None

    voice: Optional[discord.VoiceClient] = None

    repeat: bool = False

    paused: bool = False

    text_channel: Optional[discord.TextChannel] = None

    playing_task: Optional[asyncio.Task] = None

    lock: asyncio.Lock = field(
        default_factory=asyncio.Lock
    )


players: dict[int, MusicPlayer] = {}


def get_player(guild_id: int):

    if guild_id not in players:

        players[guild_id] = MusicPlayer(
            guild_id=guild_id
        )

    return players[guild_id]


# ============================================================
# YOUTUBE SEARCH
# ============================================================

def youtube_search(query: str):

    options = {

        "quiet": True,

        "no_warnings": True,

        "extract_flat": True,

        "skip_download": True,

        "noplaylist": True,

        "socket_timeout": 20,

    }

    try:

        with yt_dlp.YoutubeDL(options) as ydl:

            data = ydl.extract_info(
                f"ytsearch{MAX_RESULTS}:{query}",
                download=False
            )

        results = []

        for item in data.get("entries", []):

            if not item:
                continue

            video_id = item.get("id")

            if not video_id:
                continue

            duration = item.get("duration") or 0

            results.append({

                "title": item.get(
                    "title",
                    "Unknown"
                ),

                "url":
                    f"https://www.youtube.com/watch?v={video_id}",

                "duration": duration,

                "thumbnail":
                    item.get("thumbnail"),

            })

        return results

    except Exception:

        logger.exception(
            "YouTube search failed"
        )

        return []


# ============================================================
# GET AUDIO SOURCE
# ============================================================

def get_audio_source(url: str):

    options = {

        "quiet": True,

        "no_warnings": True,

        "format":
            "bestaudio/best",

        "noplaylist": True,

        "socket_timeout": 30,

    }

    with yt_dlp.YoutubeDL(options) as ydl:

        info = ydl.extract_info(
            url,
            download=False
        )

        audio_url = info.get("url")

        if not audio_url:

            raise RuntimeError(
                "Audio source unavailable"
            )

        return audio_url


# ============================================================
# DISCORD BOT
# ============================================================

class MusicBot(commands.Bot):

    def __init__(self):

        super().__init__(
            command_prefix="!",
            intents=intents
        )

    async def setup_hook(self):

        await self.tree.sync()

        logger.info(
            "Slash commands synchronized."
        )


bot = MusicBot()


# ============================================================
# SEARCH RESULT VIEW
# ============================================================

class SearchView(discord.ui.View):

    def __init__(
        self,
        author_id: int,
        results,
        timeout=60
    ):

        super().__init__(
            timeout=timeout
        )

        self.author_id = author_id
        self.results = results

        for index, song in enumerate(results):

            if index >= 8:
                break

            title = song["title"]

            if len(title) > 70:

                title = (
                    title[:67]
                    + "..."
                )

            button = discord.ui.Button(
                label=f"{index + 1}. {title}",
                style=discord.ButtonStyle.secondary,
                custom_id=f"music_select_{index}"
            )

            button.callback = self.make_callback(
                index
            )

            self.add_item(button)

    def make_callback(self, index):

        async def callback(
            interaction: discord.Interaction
        ):

            if interaction.user.id != self.author_id:

                await interaction.response.send_message(
                    "❌ هذه القائمة ليست لك.",
                    ephemeral=True
                )

                return

            song = self.results[index]

            await interaction.response.defer()

            guild = interaction.guild

            if not guild:

                return

            player = get_player(
                guild.id
            )

            voice_state = interaction.user.voice

            if not voice_state:

                await interaction.followup.send(
                    "❌ ادخل Voice Channel أولاً.",
                    ephemeral=True
                )

                return

            channel = voice_state.channel

            try:

                if player.voice is None:

                    player.voice = await channel.connect()

                elif player.voice.channel != channel:

                    await player.voice.move_to(
                        channel
                    )

            except Exception:

                logger.exception(
                    "Voice connection error"
                )

                await interaction.followup.send(
                    "❌ لم أستطع الدخول إلى الروم الصوتي.",
                    ephemeral=True
                )

                return

            new_song = Song(

                title=song["title"],

                url=song["url"],

                webpage_url=song["url"],

                duration=song["duration"],

                thumbnail=song.get(
                    "thumbnail"
                ),

                requester_id=interaction.user.id
            )

            player.text_channel = interaction.channel

            if player.current is None:

                player.queue.append(
                    new_song
                )

                await interaction.followup.send(
                    f"🎵 **تمت إضافة:** `{new_song.title}`\n"
                    f"▶️ سأبدأ التشغيل الآن."
                )

                await start_next(
                    guild.id
                )

            else:

                player.queue.append(
                    new_song
                )

                await interaction.followup.send(
                    f"➕ **تمت إضافة للقائمة:**\n"
                    f"🎵 `{new_song.title}`\n\n"
                    f"📋 المركز: `{len(player.queue)}`"
                )

        return callback


# ============================================================
# PLAYER VIEW
# ============================================================

class PlayerView(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        emoji="⏮️",
        style=discord.ButtonStyle.secondary
    )
    async def previous(
        self,
        interaction,
        button
    ):

        player = get_player(
            interaction.guild.id
        )

        if not player.current:

            await interaction.response.send_message(
                "❌ لا توجد أغنية حالية.",
                ephemeral=True
            )

            return

        await interaction.response.defer()

        # إعادة الأغنية السابقة
        if player.current:

            player.queue.insert(
                0,
                player.current
            )

        if player.voice:

            player.voice.stop()

    @discord.ui.button(
        emoji="⏯️",
        style=discord.ButtonStyle.primary
    )
    async def pause_resume(
        self,
        interaction,
        button
    ):

        player = get_player(
            interaction.guild.id
        )

        if not player.voice:

            await interaction.response.send_message(
                "❌ لا يوجد تشغيل.",
                ephemeral=True
            )

            return

        if player.voice.is_playing():

            player.voice.pause()

            player.paused = True

            await interaction.response.send_message(
                "⏸️ تم إيقاف الأغنية مؤقتًا.",
                ephemeral=True
            )

        elif player.voice.is_paused():

            player.voice.resume()

            player.paused = False

            await interaction.response.send_message(
                "▶️ تم استئناف الأغنية.",
                ephemeral=True
            )

        else:

            await interaction.response.send_message(
                "❌ لا توجد أغنية تعمل.",
                ephemeral=True
            )

    @discord.ui.button(
        emoji="⏭️",
        style=discord.ButtonStyle.secondary
    )
    async def skip(
        self,
        interaction,
        button
    ):

        player = get_player(
            interaction.guild.id
        )

        if not player.voice:

            await interaction.response.send_message(
                "❌ لا يوجد تشغيل.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "⏭️ تم تخطي الأغنية.",
            ephemeral=True
        )

        player.voice.stop()

    @discord.ui.button(
        emoji="🔁",
        style=discord.ButtonStyle.success
    )
    async def repeat(
        self,
        interaction,
        button
    ):

        player = get_player(
            interaction.guild.id
        )

        player.repeat = not player.repeat

        state = (
            "مفعّل 🔁"
            if player.repeat
            else "متوقف ⏹️"
        )

        await interaction.response.send_message(
            f"🔁 التكرار: **{state}**",
            ephemeral=True
        )

    @discord.ui.button(
        emoji="⏹️",
        style=discord.ButtonStyle.danger
    )
    async def stop(
        self,
        interaction,
        button
    ):

        player = get_player(
            interaction.guild.id
        )

        player.queue.clear()

        player.repeat = False

        player.current = None

        if player.voice:

            player.voice.stop()

        await interaction.response.send_message(
            "⏹️ تم إيقاف التشغيل ومسح القائمة.",
            ephemeral=True
        )


# ============================================================
# NOW PLAYING EMBED
# ============================================================

async def send_now_playing(
    player: MusicPlayer
):

    if not player.text_channel:
        return

    if not player.current:
        return

    song = player.current

    embed = discord.Embed(
        title="🎵 NOW PLAYING",
        description=(
            f"### {song.title}\n\n"
            f"⏱️ `{song.duration_text}`\n"
            f"🔁 `{'ON' if player.repeat else 'OFF'}`\n\n"
            f"🎧 طلبها <@{song.requester_id}>"
        ),
        color=discord.Color.blurple()
    )

    if song.thumbnail:

        embed.set_thumbnail(
            url=song.thumbnail
        )

    embed.set_footer(
        text="Music System • Premium Player"
    )

    try:

        await player.text_channel.send(
            embed=embed,
            view=PlayerView()
        )

    except Exception:

        logger.exception(
            "Failed to send now playing"
        )


# ============================================================
# START NEXT
# ============================================================

async def start_next(guild_id: int):

    player = get_player(
        guild_id
    )

    async with player.lock:

        if not player.voice:
            return

        if player.voice.is_playing():
            return

        if player.repeat and player.current:

            song = player.current

        elif player.queue:

            song = player.queue.pop(0)

            player.current = song

        else:

            player.current = None

            return

        try:

            audio_url = await asyncio.to_thread(
                get_audio_source,
                song.url
            )

        except Exception:

            logger.exception(
                "Failed to obtain audio source"
            )

            player.current = None

            await start_next(
                guild_id
            )

            return

        ffmpeg_options = (
            "-reconnect 1 "
            "-reconnect_streamed 1 "
            "-reconnect_delay_max 5"
        )

        source = discord.FFmpegPCMAudio(
            audio_url,
            before_options=ffmpeg_options,
            options="-vn"
        )

        def after(error):

            if error:

                logger.error(
                    "Player error: %s",
                    error
                )

            asyncio.run_coroutine_threadsafe(
                song_finished(guild_id),
                bot.loop
            )

        player.voice.play(
            source,
            after=after
        )

        player.paused = False

        await send_now_playing(
            player
        )


# ============================================================
# SONG FINISHED
# ============================================================

async def song_finished(
    guild_id: int
):

    player = get_player(
        guild_id
    )

    await asyncio.sleep(0.5)

    if player.repeat:

        if player.voice:

            player.voice.stop()

        return

    player.current = None

    await start_next(
        guild_id
    )


# ============================================================
# /PLAY
# ============================================================

@bot.tree.command(
    name="play",
    description="ابحث عن أغنية وشغلها في الروم الصوتي"
)
@app_commands.describe(
    song="اسم الأغنية"
)
async def play(
    interaction: discord.Interaction,
    song: str
):

    voice_state = interaction.user.voice

    if not voice_state:

        await interaction.response.send_message(
            "❌ يجب أن تدخل Voice Channel أولاً.",
            ephemeral=True
        )

        return

    await interaction.response.defer()

    results = await asyncio.to_thread(
        youtube_search,
        song
    )

    if not results:

        await interaction.followup.send(
            "❌ لم أجد أي نتائج."
        )

        return

    embed = discord.Embed(

        title="🎵 Music Search",

        description=(
            f"نتائج البحث عن:\n"
            f"### `{song}`\n\n"
            "اختر الأغنية التي تريد تشغيلها:"
        ),

        color=discord.Color.blurple()
    )

    embed.set_footer(
        text="Music System • اختر من القائمة"
    )

    await interaction.followup.send(

        embed=embed,

        view=SearchView(
            interaction.user.id,
            results
        )
    )


# ============================================================
# /QUEUE
# ============================================================

@bot.tree.command(
    name="queue",
    description="عرض قائمة الأغاني"
)
async def queue(
    interaction: discord.Interaction
):

    player = get_player(
        interaction.guild.id
    )

    if not player.current and not player.queue:

        await interaction.response.send_message(
            "📭 قائمة التشغيل فارغة.",
            ephemeral=True
        )

        return

    lines = []

    if player.current:

        lines.append(
            f"🎵 **الآن:** {player.current.title}"
        )

    for i, song in enumerate(
        player.queue[:15],
        start=1
    ):

        lines.append(
            f"`{i}.` {song.title}"
        )

    embed = discord.Embed(
        title="📋 Music Queue",
        description="\n".join(lines),
        color=discord.Color.blurple()
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# /LEAVE
# ============================================================

@bot.tree.command(
    name="leave",
    description="إخراج البوت من الروم الصوتي"
)
async def leave(
    interaction: discord.Interaction
):

    player = get_player(
        interaction.guild.id
    )

    player.queue.clear()

    player.current = None

    player.repeat = False

    if player.voice:

        await player.voice.disconnect()

        player.voice = None

    await interaction.response.send_message(
        "👋 خرجت من الروم الصوتي."
    )


# ============================================================
# /SKIP
# ============================================================

@bot.tree.command(
    name="skip",
    description="تخطي الأغنية الحالية"
)
async def skip(
    interaction: discord.Interaction
):

    player = get_player(
        interaction.guild.id
    )

    if not player.voice:

        await interaction.response.send_message(
            "❌ البوت غير متصل.",
            ephemeral=True
        )

        return

    player.repeat = False

    player.voice.stop()

    await interaction.response.send_message(
        "⏭️ تم تخطي الأغنية."
    )


# ============================================================
# /PAUSE
# ============================================================

@bot.tree.command(
    name="pause",
    description="إيقاف الأغنية مؤقتًا"
)
async def pause(
    interaction: discord.Interaction
):

    player = get_player(
        interaction.guild.id
    )

    if player.voice and player.voice.is_playing():

        player.voice.pause()

        await interaction.response.send_message(
            "⏸️ تم إيقاف الأغنية مؤقتًا."
        )

    else:

        await interaction.response.send_message(
            "❌ لا توجد أغنية تعمل.",
            ephemeral=True
        )


# ============================================================
# /RESUME
# ============================================================

@bot.tree.command(
    name="resume",
    description="استئناف الأغنية"
)
async def resume(
    interaction: discord.Interaction
):

    player = get_player(
        interaction.guild.id
    )

    if player.voice and player.voice.is_paused():

        player.voice.resume()

        await interaction.response.send_message(
            "▶️ تم استئناف الأغنية."
        )

    else:

        await interaction.response.send_message(
            "❌ الأغنية ليست متوقفة مؤقتًا.",
            ephemeral=True
        )


# ============================================================
# READY
# ============================================================

@bot.event
async def on_ready():

    logger.info(
        "================================"
    )

    logger.info(
        "🎵 Music Bot ONLINE"
    )

    logger.info(
        "👤 Logged in as %s",
        bot.user
    )

    logger.info(
        "🆔 Bot ID: %s",
        bot.user.id
    )

    logger.info(
        "🎧 Voice System: ON"
    )

    logger.info(
        "🔎 YouTube Search: ON"
    )

    logger.info(
        "================================"
    )


# ============================================================
# RUN
# ============================================================

if not TOKEN:

    raise RuntimeError(
        "DISCORD_TOKEN غير موجود في Environment Variables"
    )


bot.run(TOKEN)
