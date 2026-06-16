import discord
from discord import app_commands
import requests
import asyncio

# Configurazione del bot con tutti gli intenti necessari
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.emojis = True

class EmojiCloner(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def on_ready(self):
        # Sincronizza i comandi slash globalmente
        await self.tree.sync()
        print(f'✅ Bot connesso come {self.user}')

client = EmojiCloner()

@client.tree.command(name="clona_emoji", description="Copia le emoji da un server a questo usando l'ID del server sorgente.")
@app_commands.describe(source_guild_id="L'ID del server da cui vuoi copiare le emoji")
async def clona_emoji(interaction: discord.Interaction, source_guild_id: str):
    # Rispondi subito per evitare il timeout di Discord (3 secondi)
    await interaction.response.defer(ephemeral=True)

    # Verifica i permessi dell'utente nel server attuale
    if not interaction.user.guild_permissions.manage_expressions:
        await interaction.followup.send("❌ Non hai il permesso 'Gestisci espressioni' (emoji) in questo server.", ephemeral=True)
        return

    # Trova il server sorgente
    try:
        source_guild = client.get_guild(int(source_guild_id))
    except ValueError:
        await interaction.followup.send("❌ ID server non valido. Inserisci solo numeri.", ephemeral=True)
        return

    if not source_guild:
        await interaction.followup.send("❌ Non sono riuscito a trovare il server sorgente. Assicurati che il bot sia presente anche lì!", ephemeral=True)
        return

    target_guild = interaction.guild
    emojis_to_copy = source_guild.emojis

    if not emojis_to_copy:
        await interaction.followup.send(f"⚠️ Il server `{source_guild.name}` non ha emoji da copiare.", ephemeral=True)
        return

    await interaction.followup.send(f"🔄 Trovate {len(emojis_to_copy)} emoji. Inizio la copia in `{target_guild.name}`...", ephemeral=True)

    copiate = 0
    errori = 0

    for emoji in emojis_to_copy:
        # Controlla se l'emoji esiste già per nome (evita duplicati)
        existing = discord.utils.get(target_guild.emojis, name=emoji.name)
        if existing:
            continue

        try:
            # Scarica l'immagine dell'emoji
            response = requests.get(emoji.url)
            if response.status_code == 200:
                # Crea l'emoji nel server di destinazione
                await target_guild.create_custom_emoji(name=emoji.name, image=response.content)
                copiate += 1
                # Piccolo delay per evitare il rate-limit di Discord
                await asyncio.sleep(1)
        except discord.HTTPException as e:
            print(f"Errore durante la copia di {emoji.name}: {e}")
            errori += 1
        except Exception as e:
            print(f"Errore generico: {e}")
            errori += 1

    await interaction.followup.send(f"✅ Processo completato!\n🔹 Emoji copiate con successo: {copiate}\n⚠️ Errori/Limiti raggiunti: {errori}", ephemeral=True)

# Inserisci qui il token del tuo bot preso dal Developer Portal
TOKEN = "IL_TUO_TOKEN_QUI"
client.run(TOKEN)
