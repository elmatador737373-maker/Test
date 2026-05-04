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
def home(): return "SoundCloud Jukebox Online!"

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
    # Aggiungiamo un'identità per non essere bloccati
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

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

bot = MusicBot()

# --- LOGICA DI RIPRODUZIONE ---
def play_next(interaction):
    if len(bot.queue) > 0:
        next_song = bot.queue.pop(0)
        vc = interaction.guild.voice_client
        if vc:
            vc.play(discord.FFmpegPCMAudio(next_song['url'], **FFMPEG_OPTIONS), 
                    after=lambda e: play_next(interaction))
            asyncio.run_coroutine_threadsafe(
                interaction.channel.send(f"🟠 Ora in riproduzione: **{next_song['title']}**"), 
                bot.loop
            )

class JukeboxView(ui.View):
    def __init__(self, vc):
        super().__init__(timeout=None)
        self.vc = vc

    @ui.button(label="⏯️ Pausa/Riprendi", style=discord.ButtonStyle.blurple)
    async def pause_resume(self, interaction: discord.Interaction, button: ui.Button):
        if self.vc.is_playing():
            self.vc.pause()
            await interaction.response.send_message("⏸️ In pausa", ephemeral=True)
        else:
            self.vc.resume()
            await interaction.response.send_message("▶️ Ripreso", ephemeral=True)

    @ui.button(label="⏹️ Stop", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: ui.Button):
        bot.queue.clear()
        if self.vc: await self.vc.disconnect()
        await interaction.response.edit_message(content="⏹️ Sessione terminata.", embed=None, view=None)

# --- COMANDO PLAY ---
@bot.tree.command(name="play", description="Cerca e riproduci da SoundCloud")
async def play(interaction: discord.Interaction, canzone: str):
    await interaction.response.defer(thinking=True)
    
    if not interaction.user.voice:
        return await interaction.followup.send("❌ Entra in un canale vocale!")

    try:
        vc = interaction.guild.voice_client or await interaction.user.voice.channel.connect(self_deaf=True)

        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            # Se l'input non è un link, aggiungiamo scsearch: esplicitamente
            search_query = canzone if canzone.startswith('http') else f"scsearch1:{canzone}"
            
            # Usiamo il loop per non bloccare il bot durante la ricerca
            info = await bot.loop.run_in_executor(None, lambda: ydl.extract_info(search_query, download=False))
            
            if 'entries' in info:
                if not info['entries']:
                    return await interaction.followup.send("❌ Nessun risultato trovato su SoundCloud.")
                info = info['entries'][0]
            
            data = {'url': info['url'], 'title': info['title'], 'thumb': info.get('thumbnail')}

        if vc.is_playing() or vc.is_paused():
            bot.queue.append(data)
            await interaction.followup.send(f"✅ Aggiunto alla coda: **{data['title']}**")
        else:
            vc.play(discord.FFmpegPCMAudio(data['url'], **FFMPEG_OPTIONS), after=lambda e: play_next(interaction))
            embed = discord.Embed(title="🟠 Jukebox SoundCloud", description=f"Suonando: **{data['title']}**", color=0xff5500)
            if data['thumb']: embed.set_image(url=data['thumb'])
            await interaction.followup.send(embed=embed, view=JukeboxView(vc))

    except Exception as e:
        print(f"Errore Play: {e}")
        await interaction.followup.send(f"❌ Errore durante la ricerca: {e}")

# --- AUTOCOMPLETE ---
@play.autocomplete('canzone')
async def play_autocomplete(interaction: discord.Interaction, current: str):
    if not current or len(current) < 3:
        return []
    
    try:
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            # Ricerca veloce di 5 brani
            info = await bot.loop.run_in_executor(None, lambda: ydl.extract_info(f"scsearch5:{current}", download=False))
            
            if 'entries' not in info:
                return []

            return [
                app_commands.Choice(name=f"🟠 {e['title'][:90]}", value=e.get('webpage_url', e['url'])) 
                for e in info['entries'] if e.get('title')
            ]
    except Exception as e:
        print(f"Errore Autocomplete: {e}")
        return []

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.run(TOKEN)
