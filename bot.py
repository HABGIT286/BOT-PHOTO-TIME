import asyncio
import logging
import os
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
OWNER_ID = os.getenv("OWNER_ID")

MAX_SEARCH_RESULTS = 8


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("MusicBot")


# ============================================================
# INTENTS
# ============================================================

intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True


# ============================================================
# YOUTUBE OPTIONS
# ============================================================

YTDLP_SEARCH_OPTIONS = {
    "quiet": True,
    "no_warnings": True,
    "extract_flat": True,
    "skip_download": True,
    "noplaylist": True,
    "socket_timeout": 20,
    "retries": 3,
}

YTDLP_STREAM_OPTIONS = {
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "skip_download": True,
    "socket_timeout": 30,
    "retries": 3,
    "fragment_retries": 3,
}


# ============================================================
# AUDIO OPTIONS
# ============================================================

FFMPEG_OPTIONS = {
    "before_options": (
        "-reconnect 1 "
        "-reconnect_streamed 1 "
        "-reconnect_delay_max 5"
    ),
    "options": (
        "-vn "
        "-loglevel warning"
    ),
}


# ============================================================
# SONG
# ============================================================

@dataclass
class Song:
    title: str
    url: str
    webpage_url: str
    duration: Optional[int] = None
    thumbnail: Optional[str] = None
    channel: Optional[str] = None


# ============================================================
# MUSIC STATE
# ============================================================

@dataclass
class MusicState:

    guild_id: int

    queue: list[Song] = field(default_factory=list)

    current: Optional[Song] = None

    previous: list[Song] = field(default_factory=list)

    repeat: bool = False

    paused: bool = False

    text_channel_id: Optional[int] = None

    now_playing_message: Optional[discord.Message] = None

    player_lock: asyncio.Lock = field(
        default_factory=asyncio.Lock
    )


music_states: dict[int, MusicState] = {}


def get_state(guild_id: int) -> MusicState:

    if guild_id not in music_states:
        music_states[guild_id] = MusicState(
            guild_id=guild_id
        )

    return music_states[guild_id]


# ============================================================
# BOT
# ============================================================

class MusicBot(commands.Bot):

    def __init__(self):

        super().__init__(
            command_prefix="!",
            intents=intents,
        )

        self.synced = False

    async def setup_hook(self):

        try:

            synced = await self.tree.sync()

            logger.info(
                "Synced %s slash commands.",
                len(synced)
            )

            self.synced = True

        except Exception:

            logger.exception(
                "Failed to sync slash commands."
            )


bot = MusicBot()


# ============================================================
# SEARCH YOUTUBE
# ============================================================

def search_youtube(
    query: str,
    limit: int = MAX_SEARCH_RESULTS
):

    search = f"ytsearch{limit}:{query}"

    try:

        with yt_dlp.YoutubeDL(
            YTDLP_SEARCH_OPTIONS
        ) as ydl:

            data = ydl.extract_info(
                search,
                download=False
            )

        results = []

        for item in data.get(
            "entries",
            []
        ):

            if not item:
                continue

            video_id = item.get("id")

            if not video_id:
                continue

            webpage_url = (
                item.get("webpage_url")
                or
                f"https://www.youtube.com/watch?v={video_id}"
            )

            results.append(
                Song(
                    title=item.get(
                        "title",
                        "Unknown"
                    ),
                    url=webpage_url,
                    webpage_url=webpage_url,
                    duration=item.get(
                        "duration"
                    ),
                    thumbnail=item.get(
                        "thumbnail"
                    ),
                    channel=(
                        item.get("channel")
                        or
                        item.get("uploader")
                        or
                        "Unknown"
                    ),
                )
            )

        return results

    except Exception:

        logger.exception(
            "YouTube search failed."
        )

        return []


# ============================================================
# EXTRACT DIRECT AUDIO URL
# ============================================================

