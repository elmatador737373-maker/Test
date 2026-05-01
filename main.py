import discord
import os
import yt_dlp
import asyncio
from discord import app_commands, ui
from discord.ext import commands
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# --- SERVER FLASK PER PING ---
app = Flask('')

@app.route('/')
def home():
    return "Il Jukebox è online!"

def run_flask():
    # Render assegna automaticamente una porta nella variabile d'ambiente PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# --- CONFIGURAZIONE BOT DISCORD ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

class MusicBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print(f"✅ Slash Commands sincronizzati.")

bot = MusicBot()

# --- LOGICA JUKEBOX ---
async def get_yt_suggestions(query: str):
    if not query or len(query) < 3: return []
    ydl_opts = {'format': 'bestaudio', 'quiet': True}
    try:
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(f"ytsearch5:{query}", download=False))
            return [app_commands.Choice(name=f"🎵 {e['title'][:90]}", value=e['webpage_url']) for e in info['entries']]
    except: return []

class JukeboxView(ui.View):
    def __init__(self, vc):
        super().__init__(timeout=None)
        self.vc = vc

    @ui.button(label="Pausa/Riprendi", style=discord.ButtonStyle.primary, emoji="⏯️")
    async def pause_resume(self, interaction: discord.Interaction, button: ui.Button):
        if self.vc.is_playing():
            self.vc.pause()
            await interaction.response.send_message("⏸️ Pausa", ephemeral=True)
        elif self.vc.is_paused():
            self.vc.resume()
            await interaction.response.send_message("▶️ Ripreso", ephemeral=True)

    @ui.button(label="Stop", style=discord.ButtonStyle.danger, emoji="⏹️")
    async def stop(self, interaction: discord.Interaction, button: ui.Button):
        await self.vc.disconnect()
        await interaction.response.edit_message(content="⏹️ Sessione terminata.", embed=None, view=None)

@bot.tree.command(name="play", description="Riproduci musica")
@app_commands.describe(canzone="Titolo o URL")
async def play(interaction: discord.Interaction, canzone: str):
    await interaction.response.defer()
    if not interaction.user.voice:
        return await interaction.followup.send("❌ Entra in un canale vocale!")

    vc = interaction.guild.voice_client or await interaction.user.voice.channel.connect(self_deaf=True)

    with yt_dlp.YoutubeDL({'format': 'bestaudio', 'quiet': True}) as ydl:
        info = ydl.extract_info(canzone, download=False)
        if 'entries' in info: info = info['entries'][0]
        url, title, thumb = info['url'], info['title'], info.get('thumbnail')

    if vc.is_playing(): vc.stop()
    vc.play(discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS))

    embed = discord.Embed(title="🎶 Jukebox d'Elite", description=f"**In riproduzione:**\n{title}", color=0x2f3136)
    if thumb: embed.set_image(url=thumb)
    
    await interaction.followup.send(embed=embed, view=JukeboxView(vc))

@play.autocomplete('canzone')
async def play_autocomplete(interaction: discord.Interaction, current: str):
    return await get_yt_suggestions(current)

# --- AVVIO ---
if __name__ == "__main__":
    keep_alive() # Avvia Flask in parallelo
    bot.run(TOKEN)
