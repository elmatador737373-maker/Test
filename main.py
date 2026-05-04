import discord
import os
import yt_dlp
import asyncio
from discord import app_commands, ui
from discord.ext import commands
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# --- SERVER FLASK (PER RENDER) ---
app = Flask('')
@app.route('/')
def home(): return "Multi-Source Jukebox Online!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- CONFIGURAZIONE MULTI-SORGENTE ---
# SoundCloud è la sorgente predefinita per le ricerche testuali per evitare blocchi
YDL_OPTS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'default_search': 'scsearch', # Cerca su SoundCloud se non è un URL
    'source_address': '0.0.0.0',
    'nocheckcertificate': True,
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

# --- CONFIGURAZIONE BOT ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

class MusicBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.queue = [] 

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Comandi Multi-Source sincronizzati.")

bot = MusicBot()

# --- LOGICA DI RIPRODUZIONE ---
def play_next(interaction):
    if len(bot.queue) > 0:
        next_song = bot.queue.pop(0)
        vc = interaction.guild.voice_client
        if vc:
            vc.play(discord.FFmpegPCMAudio(next_song['url'], **FFMPEG_OPTIONS), 
                    after=lambda e: play_next(interaction))
            
            embed = discord.Embed(title="🎵 In coda ora", description=next_song['title'], color=0x00ff00)
            asyncio.run_coroutine_threadsafe(interaction.channel.send(embed=embed), bot.loop)

# --- INTERFACCIA JUKEBOX ---
class JukeboxView(ui.View):
    def __init__(self, vc):
        super().__init__(timeout=None)
        self.vc = vc

    @ui.button(label="⏯️ Pausa/Riprendi", style=discord.ButtonStyle.blurple)
    async def pause_resume(self, interaction: discord.Interaction, button: ui.Button):
        if self.vc.is_playing():
            self.vc.pause()
            await interaction.response.send_message("⏸️ Pausa", ephemeral=True)
        elif self.vc.is_paused():
            self.vc.resume()
            await interaction.response.send_message("▶️ Ripresa", ephemeral=True)

    @ui.button(label="⏭️ Skip", style=discord.ButtonStyle.secondary)
    async def skip(self, interaction: discord.Interaction, button: ui.Button):
        if self.vc and (self.vc.is_playing() or self.vc.is_paused()):
            self.vc.stop()
            await interaction.response.send_message("⏭️ Canzone saltata", ephemeral=True)

    @ui.button(label="⏹️ Stop", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: ui.Button):
        bot.queue.clear()
        if self.vc: await self.vc.disconnect()
        await interaction.response.edit_message(content="⏹️ Sessione terminata.", embed=None, view=None)

# --- COMANDI ---

@bot.tree.command(name="play", description="Suona musica da SoundCloud, Bandcamp o URL")
@app_commands.describe(canzone="Titolo o link (Sorgente predefinita: SoundCloud)")
async def play(interaction: discord.Interaction, canzone: str):
    await interaction.response.defer(thinking=True)
    
    if not interaction.user.voice:
        return await interaction.followup.send("❌ Devi essere in un canale vocale!")

    try:
        vc = interaction.guild.voice_client or await interaction.user.voice.channel.connect(self_deaf=True)

        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            # Se l'utente mette un URL, yt-dlp lo riconosce, altrimenti cerca su SoundCloud
            info = ydl.extract_info(canzone, download=False)
            if 'entries' in info: info = info['entries'][0]
            
            data = {
                'url': info['url'], 
                'title': info.get('title', 'Titolo sconosciuto'), 
                'thumb': info.get('thumbnail'),
                'original_url': info.get('webpage_url')
            }

        if vc.is_playing() or vc.is_paused():
            bot.queue.append(data)
            await interaction.followup.send(f"✅ Aggiunto alla coda: **{data['title']}**")
        else:
            vc.play(discord.FFmpegPCMAudio(data['url'], **FFMPEG_OPTIONS), after=lambda e: play_next(interaction))
            
            embed = discord.Embed(
                title="🎶 Multi-Source Jukebox", 
                description=f"**In riproduzione:**\n{data['title']}\n\n*Sorgente: {data['original_url']}*", 
                color=0xff5500 # Colore arancio SoundCloud
            )
            if data['thumb']: embed.set_image(url=data['thumb'])
            await interaction.followup.send(embed=embed, view=JukeboxView(vc))

    except Exception as e:
        await interaction.followup.send(f"❌ Errore nel caricamento: {e}")

@bot.tree.command(name="queue", description="Mostra la coda attuale")
async def queue(interaction: discord.Interaction):
    if not bot.queue:
        return await interaction.response.send_message("La coda è vuota.")
    lista = "\n".join([f"{i+1}. {s['title']}" for i, s in enumerate(bot.queue[:10])])
    await interaction.response.send_message(f"📜 **Coda:**\n{lista}")

@play.autocomplete('canzone')
async def play_autocomplete(interaction: discord.Interaction, current: str):
    if len(current) < 3: return []
    try:
        # Autocomplete focalizzato su SoundCloud per velocità e affidabilità
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(f"scsearch5:{current}", download=False))
            
            return [
                app_commands.Choice(name=f"🟠 {e['title'][:90]}", value=e.get('webpage_url', e['url'])) 
                for e in info['entries']
            ]
    except: return []

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.run(TOKEN)
