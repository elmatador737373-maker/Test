import os
import asyncio
import threading
import requests
from flask import Flask
import discord
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# ======================================================
# FLASK PER RENDER
# ======================================================
app = Flask('')

@app.route('/')
def home():
    return "Bot Online!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

# ======================================================
# CONFIGURAZIONE BOT
# ======================================================
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.emojis = True

class EmojiCloner(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def on_ready(self):
        # Svuota i vecchi comandi buggati dalla cache di Discord e sincronizza
        self.tree.clear_commands(guild=None)
        await self.tree.sync()
        print(f'✅ Bot connesso come {self.user} e comandi resettati!')

client = EmojiCloner()

# ======================================================
# COMANDO CLONA (VERSIONE DIRETTA)
# ======================================================
@client.tree.command(name="clona_emoji", description="Copia TUTTE le emoji dal server sorgente a questo.")
@app_commands.describe(source_guild_id="L'ID del server da cui vuoi copiare le emoji")
async def clona_emoji(interaction: discord.Interaction, source_guild_id: str):
    # Diciamo a Discord di aspettare
    await interaction.response.defer(ephemeral=True)

    if not interaction.user.guild_permissions.manage_expressions:
        await interaction.followup.send("❌ Non hai il permesso 'Gestisci espressioni' in questo server.", ephemeral=True)
        return

    try:
        source_guild = client.get_guild(int(source_guild_id))
    except ValueError:
        await interaction.followup.send("❌ ID server non valido.", ephemeral=True)
        return

    if not source_guild:
        await interaction.followup.send("❌ Server sorgente non trovato. Il bot è presente anche lì?", ephemeral=True)
        return

    target_guild = interaction.guild
    emojis_to_copy = source_guild.emojis

    if not emojis_to_copy:
        await interaction.followup.send("⚠️ Nessuna emoji trovata nel server sorgente.", ephemeral=True)
        return

    # Messaggio di partenza
    await interaction.followup.send(f"🔄 Trovate {len(emojis_to_copy)} emoji. Avvio clonazione diretta...", ephemeral=True)

    copiate = 0
    errori = 0
    duplicate = 0

    for emoji in emojis_to_copy:
        # Controllo duplicati (evita di rifare quelle che ha già copiato prima)
        existing = discord.utils.get(target_guild.emojis, name=emoji.name)
        if existing:
            duplicate += 1
            continue

        try:
            response = requests.get(emoji.url)
            if response.status_code == 200:
                await target_guild.create_custom_emoji(name=emoji.name, image=response.content)
                copiate += 1
                # Pausa ridotta a 1.2 secondi per andare più veloci senza bloccare Render
                await asyncio.sleep(1.2)
                
        except discord.RateLimited as e:
            # Se Discord si arrabbia, aspettiamo i secondi esatti che ci impone
            await asyncio.sleep(e.retry_after)
        except discord.HTTPException as e:
            if e.code == 30008: # Slot finiti sul server
                await interaction.followup.send(f"🚨 Spazio finito sul server! Copiate: {copiate}. Ferma qui.", ephemeral=True)
                return
            errori += 1
        except Exception:
            errori += 1

    await interaction.followup.send(
        f"✅ Operazione conclusa!\n"
        f"🔹 Nuove emoji copiate: {copiate}\n"
        f"🔁 Già presenti (saltate): {duplicate}\n"
        f"⚠️ Errori: {errori}", 
        ephemeral=True
    )

# ======================================================
# COMANDO CANCELLA
# ======================================================
@client.tree.command(name="elimina_tutte_emoji", description="⚠️ Svuota le emoji di questo server.")
async def elimina_tutte_emoji(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    if not interaction.user.guild_permissions.administrator:
        await interaction.followup.send("❌ Solo gli Amministratori possono farlo.", ephemeral=True)
        return

    guild = interaction.guild
    emojis_da_eliminare = guild.emojis

    if not emojis_da_eliminare:
        await interaction.followup.send("⚠️ Nessuna emoji da cancellare.", ephemeral=True)
        return

    await interaction.followup.send(f"🗑️ Cancellazione di {len(emojis_da_eliminare)} emoji avviata...", ephemeral=True)

    for emoji in emojis_da_eliminare:
        try:
            await emoji.delete()
            await asyncio.sleep(0.4)
        except Exception:
            pass

    await interaction.followup.send("✅ Server ripulito!", ephemeral=True)

if TOKEN:
    keep_alive()
    client.run(TOKEN)
else:
    print("❌ Manca il DISCORD_TOKEN.")