def extract_audio_url(
    webpage_url: str
):

    try:

        with yt_dlp.YoutubeDL(
            YTDLP_STREAM_OPTIONS
        ) as ydl:

            info = ydl.extract_info(
                webpage_url,
                download=False
            )

        if not info:
            return None

        direct_url = info.get(
            "url"
        )

        if direct_url:
            return direct_url

        formats = info.get(
            "formats",
            []
        )

        audio_formats = [
            f
            for f in formats
            if f.get("acodec") != "none"
            and f.get("url")
        ]

        if not audio_formats:
            return None

        audio_formats.sort(
            key=lambda f: (
                f.get("abr") or 0
            ),
            reverse=True
        )

        return audio_formats[0]["url"]

    except Exception:

        logger.exception(
            "Audio extraction failed."
        )

        return None


# ============================================================
# FORMAT DURATION
# ============================================================

def format_duration(
    seconds: Optional[int]
):

    if not seconds:
        return "غير معروف"

    seconds = int(seconds)

    minutes = seconds // 60
    secs = seconds % 60

    return f"{minutes}:{secs:02d}"


# ============================================================
# VOICE CONNECTION
# ============================================================

async def connect_to_user_channel(
    interaction: discord.Interaction
):

    if not interaction.guild:

        return None, (
            "❌ هذا الأمر يعمل داخل السيرفر فقط."
        )

    member = interaction.user

    if not isinstance(
        member,
        discord.Member
    ):

        return None, (
            "❌ لم أستطع معرفة حالتك الصوتية."
        )

    voice_state = member.voice

    if not voice_state:

        return None, (
            "❌ **أنت غير موجود في روم صوتي.**\n\n"
            "ادخل Voice Channel أولًا ثم استخدم `/play`."
        )

    channel = voice_state.channel

    if channel is None:

        return None, (
            "❌ لم أستطع تحديد الروم الصوتي."
        )

    # --------------------------------------------------------
    # Check bot permissions
    # --------------------------------------------------------

    permissions = channel.permissions_for(
        interaction.guild.me
    )

    if not permissions.connect:

        return None, (
            "❌ **البوت لا يملك صلاحية Connect.**\n\n"
            f"الروم: **{channel.name}**\n\n"
            "امنح البوت:\n"
            "• Connect\n"
            "• Speak"
        )

    if not permissions.speak:

        return None, (
            "❌ **البوت لا يملك صلاحية Speak.**\n\n"
            f"الروم: **{channel.name}**"
        )

    # --------------------------------------------------------
    # Existing voice client
    # --------------------------------------------------------

    voice_client = interaction.guild.voice_client

    try:

        if voice_client:

            if voice_client.channel.id != channel.id:

                logger.info(
                    "Moving bot to %s",
                    channel.name
                )

                await voice_client.move_to(
                    channel
                )

            return voice_client, None

        logger.info(
            "Connecting to voice channel: %s",
            channel.name
        )

        voice_client = await channel.connect(
            self_deaf=True,
            self_mute=False,
            reconnect=True
        )

        return voice_client, None

    except discord.Forbidden:

        return None, (
            "❌ **Discord رفض دخول البوت للروم.**\n\n"
            "تأكد من صلاحيات:\n"
            "• Connect\n"
            "• Speak"
        )

    except discord.ClientException as e:

        logger.exception(
            "Discord client voice error"
        )

        return None, (
            "❌ حدث خطأ في اتصال الصوت.\n\n"
            f"`{str(e)[:300]}`"
        )

    except asyncio.TimeoutError:

        return None, (
            "❌ انتهت مهلة الاتصال بالروم الصوتي.\n\n"
            "حاول مرة أخرى."
        )

    except Exception as e:

        logger.exception(
            "Voice connection error"
        )

        return None, (
            "❌ **لم أستطع الدخول إلى الروم الصوتي.**\n\n"
            f"الخطأ: `{str(e)[:400]}`"
        )


# ============================================================
# SEARCH VIEW
# ============================================================

