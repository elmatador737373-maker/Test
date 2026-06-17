import os
import asyncio
import threading
import zipfile
import io
from flask import Flask
import discord
from discord import app_commands
from dotenv import load_dotenv
import aiohttp

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
        await self.tree.sync()
        print(f'✅ Bot connesso e comandi sincronizzati come {self.user}')

client = EmojiBot()

# ==========================================
# COMANDO 1: CREA E SCARICA IL FILE ZIP (NUOVO)
# ==========================================
@client.tree.command(name="crea_backup_zip", description="📦 Crea un file .zip con tutte le emoji del server e te lo invia per il download.")
async def crea_backup_zip(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild
    emojis = guild.emojis

    if not emojis:
        await interaction.followup.send("⚠️ Non ci sono emoji in questo server da inserire nel backup.", ephemeral=True)
        return

    status_message = await interaction.followup.send(f"📦 Inizio creazione backup per **{len(emojis)}** emoji. Download in corso...", ephemeral=True)

    # Creiamo lo ZIP direttamente in memoria
    zip_buffer = io.BytesIO()

    async with aiohttp.ClientSession() as session:
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            successi = 0
            falliti = 0

            for emoji in emojis:
                try:
                    # Scarica l'immagine dell'emoji dai server di Discord
                    async with session.get(str(emoji.url)) as response:
                        if response.status == 200:
                            image_data = await response.read()
                            
                            # Determina l'estensione (gif se animata, altrimenti png)
                            estensione = ".gif" if emoji.animated else ".png"
                            nome_file = f"{emoji.name}{estensione}"
                            
                            # Scrive l'immagine nello ZIP
                            archive.writestr(nome_file, image_data)
                            successi += 1
                        else:
                            falliti += 1
                except Exception:
                    falliti += 1

                # Aggiorna l'utente ogni 10 emoji caricate
                if (successi + falliti) % 10 == 0:
                    try:
                        await status_message.edit(content=f"⏳ Compressione in corso... ({successi + falliti}/{len(emojis)})\n✅ Salvate: {successi} | ⚠️ Fallite: {falliti}")
                    except:
                        pass

    # Posiziona il puntatore all'inizio del buffer di memoria per poterlo leggere
    zip_buffer.seek(0)

    if successi == 0:
        await status_message.edit(content="❌ Non è stato possibile recuperare nessuna emoji per il file ZIP.")
        return

    # Crea il file da allegare su Discord
    file_discord = discord.File(fp=zip_buffer, filename=f"backup_emoji_{guild.name.replace(' ', '_')}.zip")

    await status_message.edit(content=f"🏆 **Backup completato con successo!**\n📦 Emoji incluse nello ZIP: **{successi}/{len(emojis)}**\n\n👇 Ecco il tuo file pronto da scaricare:")
    
    # Invia il file ZIP direttamente nella chat privata dell'utente
    await interaction.followup.send(file=file_discord, ephemeral=True)


# ==========================================
# COMANDO 2: CARICA DA FILE ZIP (PUBBLICO - VISIBILE A TUTTI)
# ==========================================
@client.tree.command(name="carica_zip", description="Carica uno ZIP e importa le immagini nel server. Messaggio visibile a tutti.")
@app_commands.describe(file_zip="Trascina qui il file .zip con le emoji")
async def carica_zip(interaction: discord.Interaction, file_zip: discord.Attachment):
    # Rimosso ephemeral=True da qui così la risposta iniziale diventa pubblica
    await interaction.response.defer(ephemeral=False)

    if not interaction.user.guild_permissions.manage_expressions:
        await interaction.followup.send("❌ Non hai il permesso 'Gestisci espressioni'.")
        return

    if not file_zip.filename.endswith('.zip'):
        await interaction.followup.send("❌ Deve essere un file `.zip`.")
        return

    status_message = await interaction.followup.send("📦 Estrazione del file ZIP in corso...")

    try:
        zip_bytes = await file_zip.read()
        copiate = 0
        errori = 0
        gia_presenti = 0
        target_guild = interaction.guild

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
            tutti_i_file = archive.namelist()
            
            lista_file = []
            for f in tutti_i_file:
                og_name = f.lower()
                if og_name.endswith(('.png', '.jpg', '.jpeg', '.gif')) and not '__macosx' in og_name:
                    lista_file.append(f)

            totale_file = len(lista_file)
            if totale_file == 0:
                await status_message.edit(content="⚠️ Nessuna immagine trovata dentro lo ZIP.")
                return

            await status_message.edit(content=f"📚 Trovate **{totale_file}** emoji. Avvio caricamento forzato...")

            for file_path in lista_file:
                nome_file = os.path.basename(file_path)
                nome_emoji = os.path.splitext(nome_file)[0]
                
                nome_emoji = nome_emoji.replace("-", "_").replace(" ", "_")
                nome_emoji = "".join([c if c.isalnum() or c == "_" else "" for c in nome_emoji])
                
                if not nome_emoji: 
                    continue

                existing = discord.utils.get(target_guild.emojis, name=nome_emoji)
                if existing:
                    gia_presenti += 1
                    continue

                try:
                    image_data = archive.read(file_path)
                    await target_guild.create_custom_emoji(name=nome_emoji, image=image_data)
                    copiate += 1
                    await asyncio.sleep(0.5)
                except Exception:
                    errori += 1

                try:
                    await status_message.edit(content=f"⏳ Elaborazione: **{copiate + gia_presenti + errori}/{totale_file}**\n✅ Caricate: **{copiate}** | 🔁 Saltate: **{gia_presenti}** | ⚠️ Fallite: **{errori}**")
                except:
                    pass

        await status_message.edit(content=f"🏆 **Procedura completata!**\n✨ Caricate con successo: **{copiate}**\n🔁 Saltate: **{gia_presenti}**\n⚠️ Fallite: **{errori}**")
    except Exception as e:
        await status_message.edit(content=f"❌ Errore imprevisto: {str(e)}")

# ==========================================
# COMANDO 3: ELIMINA LE DUPLICATE (CORRETTO)
# ==========================================
@client.tree.command(name="elimina_duplicate", description="🧹 Rimuove i doppioni lasciandone solo una per tipo.")
async def elimina_duplicate(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if not interaction.user.guild_permissions.manage_expressions:
        await interaction.followup.send("❌ Permessi mancanti.", ephemeral=True)
        return

    guild = interaction.guild
    all_emojis = guild.emojis
    if not all_emojis:
        await interaction.followup.send("⚠️ Nessuna emoji.", ephemeral=True)
        return

    await interaction.followup.send("🔍 Rimozione duplicati avviata...", ephemeral=True)
    nomi_visti = set()
    duplicate_eliminate, errori = 0, 0

    for emoji in all_emojis:
        nome_standard = emoji.name.lower()
        if nome_standard in nomi_visti:
            try:
                await emoji.delete()
                duplicate_eliminate += 1
                await asyncio.sleep(0.3)
            except Exception: errori += 1
        else:
            nomi_visti.add(nome_standard)

    await interaction.followup.send(f"🧹 **Pulizia completata!**\n🗑️ Eliminate: **{duplicate_eliminate}**\n💎 Rimaste: **{len(nomi_visti)}**", ephemeral=True)

# ==========================================
# COMANDO 4: RESET GENERALE (ELIMINA TUTTO)
# ==========================================
@client.tree.command(name="elimina_tutte_emoji", description="⚠️ CANCELLA TUTTE LE EMOJI DEL SERVER.")
async def elimina_tutte_emoji(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if not interaction.user.guild_permissions.administrator:
        await interaction.followup.send("❌ Solo per Amministratori.", ephemeral=True)
        return

    guild = interaction.guild
    emojis_da_eliminare = guild.emojis
    if not emojis_da_eliminare:
        await interaction.followup.send("⚠️ Nessuna emoji da eliminare.", ephemeral=True)
        return

    await interaction.followup.send(f"🗑️ Eliminazione di massa per {len(emojis_da_eliminare)} emoji...", ephemeral=True)
    eliminate, errori = 0, 0

    for emoji in emojis_da_eliminare:
        try:
            await emoji.delete()
            eliminate += 1
            await asyncio.sleep(0.3)
        except Exception: errori += 1

    await interaction.followup.send(f"✅ Svuotato!\n🗑️ Eliminate: **{eliminate}/{len(emojis_da_eliminare)}**", ephemeral=True)

# ==========================================
# AVVIO BOT
# ==========================================
if TOKEN:
    keep_alive()
    client.run(TOKEN)
else:
    print("❌ Manca il DISCORD_TOKEN nelle variabili d'ambiente.")
