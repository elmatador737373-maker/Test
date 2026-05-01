import discord
import os
import yt_dlp
import asyncio
from discord import app_commands, ui
from discord.ext import commands
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

# --- SERVER FLASK (PER RENDER/UPTIME) ---
app = Flask('')
@app.route('/')
def home(): return "Jukebox Online!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- CONFIGURAZIONE BOT ---
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
        self.queue = [] 

    async def setup_hook(self):
        await self.tree.sync()
        print(f"✅ Slash Commands sincronizzati.")

bot = MusicBot()

# --- LOGICA DI RIPRODUZIONE ---
def play_next(interaction):
    if len(bot.queue) > 0:
        next_song = bot.queue.pop(0)
        vc = interaction.guild.voice_client
        if vc:
            vc.play(discord.FFmpegPCMAudio(next_song['url'], **FFMPEG_OPTIONS), 
                    after=lambda e: play_next(interaction))
            
            # Messaggio automatico per la prossima canzone
            embed = discord.Embed(title="🎵 Prossimo brano", description=next_song['title'], color=0x00ff00)
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
            await interaction.response.send_message("⏸️ In pausa", ephemeral=True)
        elif self.vc.is_paused():
            self.vc.resume()
            await interaction.response.send_message("▶️ Ripreso", ephemeral=True)
        else:
            await interaction.response.send_message("Nulla in riproduzione", ephemeral=True)

    @ui.button(label="⏭️ Skip", style=discord.ButtonStyle.secondary)
    async def skip(self, interaction: discord.Interaction, button: ui.Button):
        if self.vc and (self.vc.is_playing() or self.vc.is_paused()):
            self.vc.stop()
            await interaction.response.send_message("⏭️ Canzone saltata", ephemeral=True)

    @ui.button(label="⏹️ Stop", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: ui.Button):
        bot.queue.clear()
        await self.vc.disconnect()
        await interaction.response.edit_message(content="⏹️ Sessione terminata e coda svuotata.", embed=None, view=None)

# --- COMANDI ---

@bot.tree.command(name="play", description="Riproduci una canzone o aggiungila alla coda")
@app_commands.describe(canzone="Cerca il titolo o incolla il link")
async def play(interaction: discord.Interaction, canzone: str):
    await interaction.response.defer()
    
    if not interaction.user.voice:
        return await interaction.followup.send("❌ Entra in un canale vocale!")

    vc = interaction.guild.voice_client or await interaction.user.voice.channel.connect(self_deaf=True)

    with yt_dlp.YoutubeDL({'format': 'bestaudio', 'quiet': True, 'no_warnings': True}) as ydl:
        try:
            info = ydl.extract_info(canzone, download=False)
            if 'entries' in info: info = info['entries'][0]
            data = {'url': info['url'], 'title': info['title'], 'thumb': info.get('thumbnail')}
        except Exception as e:
            return await interaction.followup.send(f"❌ Errore nel caricamento: {e}")

    if vc.is_playing() or vc.is_paused():
        bot.queue.append(data)
        await interaction.followup.send(f"✅ Aggiunto alla coda: **{data['title']}**")
    else:
        vc.play(discord.FFmpegPCMAudio(data['url'], **FFMPEG_OPTIONS), after=lambda e: play_next(interaction))
        
        embed = discord.Embed(title="🎶 Jukebox d'Elite", description=f"**In riproduzione:**\n{data['title']}", color=0x2f3136)
        if data['thumb']: embed.set_image(url=data['thumb'])
        embed.set_footer(text=f"Richiesto da {interaction.user.display_name}")
        
        await interaction.followup.send(embed=embed, view=JukeboxView(vc))

@bot.tree.command(name="queue", description="Mostra le prossime canzoni")
async def queue(interaction: discord.Interaction):
    if not bot.queue:
        return await interaction.response.send_message("La coda è attualmente vuota.")
    
    msg = "**📜 Coda attuale:**\n" + "\n".join([f"{i+1}. {s['title']}" for i, s in enumerate(bot.queue[:10])])
    await interaction.response.send_message(msg)

@bot.tree.command(name="volume", description="Cambia il volume (0-100)")
async def volume(interaction: discord.Interaction, livello: int):
    vc = interaction.guild.voice_client
    if vc and vc.source:
        if 0 <= livello <= 100:
            # Applichiamo il trasformatore di volume se non presente
            if not isinstance(vc.source, discord.PCMVolumeTransformer):
                vc.source = discord.PCMVolumeTransformer(vc.source)
            vc.source.volume = livello / 100
            await interaction.response.send_message(f"🔊 Volume impostato al {livello}%")
        else:
            await interaction.response.send_message("Inserisci un numero tra 0 e 100.", ephemeral=True)

# --- AUTOCOMPLETE VELOCE ---
@play.autocomplete('canzone')
async def play_autocomplete(interaction: discord.Interaction, current: str):
    if len(current) < 3: return []
    try:
        # Ricerca rapidissima usando extract_flat
        ydl_opts = {'quiet': True, 'extract_flat': True, 'force_generic_extractor': False}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(f"ytsearch5:{current}", download=False))
            
            choices = []
            for e in info['entries']:
                title = e.get('title', 'Video senza titolo')[:90]
                url = f"https://www.youtube.com/watch?v={e['id']}" if 'id' in e else e.get('url')
                if url:
                    choices.append(app_commands.Choice(name=f"🎵 {title}", value=url))
            return choices
    except:
        return []

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.run(TOKEN)
