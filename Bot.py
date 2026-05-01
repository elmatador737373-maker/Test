import discord
import os
import yt_dlp
import asyncio
from discord import app_commands, ui
from discord.ext import commands
from dotenv import load_dotenv

# Caricamento Token
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Opzioni per lo streaming audio (FFmpeg)
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

# Configurazione del Bot
class MusicBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Registra i comandi slash
        await self.tree.sync()
        print(f"✅ Comandi sincronizzati per {self.user}")

bot = MusicBot()

# --- LOGICA DI RICERCA YOUTUBE ---
async def get_yt_suggestions(query: str):
    if not query or len(query) < 3:
        return []
    
    ydl_opts = {'format': 'bestaudio', 'quiet': True, 'no_warnings': True}
    try:
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Ricerca veloce senza download
            info = await loop.run_in_executor(
                None, lambda: ydl.extract_info(f"ytsearch5:{query}", download=False)
            )
            return [
                app_commands.Choice(name=f"🎵 {entry['title'][:90]}", value=entry['webpage_url']) 
                for entry in info['entries']
            ]
    except Exception as e:
        print(f"Errore ricerca: {e}")
        return []

# --- INTERFACCIA JUKEBOX (BOTTONI) ---
class JukeboxView(ui.View):
    def __init__(self, vc):
        super().__init__(timeout=None)
        self.vc = vc

    @ui.button(label="Pausa/Riprendi", style=discord.ButtonStyle.primary, emoji="⏯️")
    async def pause_resume(self, interaction: discord.Interaction, button: ui.Button):
        if self.vc.is_playing():
            self.vc.pause()
            await interaction.response.send_message("⏸️ In pausa", ephemeral=True)
        elif self.vc.is_paused():
            self.vc.resume()
            await interaction.response.send_message("▶️ Ripreso", ephemeral=True)
        else:
            await interaction.response.send_message("Nulla in riproduzione", ephemeral=True)

    @ui.button(label="Stop", style=discord.ButtonStyle.danger, emoji="⏹️")
    async def stop(self, interaction: discord.Interaction, button: ui.Button):
        if self.vc:
            await self.vc.disconnect()
            await interaction.response.edit_message(content="⏹️ Riproduzione terminata.", embed=None, view=None)
        else:
            await interaction.response.send_message("Non sono connesso", ephemeral=True)

# --- COMANDI ---

@bot.tree.command(name="play", description="Riproduci musica da YouTube con stile Jukebox")
@app_commands.describe(canzone="Cerca il titolo o incolla l'URL")
async def play(interaction: discord.Interaction, canzone: str):
    await interaction.response.defer()
    
    # Controllo se l'utente è in un canale vocale
    if not interaction.user.voice:
        return await interaction.followup.send("❌ Devi essere in un canale vocale!")

    # Connessione
    vc = interaction.guild.voice_client
    if not vc:
        vc = await interaction.user.voice.channel.connect(self_deaf=True)

    # Estrazione audio
    ydl_opts = {'format': 'bestaudio/best', 'quiet': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(canzone, download=False)
            if 'entries' in info: # Se è una playlist o ricerca generica prendi il primo
                info = info['entries'][0]
            
            url = info['url']
            title = info['title']
            thumb = info.get('thumbnail')
            duration = info.get('duration_string', 'Sconosciuta')

        if vc.is_playing():
            vc.stop()

        # Riproduzione
        source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
        vc.play(source)

        # Creazione Embed Jukebox
        embed = discord.Embed(
            title="🎶 Jukebox d'Elite",
            description=f"**In riproduzione:**\n[{title}]({canzone})",
            color=0x2f3136 # Grigio scuro elegante
        )
        if thumb:
            embed.set_image(url=thumb)
        
        embed.add_field(name="⏱️ Durata", value=duration, inline=True)
        embed.add_field(name="👤 Richiesto da", value=interaction.user.mention, inline=True)
        embed.set_footer(text="Usa i bottoni qui sotto per controllare la musica")

        view = JukeboxView(vc)
        await interaction.followup.send(embed=embed, view=view)

    except Exception as e:
        await interaction.followup.send(f"❌ Errore durante la riproduzione: {e}")

@play.autocomplete('canzone')
async def play_autocomplete(interaction: discord.Interaction, current: str):
    return await get_yt_suggestions(current)

@bot.event
async def on_ready():
    print(f'--- BOT ONLINE: {bot.user} ---')

# Avvio
if __name__ == "__main__":
    bot.run(TOKEN)