class SearchView(
    discord.ui.View
):

    def __init__(
        self,
        interaction: discord.Interaction,
        songs: list[Song]
    ):

        super().__init__(
            timeout=120
        )

        self.owner_id = interaction.user.id

        self.songs = songs

        for index, song in enumerate(
            songs
        ):

            button = discord.ui.Button(
                label=(
                    f"{index + 1}. "
                    f"{song.title[:75]}"
                ),
                style=discord.ButtonStyle.secondary,
                emoji="🎵",
                custom_id=(
                    f"search_song_{index}"
                ),
                row=index // 2
            )

            async def callback(
                button_interaction:
                discord.Interaction,
                index=index
            ):

                await self.select_song(
                    button_interaction,
                    index
                )

            button.callback = callback

            self.add_item(
                button
            )

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ):

        if interaction.user.id != self.owner_id:

            await interaction.response.send_message(
                "❌ هذه النتائج تخص الشخص الذي بدأ البحث.",
                ephemeral=True
            )

            return False

        return True

    async def select_song(
        self,
        interaction: discord.Interaction,
        index: int
    ):

        if index >= len(self.songs):

            await interaction.response.send_message(
                "❌ الأغنية غير موجودة.",
                ephemeral=True
            )

            return

        song = self.songs[index]

        await interaction.response.edit_message(
            content=(
                "⏳ **جاري تجهيز الأغنية...**\n\n"
                f"🎵 **{song.title}**\n"
                f"📺 {song.channel or 'Unknown'}\n"
                f"⏱️ {format_duration(song.duration)}"
            ),
            embed=None,
            view=None
        )

        state = get_state(
            interaction.guild.id
        )

        state.text_channel_id = (
            interaction.channel.id
        )

        voice_client, error = (
            await connect_to_user_channel(
                interaction
            )
        )

        if error:

            await interaction.followup.send(
                error
            )

            return

        state.queue.append(
            song
        )

        # إذا لا توجد أغنية تعمل
        if not voice_client.is_playing() and not voice_client.is_paused():

            await play_next(
                interaction.guild
            )

            return

        await interaction.followup.send(
            f"✅ تمت إضافة **{song.title}** إلى قائمة الانتظار.\n"
            f"📋 المركز: **{len(state.queue)}**"
        )


# ============================================================
# MUSIC CONTROL VIEW
# ============================================================

