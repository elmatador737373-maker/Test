import os
import asyncio
import threading
import zipfile
import io
from flask import Flask
import discord
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# ==========================================
# SERVER WEB MINIMALE PER RENDER (KEEP ALIVE)
# ==========================================
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

# ==========================================
# CONFIGURAZIONE BOT DISCORD
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.emojis = True

class EmojiBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def on_ready(self):
        # Forza la sincronizzazione globale dei comandi appena il bot si connette
        await self.tree.sync()
        print(f'✅ Bot connesso e comandi sincronizzati come {self.user}')

client = EmojiBot()

# ==========================================
# COMANDO 1: CARICA DA FILE ZIP
# ==========================================
@client.tree.command(name="carica_zip", description="Carica un file .zip contenente le emoji e le importa direttamente nel server.")
@app_commands.describe(file_zip="Trascina qui il file .zip con le emoji")
async def carica_zip(interaction: discord.Interaction, file_zip: discord.Attachment):
    await interaction.response.defer(ephemeral=True)

    if not interaction.user.guild_permissions.manage_expressions:
        await interaction.followup.send("❌ Non hai il permesso 'Gestisci espressioni' in questo server.", ephemeral=True)
        return

    if not file_zip.filename.endswith('.zip'):
        await interaction.followup.send("❌ Il file caricato deve essere in formato `.zip`.", ephemeral=True)
        return

    status_message = await interaction.followup.send("📦 Lettura del file ZIP in corso...", ephemeral=True)

    try:
        zip_bytes = await file_zip.read()
        copiate = 0
        errori = 0
        gia_presenti = 0
        target_guild = interaction.guild

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
            estensioni_valide = ('.png', '.jpg', '.jpeg', '.gif')
            lista_file = [f for f in archive.namelist() if f.lower().endswith(estensioni_valide) and not f.startswith('__MACOSX/')]
            totale_file = len(lista_file)
            
            if totale_file == 0:
                await status_message.edit(content="⚠️ Non ho trovato immagini valide (.png, .jpg, .gif) all'interno dello ZIP.")
                return

            await status_message.edit(content=f"📚 Trovate **{totale_file}** immagini nello ZIP. Inizio l'importazione...")

            for file_path in lista_file:
                nome_file = os.path.basename(file_path)
                nome_emoji = os.path.splitext(nome_file)[0]
                nome_emoji = "".join([c if c.isalnum() or c == "_" else "" for c in nome_emoji])
                
                if not nome_emoji:
                    continue

                # Controllo duplicati sicuro (sia minuscolo che normale)
                existing = discord.utils.get(target_guild.emojis, name=nome_emoji.lower()) or discord.utils.get(target_guild.emojis, name=nome_emoji)
                if existing:
                    gia_presenti += 1
                    continue

                try:
                    with archive.open(file_path) as file_immagine:
                        image_data = file_immagine.read()
                        await target_guild.create_custom_emoji(name=nome_emoji, image=image_data)
                        copiate += 1
                        await asyncio.sleep(0.4) # Pausa minima anti-rate limit
                except discord.HTTPException as e:
                    if e.code == 30008:
                        await status_message.edit(content=f"🚨 Spazio esaurito sul server dopo aver caricato {copiate} emoji!")
                        return
                    errori += 1
                except Exception:
                    errori += 1

                if (copiate + gia_presenti + errori) % 5 == 0:
                    try:
                        await status_message.edit(content=f"⏳ Importazione in corso... ({copiate + gia_presenti + errori}/{totale_file})\n"
                                                          f"✅ Nuove: **{copiate}** | 🔁 Duplicate saltate: **{gia_presenti}** | ⚠️ Errori: **{errori}**")
                    except: pass

        await status_message.edit(content=f"🏆 **Importazione completata!**\n\n✨ Nuove aggiunte: **{copiate}**\n🔁 Saltate (già presenti): **{gia_presenti}**\n⚠️ Errori: **{errori}**")

    except Exception as e:
        await status_message.edit(content=f"❌ Errore durante l'apertura dello ZIP: {str(e)}")

# ==========================================
# COMANDO 2: ELIMINA SOLO LE DUPLICATE
# ==========================================
@client.tree.command(name="elimina_duplicate", description="🧹 Rimuove i doppioni delle emoji nel server, lasciandone solo una per tipo.")
async def elimina_duplicate(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    if not interaction.user.guild_permissions.manage_expressions:
        await interaction.followup.send("❌ Non hai il permesso 'Gestisci espressioni' per usare questo comando.", ephemeral=True)
        return

    guild = interaction.guild
    all_emojis = guild.emojis

    if not all_emojis:
        await interaction.followup.send("⚠️ Non ci sono emoji in questo server.", ephemeral=True)
        return

    await interaction.followup.send("🔍 Analisi delle emoji e rimozione duplicati avviata...", ephemeral=True)

    nomi_visti = set()
    duplicate_eliminate = 0
    errori = 0

    for emoji in all_emojis:
        nome_standard = emoji.name.lower()

        if nome_standard in nomi_visti:
            try:
                await emoji.delete()
                duplicate_eliminate += 1
                await asyncio.sleep(0.3)
            except Exception:
                errori += 1
        else:
            nomi_visti.add(nome_standard)

    if duplicate_eliminate == 0:
        await interaction.followup.send("✨ Nessun duplicato trovato! Il server è già pulito.", ephemeral=True)
    else:
        await interaction.followup.send(f"🧹 **Pulizia completata!**\n🗑️ Duplicate eliminate: **{duplicate_eliminate}**\n💎 Emoji uniche rimaste: **{len(nomi_visti)}**\n⚠️ Errori: **{errori}**", ephemeral=True)

# ==========================================
# COMANDO 3: ELIMINA TUTTE LE EMOJI (RESET)
# ==========================================
@client.tree.command(name="elimina_tutte_emoji", description="⚠️ CANCELLA TUTTE LE EMOJI DA QUESTO SERVER. Richiede permessi di Amministratore.")
async def elimina_tutte_emoji(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    if not interaction.user.guild_permissions.administrator:
        await interaction.followup.send("❌ Questo comando distruttivo può essere eseguito solo da un Amministratore.", ephemeral=True)
        return

    guild = interaction.guild
    emojis_da_eliminare = guild.emojis

    if not emojis_da_eliminare:
        await interaction.followup.send("⚠️ Non ci sono emoji da eliminare.", ephemeral=True)
        return

    totale = len(emojis_da_eliminare)
    await interaction.followup.send(f"🗑️ Rimozione di massa avviata per {totale} emoji...", ephemeral=True)

    eliminate = 0
    errori = 0

    for emoji in emojis_da_eliminare:
        try:
            await emoji.delete()
            eliminate += 1
            await asyncio.sleep(0.3)
        except Exception:
            errori += 1

    await interaction.followup.send(f"✅ Svuotamento completato!\n🗑️ Emoji eliminate: **{eliminate}/{totale}**\n⚠️ Errori: **{errori}**", ephemeral=True)

# ==========================================
# AVVIO BOT
# ==========================================
if TOKEN:
    keep_alive()
    client.run(TOKEN)
else:
    print("❌ Manca il DISCORD_TOKEN nelle variabili d'ambiente.")
