import os, re, sqlite3, logging
import discord
from discord.ext import commands
from discord import app_commands

# COLORS_SOK_2B
# Required Environment Variables:
# DISCORD_TOKEN, OWNER_CODE, OWNER_USER_ID
# Install: pip install -U discord.py
# Enable: Server Members Intent + Message Content Intent

DB="colors_sok_2b.sqlite3"
IMAGE="colors.png"
COLORS=[
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

intents=discord.Intents.default()
intents.members=True
intents.message_content=True
bot=commands.Bot(command_prefix="!",intents=intents)
db=sqlite3.connect(DB,check_same_thread=False)
db.row_factory=sqlite3.Row

def init():
    db.execute("""CREATE TABLE IF NOT EXISTS settings(
      guild_id INTEGER PRIMARY KEY,
      members_on INTEGER DEFAULT 1,
      admins_on INTEGER DEFAULT 1,
      system_on INTEGER DEFAULT 1,
      log_channel INTEGER)""")
    db.execute("""CREATE TABLE IF NOT EXISTS roles(
      guild_id INTEGER,user_id INTEGER,role_id INTEGER,
      PRIMARY KEY(guild_id,user_id))""")
    db.commit()

def ensure(gid):
    db.execute("INSERT OR IGNORE INTO settings(guild_id) VALUES(?)",(gid,)); db.commit()

def get(gid,key):
    ensure(gid)
    return bool(db.execute(f"SELECT {key} FROM settings WHERE guild_id=?",(gid,)).fetchone()[key])

def put(gid,key,value):
    ensure(gid); db.execute(f"UPDATE settings SET {key}=? WHERE guild_id=?",(int(value),gid)); db.commit()

def admin(m):
    return isinstance(m,discord.Member) and (m.guild.owner_id==m.id or m.guild_permissions.administrator)

def owner(uid):
    x=os.getenv("OWNER_USER_ID","")
    return x.isdigit() and int(x)==uid

def valid_hex(s):
    s=s.strip().upper()
    if not s.startswith("#"): s="#"+s
    if re.fullmatch(r"#[0-9A-F]{6}",s): return s
    if re.fullmatch(r"#[0-9A-F]{3}",s): return "#"+''.join(c*2 for c in s[1:])
    return None

def by_number(n):
    return next(((h,nm) for i,h,nm in COLORS if i==n),None)

async def color_role(member):
    row=db.execute("SELECT role_id FROM roles WHERE guild_id=? AND user_id=?",
                   (member.guild.id,member.id)).fetchone()
    role=member.guild.get_role(row["role_id"]) if row else None
    if role is None:
        role=await member.guild.create_role(name=f"COLOR • {member.display_name}"[:100],
                                            reason="COLORS_SOK_2B personal color role")
        db.execute("INSERT OR REPLACE INTO roles VALUES(?,?,?)",
                   (member.guild.id,member.id,role.id)); db.commit()
    return role

async def write_log(guild,member,old,new,who):
    row=db.execute("SELECT log_channel FROM settings WHERE guild_id=?",(guild.id,)).fetchone()
    ch=guild.get_channel(row["log_channel"]) if row and row["log_channel"] else None
    if not ch:return
    await ch.send(
      f"🎨 COLOR LOG\n\n👤 العضو:\n{member.display_name}\n\n"
      f"🆔 ID:\n{member.id}\n\n🔴 اللون السابق:\n{old}\n\n"
      f"🟢 اللون الجديد:\n{new}\n\n👮 بواسطة:\n{who}\n\n"
      f"🕒 الوقت:\n{discord.utils.utcnow().strftime('%Y/%m/%d %H:%M:%S')}")

async def apply(member,value,who):
    if value.strip().isdigit():
        n=int(value.strip()); p=by_number(n)
        if not p: raise ValueError("رقم اللون يجب أن يكون من 001 إلى 100.")
        hx,_=p; label=f"COLOR {n}"
    else:
        hx=valid_hex(value)
        if not hx: raise ValueError("HEX غير صالح. مثال: #F11111 أو F11111.")
        label=hx
    role=await color_role(member)
    old=role.name
    await role.edit(name=f"COLOR • {member.display_name}"[:100],
                    color=discord.Color(int(hx[1:],16)),
                    reason="COLORS_SOK_2B")
    if role not in member.roles:
        await member.add_roles(role,reason="COLORS_SOK_2B")
    await write_log(member.guild,member,old,label,who)
    return label,hx

@bot.tree.command(name="colors",description="عرض صورة الألوان")
async def colors_cmd(i:discord.Interaction):
    if not i.guild:return await i.response.send_message("❌ استخدمه داخل السيرفر.",ephemeral=True)
    if not get(i.guild.id,"system_on"):return await i.response.send_message("⛔ النظام متوقف.",ephemeral=True)
    await i.response.send_message("🎨 أرسل رقم اللون أو HEX مباشرة.",file=discord.File(IMAGE))

@bot.tree.command(name="setcolor",description="تغيير لون عضو - الإدارة")
@app_commands.describe(user_id="ID العضو المستهدف")
async def setcolor(i:discord.Interaction,user_id:str):
    if not i.guild:return await i.response.send_message("❌ داخل السيرفر فقط.",ephemeral=True)
    if not admin(i.user):return await i.response.send_message("❌ للإدارة فقط.",ephemeral=True)
    if not get(i.guild.id,"admins_on"):return await i.response.send_message("⛔ إدارة البوت متوقفة.",ephemeral=True)
    if not user_id.isdigit():return await i.response.send_message("❌ ID غير صحيح.",ephemeral=True)
    m=i.guild.get_member(int(user_id))
    if not m:
        try:m=await i.guild.fetch_member(int(user_id))
        except discord.HTTPException:m=None
    if not m:return await i.response.send_message("❌ العضو غير موجود.",ephemeral=True)
    await i.response.send_message(f"👤 {m.mention} أرسل رقم اللون 1-100 أو HEX.",ephemeral=True)
    def check(x):return x.author.id==i.user.id and x.channel.id==i.channel.id
    try:
        msg=await bot.wait_for("message",timeout=120,check=check)
        label,hx=await apply(m,msg.content,i.user.display_name)
        await i.followup.send(f"✅ تم تطبيق {label} `{hx}` على {m.mention}.",ephemeral=True)
    except TimeoutError:
        await i.followup.send("⌛ انتهى الوقت.",ephemeral=True)
    except Exception as e:
        await i.followup.send(f"❌ {e}",ephemeral=True)

class OwnerModal(discord.ui.Modal,title="SOKO_IDMIN"):
    code=discord.ui.TextInput(label="رمز المالك",required=True)
    async def on_submit(self,i):
        if str(self.code)!=os.getenv("OWNER_CODE",""):
            return await i.response.send_message("❌ رمز غير صحيح.",ephemeral=True)
        await i.response.send_message("👑 لوحة المالك",view=OwnerView(),ephemeral=True)

class OwnerView(discord.ui.View):
    def __init__(self):super().__init__(timeout=300)

    @discord.ui.button(label="🎨 الأعضاء",style=discord.ButtonStyle.primary)
    async def members(self,i,b):
        if not owner(i.user.id):return await i.response.send_message("❌ غير مصرح.",ephemeral=True)
        if not i.guild:return await i.response.send_message("❌ داخل السيرفر.",ephemeral=True)
        v=not get(i.guild.id,"members_on");put(i.guild.id,"members_on",v)
        await i.response.send_message("🟢 تغيير الأعضاء مفعّل." if v else "🔴 تغيير الأعضاء متوقف.",ephemeral=True)

    @discord.ui.button(label="👑 الإدارة",style=discord.ButtonStyle.secondary)
    async def admins(self,i,b):
        if not owner(i.user.id):return await i.response.send_message("❌ غير مصرح.",ephemeral=True)
        if not i.guild:return await i.response.send_message("❌ داخل السيرفر.",ephemeral=True)
        v=not get(i.guild.id,"admins_on");put(i.guild.id,"admins_on",v)
        await i.response.send_message("🟢 الإدارة مفعلة." if v else "🔴 الإدارة متوقفة.",ephemeral=True)

    @discord.ui.button(label="🤖 النظام",style=discord.ButtonStyle.success)
    async def system(self,i,b):
        if not owner(i.user.id):return await i.response.send_message("❌ غير مصرح.",ephemeral=True)
        if not i.guild:return await i.response.send_message("❌ داخل السيرفر.",ephemeral=True)
        v=not get(i.guild.id,"system_on");put(i.guild.id,"system_on",v)
        await i.response.send_message("🟢 النظام يعمل." if v else "🔴 النظام متوقف.",ephemeral=True)

    @discord.ui.button(label="⛔ إيقاف البوت",style=discord.ButtonStyle.danger)
    async def stop(self,i,b):
        if not owner(i.user.id):return await i.response.send_message("❌ غير مصرح.",ephemeral=True)
        await i.response.send_message("⛔ إيقاف البوت.",ephemeral=True);await bot.close()

@bot.tree.command(name="SOKO_IDMIN",description="لوحة تحكم المبرمج")
async def soko(i:discord.Interaction):
    if not owner(i.user.id):return await i.response.send_message("❌ غير مصرح.",ephemeral=True)
    await i.response.send_modal(OwnerModal())

@bot.tree.command(name="help",description="مساعدة")
async def help_cmd(i:discord.Interaction):
    await i.response.send_message("🎨 /colors\n🛠️ /setcolor <user_id>\n👑 /SOKO_IDMIN\nℹ️ /help",ephemeral=True)

@bot.event
async def on_message(message):
    if message.author.bot:return
    if message.guild and get(message.guild.id,"system_on") and get(message.guild.id,"members_on"):
        raw=message.content.strip()
        if raw.isdigit() or valid_hex(raw):
            try:
                label,hx=await apply(message.author,raw,"Self")
                await message.channel.send(f"✅ {message.author.mention} تم تغيير لونك إلى {label} `{hx}`.",delete_after=8)
                try:await message.delete()
                except discord.HTTPException:pass
                return
            except Exception as e:
                await message.channel.send(f"❌ {e}",delete_after=8);return
    await bot.process_commands(message)

@bot.event
async def on_ready():
    init();await bot.tree.sync();print(f"{BOT_NAME} online: {bot.user}")

if __name__=="__main__":
    init()
    token=os.getenv("DISCORD_TOKEN")
    if not token:raise RuntimeError("DISCORD_TOKEN غير موجود.")
    bot.run(token)