class MusicControlView(
    discord.ui.View
):

    def __init__(
        self,
        guild_id: int
    ):

        super().__init__(
            timeout=None
        )

        self.guild_id = guild_id

    def get_voice(
        self,
        interaction
    ):

        return interaction.guild.voice_client

    # --------------------------------------------------------
    # Pause / Resume
    # --------------------------------------------------------

    @discord.ui.button(
        label="إيقاف",
        emoji="⏯️",
        style=discord.ButtonStyle.primary,
        row=0
    )
    async def pause_resume(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        voice = self.get_voice(
            interaction
        )

        if not voice:

            await interaction.response.send_message(
                "❌ البوت غير متصل بالروم الصوتي.",
                ephemeral=True
            )

            return

        if voice.is_paused():

            voice.resume()

            button.label = "إيقاف"

            await interaction.response.edit_message(
                view=self
            )

            await interaction.followup.send(
                "▶️ تم استئناف الأغنية.",
                ephemeral=True
            )

            return

        if voice.is_playing():

            voice.pause()

            button.label = "استئناف"

            await interaction.response.edit_message(
                view=self
            )

            await interaction.followup.send(
                "⏸️ تم إيقاف الأغنية مؤقتًا.",
                ephemeral=True
            )

            return

        await interaction.response.send_message(
            "❌ لا توجد أغنية تعمل حاليًا.",
            ephemeral=True
        )

    # --------------------------------------------------------
    # Skip
    # --------------------------------------------------------

    @discord.ui.button(
        label="تخطي",
        emoji="⏭️",
        style=discord.ButtonStyle.secondary,
        row=0
    )
    async def skip(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        voice = self.get_voice(
            interaction
        )

        if not voice or not voice.is_playing():

            await interaction.response.send_message(
                "❌ لا توجد أغنية تعمل.",
                ephemeral=True
            )

            return

        await interaction.response.defer()

        voice.stop()

        await interaction.followup.send(
            "⏭️ تم تخطي الأغنية.",
            ephemeral=True
        )

    # --------------------------------------------------------
    # Previous
    # --------------------------------------------------------

    @discord.ui.button(
        label="السابق",
        emoji="⏮️",
        style=discord.ButtonStyle.secondary,
        row=0
    )
    async def previous(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        state = get_state(
            interaction.guild.id
        )

        if not state.previous:

            await interaction.response.send_message(
                "❌ لا توجد أغنية سابقة.",
                ephemeral=True
            )

            return

        voice = self.get_voice(
            interaction
        )

        if not voice:

            await interaction.response.send_message(
                "❌ البوت غير متصل.",
                ephemeral=True
            )

            return

        previous_song = (
            state.previous.pop()
        )

        if state.current:

            state.queue.insert(
                0,
                state.current
            )

        state.current = previous_song

        await interaction.response.defer()

        if voice.is_playing() or voice.is_paused():

            voice.stop()

        await play_song(
            interaction.guild,
            previous_song
        )

    # --------------------------------------------------------
    # Repeat
    # --------------------------------------------------------

    @discord.ui.button(
        label="تكرار",
        emoji="🔁",
        style=discord.ButtonStyle.secondary,
        row=1
    )
    async def repeat(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        state = get_state(
            interaction.guild.id
        )

        state.repeat = not state.repeat

        if state.repeat:

            button.label = "التكرار: ON"

            await interaction.response.edit_message(
                view=self
            )

            await interaction.followup.send(
                "🔁 تم تفعيل تكرار الأغنية الحالية.",
                ephemeral=True
            )

        else:

            button.label = "التكرار"

            await interaction.response.edit_message(
                view=self
            )

            await interaction.followup.send(
                "🔁 تم إيقاف التكرار.",
                ephemeral=True
            )

    # --------------------------------------------------------
    # Stop
    # --------------------------------------------------------

    @discord.ui.button(
        label="إيقاف",
        emoji="⏹️",
        style=discord.ButtonStyle.danger,
        row=1
    )
    async def stop(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        voice = self.get_voice(
            interaction
        )

        if voice:

            if voice.is_playing() or voice.is_paused():

                voice.stop()

            await voice.disconnect(
                force=True
            )

        state = get_state(
            interaction.guild.id
        )

        state.queue.clear()
        state.previous.clear()
        state.current = None
        state.repeat = False
        state.paused = False

        await interaction.response.send_message(
            "⏹️ تم إيقاف المشغل ومغادرة الروم الصوتي.",
            ephemeral=True
        )


# ============================================================
# NOW PLAYING EMBED
# ============================================================

def create_now_playing_embed(
    song: Song,
    state: MusicState
):

    embed = discord.Embed(
        title="🎵 الآن يتم التشغيل",
        description=(
            f"**{song.title}**"
        ),
        color=discord.Color.blurple()
    )

    if song.thumbnail:

        embed.set_thumbnail(
            url=song.thumbnail
        )

    embed.add_field(
        name="📺 القناة",
        value=(
            song.channel
            or
            "Unknown"
        ),
        inline=True
    )

    embed.add_field(
        name="⏱️ المدة",
        value=format_duration(
            song.duration
        ),
        inline=True
    )

    embed.add_field(
        name="🔁 التكرار",
        value=(
            "مفعل"
            if state.repeat
            else "متوقف"
        ),
        inline=True
    )

    embed.add_field(
        name="📋 القادمة",
        value=str(
            len(state.queue)
        ),
        inline=True
    )

    embed.set_footer(
        text="Music Bot • استخدم الأزرار للتحكم"
    )

    return embed


# ============================================================
# PLAY SONG
# ============================================================

async def play_song(
    guild: discord.Guild,
    song: Song
):

    voice = guild.voice_client

    if not voice:

        logger.error(
            "play_song called without voice client."
        )

        return False

    state = get_state(
        guild.id
    )

    logger.info(
        "Preparing audio: %s",
        song.title
    )

    direct_url = await asyncio.to_thread(
        extract_audio_url,
        song.webpage_url
    )

    if not direct_url:

        logger.error(
            "Could not extract direct audio URL."
        )

        channel = bot.get_channel(
            state.text_channel_id
        )

        if channel:

            await channel.send(
                "❌ لم أستطع الحصول على رابط الصوت لهذه الأغنية."
            )

        return False

    state.current = song
    state.paused = False

    try:

        source = discord.FFmpegPCMAudio(
            direct_url,
            **FFMPEG_OPTIONS
        )

        # ----------------------------------------------------
        # Callback after playback
        # ----------------------------------------------------

        def after_play(error):

            if error:

                logger.error(
                    "Player error: %s",
                    error
                )

            asyncio.run_coroutine_threadsafe(
                playback_finished(
                    guild
                ),
                bot.loop
            )

        voice.play(
            source,
            after=after_play
        )

        logger.info(
            "Now playing: %s",
            song.title
        )

        # ----------------------------------------------------
        # Send now playing
        # ----------------------------------------------------

        channel = bot.get_channel(
            state.text_channel_id
        )

        if channel:

            try:

                embed = create_now_playing_embed(
                    song,
                    state
                )

                view = MusicControlView(
                    guild.id
                )

                message = await channel.send(
                    embed=embed,
                    view=view
                )

                state.now_playing_message = (
                    message
                )

            except Exception:

                logger.exception(
                    "Failed to send player message."
                )

        return True

    except Exception:

        logger.exception(
            "FFmpeg playback failed."
        )

        return False


# ============================================================
# PLAY NEXT
# ============================================================

async def play_next(
    guild: discord.Guild
):

    state = get_state(
        guild.id
    )

    voice = guild.voice_client

    if not voice:

        return

    if not state.queue:

        state.current = None

        return

    next_song = state.queue.pop(
        0
    )

    if state.current:

        state.previous.append(
            state.current
        )

        # Keep only last 20
        if len(state.previous) > 20:

            state.previous = (
                state.previous[-20:]
            )

    await play_song(
        guild,
        next_song
    )


# ============================================================
# PLAYBACK FINISHED
# ============================================================

async def playback_finished(
    guild: discord.Guild
):

    await asyncio.sleep(
        0.5
    )

    state = get_state(
        guild.id
    )

    voice = guild.voice_client

    if not voice:

        return

    # --------------------------------------------------------
    # Repeat current song
    # --------------------------------------------------------

    if state.repeat and state.current:

        song = state.current

        await play_song(
            guild,
            song
        )

        return

    # --------------------------------------------------------
    # Next
    # --------------------------------------------------------

    await play_next(
        guild
    )


# ============================================================
# /PLAY
# ============================================================

@bot.tree.command(
    name="play",
    description="ابحث عن أغنية وشغلها في الروم الصوتي"
)
@app_commands.describe(
    query="اسم الأغنية أو الفنان"
)
async def play_command(
    interaction: discord.Interaction,
    query: str
):

    await interaction.response.defer()

    if not interaction.guild:

        await interaction.followup.send(
            "❌ استخدم الأمر داخل سيرفر."
        )

        return

    # --------------------------------------------------------
    # Check voice first
    # --------------------------------------------------------

    member = interaction.user

    if not isinstance(
        member,
        discord.Member
    ):

        await interaction.followup.send(
            "❌ لم أستطع معرفة حالتك الصوتية."
        )

        return

    if not member.voice:

        await interaction.followup.send(
            "❌ ادخل روم صوتي أولًا ثم استخدم `/play`."
        )

        return

    # --------------------------------------------------------
    # Search
    # --------------------------------------------------------

    await interaction.followup.send(
        "🔎 **جاري البحث عن الأغاني...**"
    )

    search_message = (
        await interaction.channel.fetch_message(
            interaction.channel.last_message_id
        )
        if interaction.channel
        else None
    )

    songs = await asyncio.to_thread(
        search_youtube,
        query,
        MAX_SEARCH_RESULTS
    )

    if not songs:

        await interaction.followup.send(
            "❌ لم أجد نتائج لهذه الأغنية."
        )

        return

    # --------------------------------------------------------
    # Results embed
    # --------------------------------------------------------

    embed = discord.Embed(
        title="🎵 نتائج البحث",
        description=(
            f"نتائج البحث عن:\n"
            f"**{query}**\n\n"
            "اختر الأغنية التي تريد تشغيلها:"
        ),
        color=discord.Color.blurple()
    )

    for index, song in enumerate(
        songs,
        start=1
    ):

        embed.add_field(
            name=f"🎵 {index}. {song.title[:80]}",
            value=(
                f"📺 {song.channel or 'Unknown'}"
                f" • "
                f"⏱️ {format_duration(song.duration)}"
            ),
            inline=False
        )

    view = SearchView(
        interaction,
        songs
    )

    await interaction.followup.send(
        embed=embed,
        view=view
    )


# ============================================================
# /SKIP
# ============================================================

@bot.tree.command(
    name="skip",
    description="تخطي الأغنية الحالية"
)
async def skip_command(
    interaction: discord.Interaction
):

    await interaction.response.defer(
        ephemeral=True
    )

    if not interaction.guild:

        await interaction.followup.send(
            "❌ استخدم الأمر داخل السيرفر."
        )

        return

    voice = interaction.guild.voice_client

    if not voice or not voice.is_playing():

        await interaction.followup.send(
            "❌ لا توجد أغنية تعمل."
        )

        return

    voice.stop()

    await interaction.followup.send(
        "⏭️ تم تخطي الأغنية."
    )


# ============================================================
# /PAUSE
# ============================================================

@bot.tree.command(
    name="pause",
    description="إيقاف الأغنية مؤقتًا"
)
async def pause_command(
    interaction: discord.Interaction
):

    voice = interaction.guild.voice_client

    if not voice or not voice.is_playing():

        await interaction.response.send_message(
            "❌ لا توجد أغنية تعمل.",
            ephemeral=True
        )

        return

    voice.pause()

    await interaction.response.send_message(
        "⏸️ تم إيقاف الأغنية مؤقتًا.",
        ephemeral=True
    )


# ============================================================
# /RESUME
# ============================================================

@bot.tree.command(
    name="resume",
    description="استئناف الأغنية"
)
async def resume_command(
    interaction: discord.Interaction
):

    voice = interaction.guild.voice_client

    if not voice or not voice.is_paused():

        await interaction.response.send_message(
            "❌ الأغنية ليست متوقفة.",
            ephemeral=True
        )

        return

    voice.resume()

    await interaction.response.send_message(
        "▶️ تم استئناف الأغنية.",
        ephemeral=True
    )


# ============================================================
# /STOP
# ============================================================

@bot.tree.command(
    name="stop",
    description="إيقاف المشغل ومغادرة الروم"
)
async def stop_command(
    interaction: discord.Interaction
):

    await interaction.response.defer(
        ephemeral=True
    )

    if interaction.guild:

        voice = interaction.guild.voice_client

        if voice:

            if voice.is_playing() or voice.is_paused():

                voice.stop()

            await voice.disconnect(
                force=True
            )

        state = get_state(
            interaction.guild.id
        )

        state.queue.clear()
        state.previous.clear()
        state.current = None
        state.repeat = False

    await interaction.followup.send(
        "⏹️ تم إيقاف المشغل ومغادرة الروم."
    )


# ============================================================
# /QUEUE
# ============================================================

@bot.tree.command(
    name="queue",
    description="عرض قائمة الأغاني القادمة"
)
async def queue_command(
    interaction: discord.Interaction
):

    if not interaction.guild:

        await interaction.response.send_message(
            "❌ استخدم الأمر داخل السيرفر.",
            ephemeral=True
        )

        return

    state = get_state(
        interaction.guild.id
    )

    if not state.queue:

        await interaction.response.send_message(
            "📋 قائمة الانتظار فارغة.",
            ephemeral=True
        )

        return

    description = ""

    for index, song in enumerate(
        state.queue[:10],
        start=1
    ):

        description += (
            f"**{index}.** "
            f"{song.title[:70]}\n"
        )

    if len(state.queue) > 10:

        description += (
            f"\n... و {len(state.queue) - 10} أغاني أخرى."
        )

    embed = discord.Embed(
        title="📋 قائمة الانتظار",
        description=description,
        color=discord.Color.blurple()
    )

    await interaction.response.send_message(
        embed=embed
    )


# ============================================================
# /NOWPLAYING
# ============================================================

@bot.tree.command(
    name="nowplaying",
    description="عرض الأغنية الحالية"
)
async def nowplaying_command(
    interaction: discord.Interaction
):

    if not interaction.guild:

        await interaction.response.send_message(
            "❌ استخدم الأمر داخل السيرفر.",
            ephemeral=True
        )

        return

    state = get_state(
        interaction.guild.id
    )

    if not state.current:

        await interaction.response.send_message(
            "❌ لا توجد أغنية تعمل حاليًا.",
            ephemeral=True
        )

        return

    embed = create_now_playing_embed(
        state.current,
        state
    )

    await interaction.response.send_message(
        embed=embed,
        view=MusicControlView(
            interaction.guild.id
        )
    )


# ============================================================
# /LEAVE
# ============================================================

@bot.tree.command(
    name="leave",
    description="إخراج البوت من الروم الصوتي"
)
async def leave_command(
    interaction: discord.Interaction
):

    if not interaction.guild:

        await interaction.response.send_message(
            "❌ استخدم الأمر داخل السيرفر.",
            ephemeral=True
        )

        return

    voice = interaction.guild.voice_client

    if not voice:

        await interaction.response.send_message(
            "❌ البوت ليس داخل روم صوتي.",
            ephemeral=True
        )

        return

    await voice.disconnect(
        force=True
    )

    state = get_state(
        interaction.guild.id
    )

    state.queue.clear()
    state.current = None

    await interaction.response.send_message(
        "👋 غادرت الروم الصوتي."
    )


# ============================================================
# BOT READY
# ============================================================

@bot.event
async def on_ready():

    logger.info(
        "================================"
    )

    logger.info(
        "🎵 Discord Music Bot"
    )

    logger.info(
        "================================"
    )

    logger.info(
        "✅ Logged in as %s",
        bot.user
    )

    logger.info(
        "🆔 Bot ID: %s",
        bot.user.id
    )

    logger.info(
        "🎵 /play: ON"
    )

    logger.info(
        "🔎 YouTube Search: ON"
    )

    logger.info(
        "🎧 Voice Playback: ON"
    )

    logger.info(
        "⏯️ Pause / Resume: ON"
    )

    logger.info(
        "⏭️ Skip: ON"
    )

    logger.info(
        "⏮️ Previous: ON"
    )

    logger.info(
        "🔁 Repeat: ON"
    )

    logger.info(
        "📋 Queue: ON"
    )

    logger.info(
        "================================"
    )


# ============================================================
# ERROR
# ============================================================

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):

    logger.exception(
        "Slash command error",
        exc_info=error
    )

    message = (
        "❌ حدث خطأ أثناء تنفيذ الأمر."
    )

    try:

        if interaction.response.is_done():

            await interaction.followup.send(
                message,
                ephemeral=True
            )

        else:

            await interaction.response.send_message(
                message,
                ephemeral=True
            )

    except Exception:

        pass


# ============================================================
# START
# ============================================================

def main():

    if not TOKEN:

        print(
            "❌ DISCORD_TOKEN غير موجود."
        )

        print(
            "ضعه في GitHub Actions Secrets."
        )

        return

    print(
        "================================"
    )

    print(
        "🎵 Discord Music Bot"
    )

    print(
        "================================"
    )

    print(
        "🔎 YouTube Search: ON"
    )

    print(
        "🎧 Voice Playback: ON"
    )

    print(
        "🎵 /play: ON"
    )

    print(
        "⏯️ Pause / Resume: ON"
    )

    print(
        "⏭️ Skip: ON"
    )

    print(
        "⏮️ Previous: ON"
    )

    print(
        "🔁 Repeat: ON"
    )

    print(
        "📋 Queue: ON"
    )

    print(
        "================================"
    )

    bot.run(
        TOKEN
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
