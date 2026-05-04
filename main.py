import discord
import os
import yt_dlp
import asyncio
from discord import app_commands, ui
from discord.ext import commands
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# --- SERVER FLASK ---
app = Flask('')
@app.route('/')
def home(): return "Jukebox Max Results Online!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- CONFIGURAZIONE YDL ---
YDL_OPTS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'default_search': 'scsearch',
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -filter:a "volume=1.0,aresample=48000"',
}

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

class MusicBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.queue = [] 
        self.current_volume = 1.0

    async def setup_hook(self):
        await self.tree.sync()

bot = MusicBot()

# --- LOGICA DI RIPRODUZIONE ---
def play_next(interaction):
    if len(bot.queue) > 0:
        next_song = bot.queue.pop(0)
        vc = interaction.guild.voice_client
        if vc:
            vol_str = f"volume={bot.current_volume}"
            opts = FFMPEG_OPTIONS['options'].replace("volume=1.0", vol_str)
            source = discord.FFmpegPCMAudio(next_song['url'], before_options=FFMPEG_OPTIONS['before_options'], options=opts)
            vc.play(source, after=lambda e: play_next(interaction))
            
            asyncio.run_coroutine_threadsafe(
                interaction.channel.send(f"⏭️ **In riproduzione:** {next_song['title']}"), 
                bot.loop
            )

# --- INTERFACCIA ---
class JukeboxView(ui.View):
    def __init__(self, vc):
        super().__init__(timeout=None)
        self.vc = vc

    @ui.button(label="⏯️ Pausa/Play", style=discord.ButtonStyle.blurple)
    async def pause_resume(self, interaction: discord.Interaction, button: ui.Button):
        if self.vc.is_playing():
            self.vc.pause()
            await interaction.response.send_message("⏸️ Pausa", ephemeral=True)
        else:
            self.vc.resume()
            await interaction.response.send_message("▶️ Ripreso", ephemeral=True)

    @ui.button(label="⏭️ Skip", style=discord.ButtonStyle.secondary)
    async def skip(self, interaction: discord.Interaction, button: ui.Button):
        if self.vc:
            self.vc.stop()
            await interaction.response.send_message("⏭️ Canzone saltata", ephemeral=True)

    @ui.button(label="🔊 +", style=discord.ButtonStyle.gray)
    async def vol_up(self, interaction: discord.Interaction, button: ui.Button):
        bot.current_volume = min(bot.current_volume + 0.2, 2.0)
        await interaction.response.send_message(f"🔊 Volume: {int(bot.current_volume*100)}%", ephemeral=True)

    @ui.button(label="🔉 -", style=discord.ButtonStyle.gray)
    async def vol_down(self, interaction: discord.Interaction, button: ui.Button):
        bot.current_volume = max(bot.current_volume - 0.2, 0.1)
        await interaction.response.send_message(f"🔉 Volume: {int(bot.current_volume*100)}%", ephemeral=True)

# --- COMANDO PLAY ---
@bot.tree.command(name="play", description="Riproduci musica (Sorgente: SoundCloud)")
async def play(interaction: discord.Interaction, canzone: str):
    await interaction.response.defer(thinking=True)
    
    if not interaction.user.voice:
        return await interaction.followup.send("❌ Devi essere in un canale vocale!")

    try:
        vc = interaction.guild.voice_client or await interaction.user.voice.channel.connect(self_deaf=True)

        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            # Se l'input è già un link (da autocomplete o incollo), lo usa direttamente
            info = await bot.loop.run_in_executor(None, lambda: ydl.extract_info(canzone, download=False))
            
            if 'entries' in info:
                valid_entries = [e for e in info['entries'] if e is not None]
                if not valid_entries:
                    return await interaction.followup.send("❌ Nessun brano trovato.")
                info = valid_entries[0]
            
            data = {'url': info['url'], 'title': info['title'], 'thumb': info.get('thumbnail')}

        if vc.is_playing() or vc.is_paused():
            bot.queue.append(data)
            await interaction.followup.send(f"✅ In coda: **{data['title']}**")
        else:
            vol_str = f"volume={bot.current_volume}"
            opts = FFMPEG_OPTIONS['options'].replace("volume=1.0", vol_str)
            source = discord.FFmpegPCMAudio(data['url'], before_options=FFMPEG_OPTIONS['before_options'], options=opts)
            vc.play(source, after=lambda e: play_next(interaction))
            
            embed = discord.Embed(title="🎶 Jukebox d'Elite", description=f"**In riproduzione:**\n{data['title']}", color=0xff5500)
            if data['thumb']: embed.set_image(url=data['thumb'])
            await interaction.followup.send(embed=embed, view=JukeboxView(vc))

    except Exception as e:
        await interaction.followup.send(f"❌ Errore: {e}")

# --- AUTOCOMPLETE MASSIMIZZATO (25 RISULTATI) ---
@play.autocomplete('canzone')
async def play_autocomplete(interaction: discord.Interaction, current: str):
    if len(current) < 2: return []
    try:
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            # Chiediamo 30 risultati per essere sicuri di averne 25 validi dopo i filtri
            info = await bot.loop.run_in_executor(None, lambda: ydl.extract_info(f"scsearch30:{current}", download=False))
            
            choices = []
            for e in info['entries']:
                if e and len(choices) < 25: # Limite fisico di Discord
                    title = f"🎵 {e['title'][:85]}"
                    # Passiamo l'URL come valore per una riproduzione immediata
                    choices.append(app_commands.Choice(name=title, value=e.get('webpage_url', e['url'])))
            return choices
    except: return []

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.run(TOKEN)
