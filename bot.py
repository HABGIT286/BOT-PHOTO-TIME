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

    async def setup_hook(self):

        try:

            synced = await self.tree.sync()

            logger.info(
                "Synced %s slash commands.",
                len(synced)
            )

        except Exception:

            logger.exception(
                "Failed to sync slash commands."
            )


bot = MusicBot()


# ============================================================
# YOUTUBE SEARCH
# ============================================================

def search_youtube(
    query: str,
    limit: int = MAX_SEARCH_RESULTS
):

    options = {

        "quiet": True,
        "no_warnings": True,

        "extract_flat": True,

        "skip_download": True,

        "noplaylist": True,

        "socket_timeout": 30,

        "retries": 3,

        "fragment_retries": 3,

    }

    search_query = f"ytsearch{limit}:{query}"

    try:

        with yt_dlp.YoutubeDL(options) as ydl:

            data = ydl.extract_info(
                search_query,
                download=False
            )

        results = []

        for item in data.get("entries", []):

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
                    duration=item.get("duration"),
                    thumbnail=item.get("thumbnail"),
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
# EXTRACT AUDIO STREAM
# ============================================================

def extract_audio_stream(
    webpage_url: str
):

    methods = [

        # الطريقة الأولى
        {
            "format": "bestaudio/best",
            "extractor_args": {
                "youtube": {
                    "player_client": [
                        "android",
                        "web"
                    ]
                }
            }
        },

        # الطريقة الثانية
        {
            "format": "ba/b",
            "extractor_args": {
                "youtube": {
                    "player_client": [
                        "web"
                    ]
                }
            }
        },

        # الطريقة الثالثة
        {
            "format": "best",
            "extractor_args": {
                "youtube": {
                    "player_client": [
                        "android"
                    ]
                }
            }
        },

        # الطريقة الرابعة
        {
            "format": "bestaudio",
            "extractor_args": {
                "youtube": {
                    "player_client": [
                        "ios"
                    ]
                }
            }
        },
    ]

    for number, method in enumerate(
        methods,
        start=1
    ):

        try:

            logger.info(
                "Trying YouTube audio method %s/%s",
                number,
                len(methods)
            )

            options = {

                "quiet": True,

                "no_warnings": True,

                "noplaylist": True,

                "skip_download": True,

                "socket_timeout": 30,

                "retries": 3,

                "fragment_retries": 3,

                "nocheckcertificate": True,

            }

            options.update(method)

            with yt_dlp.YoutubeDL(
                options
            ) as ydl:

                info = ydl.extract_info(
                    webpage_url,
                    download=False
                )

            if not info:

                continue

            # ------------------------------------------------
            # Direct URL
            # ------------------------------------------------

            direct_url = info.get("url")

            if direct_url:

                return {
                    "url": direct_url,
                    "headers": info.get(
                        "http_headers",
                        {}
                    )
                }

            # ------------------------------------------------
            # Formats
            # ------------------------------------------------

            formats = info.get(
                "formats",
                []
            )

            audio_formats = []

            for fmt in formats:

                if not fmt.get("url"):
                    continue

                if (
                    fmt.get("acodec")
                    and
                    fmt.get("acodec") != "none"
                ):

                    audio_formats.append(fmt)

            if not audio_formats:

                continue

            audio_formats.sort(
                key=lambda f: (
                    f.get("abr") or 0,
                    f.get("asr") or 0
                ),
                reverse=True
            )

            best = audio_formats[0]

            return {
                "url": best["url"],
                "headers": best.get(
                    "http_headers",
                    {}
                )
            }

        except Exception as e:

            logger.warning(
                "Audio method %s failed: %s",
                number,
                str(e)
            )

            continue

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
# CONNECT TO USER VOICE CHANNEL
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

    if not member.voice:

        return None, (
            "❌ **أنت غير موجود في روم صوتي.**\n\n"
            "ادخل الروم الصوتي أولًا."
        )

    channel = member.voice.channel

    if channel is None:

        return None, (
            "❌ لم أستطع تحديد الروم الصوتي."
        )

    # ========================================================
    # BOT MEMBER
    # ========================================================

    bot_member = interaction.guild.me

    if bot_member is None:

        try:

            bot_member = await interaction.guild.fetch_member(
                bot.user.id
            )

        except Exception:

            return None, (
                "❌ لم أستطع تحديد عضو البوت داخل السيرفر."
            )

    # ========================================================
    # PERMISSIONS
    # ========================================================

    permissions = channel.permissions_for(
        bot_member
    )

    if not permissions.connect:

        return None, (
            "❌ **البوت لا يملك Connect.**\n\n"
            f"الروم: **{channel.name}**"
        )

    if not permissions.speak:

        return None, (
            "❌ **البوت لا يملك Speak.**\n\n"
            f"الروم: **{channel.name}**"
        )

    # ========================================================
    # EXISTING CONNECTION
    # ========================================================

    voice = interaction.guild.voice_client

    try:

        if voice:

            if voice.channel.id != channel.id:

                logger.info(
                    "Moving bot to: %s",
                    channel.name
                )

                await voice.move_to(
                    channel
                )

            return voice, None

        # ====================================================
        # CONNECT
        # ====================================================

        logger.info(
            "Connecting to voice channel: %s",
            channel.name
        )

        voice = await channel.connect(
            timeout=30,
            reconnect=True,
            self_deaf=True,
            self_mute=False
        )

        logger.info(
            "Connected to voice channel: %s",
            channel.name
        )

        return voice, None

    except discord.Forbidden:

        return None, (
            "❌ Discord رفض دخول البوت للروم.\n\n"
            "تأكد من Connect و Speak."
        )

    except discord.ClientException as e:

        logger.exception(
            "Discord voice client error."
        )

        return None, (
            "❌ خطأ في اتصال الصوت:\n"
            f"`{str(e)[:400]}`"
        )

    except asyncio.TimeoutError:

        return None, (
            "❌ انتهت مهلة الاتصال بالروم الصوتي."
        )

    except Exception as e:

        logger.exception(
            "Voice connection error."
        )

        return None, (
            "❌ **لم أستطع الدخول إلى الروم الصوتي.**\n\n"
            f"`{str(e)[:400]}`"
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

            row = index // 2

            button = discord.ui.Button(
                label=(
                    f"{index + 1}. "
                    f"{song.title[:75]}"
                ),
                emoji="🎵",
                style=discord.ButtonStyle.secondary,
                row=row
            )

            async def callback(
                button_interaction:
                discord.Interaction,
                selected_index=index
            ):

                await self.select_song(
                    button_interaction,
                    selected_index
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

        if index < 0 or index >= len(
            self.songs
        ):

            await interaction.response.send_message(
                "❌ الأغنية غير موجودة.",
                ephemeral=True
            )

            return

        song = self.songs[index]

        # ====================================================
        # RESPOND IMMEDIATELY
        # ====================================================

        await interaction.response.edit_message(
            content=(
                "⚡ **جاري تشغيل الأغنية...**\n\n"
                f"🎵 **{song.title}**\n"
                f"📺 {song.channel or 'Unknown'}\n"
                f"⏱️ {format_duration(song.duration)}"
            ),
            embed=None,
            view=None
        )

        # ====================================================
        # STATE
        # ====================================================

        state = get_state(
            interaction.guild.id
        )

        state.text_channel_id = (
            interaction.channel.id
        )

        # ====================================================
        # CONNECT
        # ====================================================

        voice, error = (
            await connect_to_user_channel(
                interaction
            )
        )

        if error:

            await interaction.followup.send(
                error
            )

            return

        # ====================================================
        # QUEUE
        # ====================================================

        state.queue.append(
            song
        )

        # ====================================================
        # START IMMEDIATELY
        # ====================================================

        if (
            not voice.is_playing()
            and
            not voice.is_paused()
        ):

            await play_next(
                interaction.guild
            )

        else:

            await interaction.followup.send(
                f"✅ تمت إضافة **{song.title}** إلى قائمة الانتظار."
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

    # ========================================================
    # PAUSE / RESUME
    # ========================================================

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

        voice = interaction.guild.voice_client

        if not voice:

            await interaction.response.send_message(
                "❌ البوت غير متصل.",
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
            "❌ لا توجد أغنية تعمل.",
            ephemeral=True
        )

    # ========================================================
    # SKIP
    # ========================================================

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

        voice = interaction.guild.voice_client

        if not voice or not (
            voice.is_playing()
            or voice.is_paused()
        ):

            await interaction.response.send_message(
                "❌ لا توجد أغنية تعمل.",
                ephemeral=True
            )

            return

        await interaction.response.defer(
            ephemeral=True
        )

        voice.stop()

        await interaction.followup.send(
            "⏭️ تم تخطي الأغنية.",
            ephemeral=True
        )

    # ========================================================
    # PREVIOUS
    # ========================================================

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

        voice = interaction.guild.voice_client

        if not voice:

            await interaction.response.send_message(
                "❌ البوت غير متصل.",
                ephemeral=True
            )

            return

        previous_song = state.previous.pop()

        if state.current:

            state.queue.insert(
                0,
                state.current
            )

        state.current = previous_song

        await interaction.response.defer(
            ephemeral=True
        )

        if (
            voice.is_playing()
            or
            voice.is_paused()
        ):

            voice.stop()

        await interaction.followup.send(
            f"⏮️ الرجوع إلى **{previous_song.title}**",
            ephemeral=True
        )

        await play_song(
            interaction.guild,
            previous_song
        )

    # ========================================================
    # REPEAT
    # ========================================================

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
                "🔁 تم تفعيل التكرار.",
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

    # ========================================================
    # STOP
    # ========================================================

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

        voice = interaction.guild.voice_client

        if voice:

            if (
                voice.is_playing()
                or
                voice.is_paused()
            ):

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
            "⏹️ تم إيقاف المشغل ومغادرة الروم.",
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
        description=f"**{song.title}**",
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
            else
            "متوقف"
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
        text="Music Bot • تحكم بالموسيقى من الأزرار"
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
            "No voice connection."
        )

        return False

    state = get_state(
        guild.id
    )

    logger.info(
        "Preparing: %s",
        song.title
    )

    # ========================================================
    # GET STREAM
    # ========================================================

    stream = await asyncio.to_thread(
        extract_audio_stream,
        song.webpage_url
    )

    if not stream:

        logger.error(
            "Could not get audio stream."
        )

        channel = bot.get_channel(
            state.text_channel_id
        )

        if channel:

            await channel.send(
                "❌ لم أستطع الحصول على بث صوتي لهذه الأغنية."
            )

        return False

    direct_url = stream.get(
        "url"
    )

    if not direct_url:

        return False

    headers = stream.get(
        "headers",
        {}
    )

    # ========================================================
    # HTTP HEADERS
    # ========================================================

    header_string = ""

    for key, value in headers.items():

        if key.lower() == "cookie":

            continue

        header_string += (
            f"{key}: {value}\r\n"
        )

    # ========================================================
    # FFMPEG
    # ========================================================

    before_options = (
        "-reconnect 1 "
        "-reconnect_streamed 1 "
        "-reconnect_delay_max 5 "
        "-nostdin"
    )

    if header_string:

        before_options += (
            " -headers "
            f"\"{header_string}\""
        )

    ffmpeg_options = {

        "before_options":
            before_options,

        "options":
            "-vn -loglevel warning"
    }

    try:

        source = discord.FFmpegPCMAudio(
            direct_url,
            **ffmpeg_options
        )

        state.current = song

        state.paused = False

        # ====================================================
        # CALLBACK
        # ====================================================

        def after_play(error):

            if error:

                logger.error(
                    "Playback error: %s",
                    error
                )

            try:

                asyncio.run_coroutine_threadsafe(
                    playback_finished(guild),
                    bot.loop
                )

            except Exception:

                logger.exception(
                    "Failed playback callback."
                )

        # ====================================================
        # START
        # ====================================================

        voice.play(
            source,
            after=after_play
        )

        logger.info(
            "▶️ NOW PLAYING: %s",
            song.title
        )

        # ====================================================
        # PLAYER MESSAGE
        # ====================================================

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

                state.now_playing_message = message

            except Exception:

                logger.exception(
                    "Failed to send player message."
                )

        return True

    except Exception:

        logger.exception(
            "FFmpeg failed."
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

        if len(state.previous) > 20:

            state.previous = (
                state.previous[-20:]
            )

    success = await play_song(
        guild,
        next_song
    )

    if not success:

        await asyncio.sleep(
            1
        )

        await play_next(
            guild
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

    if state.repeat and state.current:

        current = state.current

        await play_song(
            guild,
            current
        )

        return

    await play_next(
        guild
    )


# ============================================================
# /PLAY
# ============================================================

@bot.tree.command(
    name="play",
    description="ابحث عن أغنية وشغلها"
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
            "❌ استخدم الأمر داخل السيرفر."
        )

        return

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
            "❌ ادخل روم صوتي أولًا."
        )

        return

    await interaction.followup.send(
        "🔎 **جاري البحث...**"
    )

    songs = await asyncio.to_thread(
        search_youtube,
        query,
        MAX_SEARCH_RESULTS
    )

    if not songs:

        await interaction.followup.send(
            "❌ لم أجد نتائج."
        )

        return

    embed = discord.Embed(
        title="🎵 نتائج البحث",
        description=(
            f"البحث عن:\n"
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
            name=(
                f"🎵 {index}. "
                f"{song.title[:80]}"
            ),
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
    description="تخطي الأغنية"
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

    if not voice or not (
        voice.is_playing()
        or voice.is_paused()
    ):

        await interaction.followup.send(
            "❌ لا توجد أغنية تعمل."
        )

        return

    voice.stop()

    await interaction.followup.send(
        "⏭️ تم التخطي."
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
        "⏸️ تم الإيقاف المؤقت.",
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
        "▶️ تم الاستئناف.",
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

            if (
                voice.is_playing()
                or
                voice.is_paused()
            ):

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

    await interaction.followup.send(
        "⏹️ تم إيقاف المشغل."
    )


# ============================================================
# /QUEUE
# ============================================================

@bot.tree.command(
    name="queue",
    description="عرض قائمة الانتظار"
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
            f"\n... و {len(state.queue) - 10} أخرى."
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
            "❌ لا توجد أغنية تعمل.",
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
    description="مغادرة الروم الصوتي"
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

    state.previous.clear()

    state.current = None

    await interaction.response.send_message(
        "👋 غادرت الروم الصوتي."
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
        "🎧 Direct Voice Playback: ON"
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

    try:

        if interaction.response.is_done():

            await interaction.followup.send(
                "❌ حدث خطأ أثناء تنفيذ الأمر.",
                ephemeral=True
            )

        else:

            await interaction.response.send_message(
                "❌ حدث خطأ أثناء تنفيذ الأمر.",
                ephemeral=True
            )

    except Exception:

        pass


# ============================================================
# MAIN
# ============================================================

def main():

    if not TOKEN:

        print(
            "❌ DISCORD_TOKEN غير موجود."
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
        "🎧 Direct Voice Playback: ON"
    )

    print(
        "⚡ Instant Playback: ON"
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
