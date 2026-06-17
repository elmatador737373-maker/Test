import os
import asyncio
import threading
import aiohttp
from flask import Flask
import discord
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# ==========================================
# SERVER WEB MINIMALE PER RENDER
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

class EmojiCloner(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def on_ready(self):
        await self.tree.sync()
        print(f'✅ Bot connesso come {self.user}')

client = EmojiCloner()

# ==========================================
# COMANDO 1: CLONA EMOTE (CON LOG EPHEMERAL)
# ==========================================
# ==========================================
# COMANDO CLONA: VERSIONE ANTI-BLOCCO 5 EMOJI
# ==========================================
@client.tree.command(name="clona_emoji", description="Copia le emoji rallentando il ritmo per evitare il blocco di Discord.")
@app_commands.describe(source_guild_id="L'ID del server da cui vuoi copiare le emoji")
async def clona_emoji(interaction: discord.Interaction, source_guild_id: str):
    await interaction.response.defer(ephemeral=True)

    if not interaction.user.guild_permissions.manage_expressions:
        await interaction.followup.send("❌ Non hai il permesso 'Gestisci espressioni' in questo server.", ephemeral=True)
        return

    try:
        source_guild = client.get_guild(int(source_guild_id))
    except ValueError:
        await interaction.followup.send("❌ ID server sorgente non valido.", ephemeral=True)
        return

    if not source_guild:
        await interaction.followup.send("❌ Server sorgente non trovato.", ephemeral=True)
        return

    emojis_to_copy = source_guild.emojis
    target_guild = interaction.guild
    totale_emoji = len(emojis_to_copy)

    if not emojis_to_copy:
        await interaction.followup.send(f"⚠️ Il server `{source_guild.name}` non ha emoji.", ephemeral=True)
        return

    status_message = await interaction.followup.send(
        f"🔄 **Clonazione avviata!**\n📦 Server sorgente: `{source_guild.name}`\n🔮 Totale: **{totale_emoji}**\n⏳ Controllo duplicati in corso...", 
        ephemeral=True
    )

    copiate = 0
    errori = 0
    gia_presenti = 0
    analizzate = 0
    lista_log_recenti = []

    timeout_config = aiohttp.ClientTimeout(total=10) # Timeout alzato a 10s per connessioni stabili

    async with aiohttp.ClientSession(timeout=timeout_config) as session:
        for emoji in emojis_to_copy:
            analizzate += 1
            
            existing = discord.utils.get(target_guild.emojis, name=emoji.name)
            if existing:
                gia_presenti += 1
                # Non aggiorniamo lo schermo per ogni duplicato, andiamo dritti al punto
                continue

            # Forza l'aggiornamento visivo appena trova un'emoji da copiare davvero
            percentuale = int((analizzate / totale_emoji) * 100)
            barra = "🟩" * int(percentuale / 10) + "⬛" * (10 - int(percentuale / 10))
            testo_cronologia = "\n".join(lista_log_recenti) if lista_log_recenti else "Copia in corso..."
            
            try:
                await status_message.edit(content=f"🔄 **Clonazione in corso (Ritmo sicuro)...**\n"
                                                  f"📊 Avanzamento: {barra} **{percentuale}%** ({analizzate}/{totale_emoji})\n"
                                                  f"⚡ Sto clonando: `{emoji.name}`\n\n"
                                                  f"🔹 Nuove: **{copiate}** | 🔁 Duplicate saltate: **{gia_presenti}** | ⚠️ Errori: **{errori}**\n\n"
                                                  f"📋 **Ultime azioni:**\n```text\n{testo_cronologia}\n```")
            except: pass

            try:
                async with session.get(str(emoji.url)) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        await target_guild.create_custom_emoji(name=emoji.name, image=image_data)
                        copiate += 1
                        lista_log_recenti.append(f"✅ Copiata: `{emoji.name}`")
                        
                        # Alziamo la pausa a 3.5 secondi. È più lento, ma impedisce a Discord di murare il bot alla quinta emoji
                        await asyncio.sleep(3.5)
                    else:
                        lista_log_recenti.append(f"❌ Errore scaricamento su `{emoji.name}`")
                        errori += 1
                        
            except discord.RateLimited as e:
                # Se becchiamo il blocco, aggiorniamo il log visivo dicendo quanti secondi aspettare
                attesa = int(e.retry_after) + 2
                lista_log_recenti.append(f"⚠️ Blocco anti-spam. Pausa forzata di {attesa}s...")
                await asyncio.sleep(attesa)
                
            except discord.HTTPException as e:
                if e.code == 30008: 
                    lista_log_recenti.append("🚨 Spazio esaurito!")
                    break
                lista_log_recenti.append(f"❌ Errore Discord {e.code}")
                errori += 1
            except Exception:
                lista_log_recenti.append(f"❌ Errore imprevisto su `{emoji.name}`")
                errori += 1

            if len(lista_log_recenti) > 5:
                lista_log_recenti.pop(0)

    await status_message.edit(content=f"🏆 **Sessione Completata!**\n📊 Conto finale: ({analizzate}/{totale_emoji}) analizzate.\n\n✨ Nuove emoji aggiunte in questa sessione: **{copiate}**\n🔁 Totale duplicate nel server: **{gia_presenti}**\n⚠️ Errori: **{errori}**\n\n💡 *Se mancano ancora emoji, aspetta 30 secondi e rilancia il comando. Continuerà a scavalcare quelle vecchie e a fare blocchi da 15-20 emoji alla volta senza piantarsi.*")

# ==========================================
# COMANDO 4: ELIMINA SOLO LE EMOJI DUPLICATE
# ==========================================
@client.tree.command(name="elimina_duplicate", description="🧹 Rimuove i doppioni delle emoji nel server, lasciandone solo una per tipo.")
async def elimina_duplicate(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    # Controllo permessi
    if not interaction.user.guild_permissions.manage_expressions:
        await interaction.followup.send("❌ Non hai il permesso 'Gestisci espressioni' per usare questo comando.", ephemeral=True)
        return

    guild = interaction.guild
    all_emojis = guild.emojis

    if not all_emojis:
        await interaction.followup.send("⚠️ Non ci sono emoji in questo server.", ephemeral=True)
        return

    await interaction.followup.send("🔍 Analisi delle emoji in corso... Sto cercando i doppioni...", ephemeral=True)

    nomi_visti = set()
    duplicate_eliminate = 0
    errori = 0

    for emoji in all_emojis:
        # Portiamo il nome in minuscolo per un controllo preciso (es. "Gold" e "gold" vengono visti come doppioni)
        nome_standard = emoji.name.lower()

        if nome_standard in nomi_visti:
            # Se il nome è già presente nel set, questa emoji è un doppione e va eliminata
            try:
                await emoji.delete()
                duplicate_eliminate += 1
                # Micro-pausa per evitare il rate-limit di Discord durante l'eliminazione
                await asyncio.sleep(0.3)
            except Exception:
                errori += 1
        else:
            # Se è la prima volta che vediamo questo nome, lo salviamo e teniamo l'emoji
            nomi_visti.add(nome_standard)

    # Resoconto finale
    if duplicate_eliminate == 0:
        await interaction.followup.send("✨ Pulizia completata! Non è stato trovato nessun duplicato, il server è già in ordine.", ephemeral=True)
    else:
        await interaction.followup.send(
            f"🧹 **Pulizia completata con successo!**\n"
            f"🗑️ Emoji duplicate eliminate: **{duplicate_eliminate}**\n"
            f"💎 Emoji uniche salvate e rimaste: **{len(nomi_visti)}**\n"
            f"⚠️ Errori durante l'eliminazione: **{errori}**", 
            ephemeral=True
        )

# ==========================================
# COMANDO 2: ELIMINA TUTTE LE EMOJI
# ==========================================
@client.tree.command(name="elimina_tutte_emoji", description="⚠️ CANCELLA TUTTE LE EMOJI DA QUESTO SERVER. Richiede permessi di Amministratore.")
async def elimina_tutte_emoji(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    if not interaction.user.guild_permissions.administrator:
        await interaction.followup.send("❌ Errore: Questo comando distruttivo può essere eseguito solo da un Amministratore.", ephemeral=True)
        return

    guild = interaction.guild
    emojis_da_eliminare = guild.emojis

    if not emojis_da_eliminare:
        await interaction.followup.send("⚠️ Non ci sono emoji da eliminare in questo server.", ephemeral=True)
        return

    totale = len(emojis_da_eliminare)
    await interaction.followup.send(f"🗑️ Trovate {totale} emoji. Inizio l'eliminazione di massa...", ephemeral=True)

    eliminate = 0
    errori = 0

    for emoji in emojis_da_eliminare:
        try:
            await emoji.delete()
            eliminate += 1
            await asyncio.sleep(0.4)
        except Exception:
            errori += 1

    await interaction.followup.send(
        f"✅ Operazione di pulizia completata!\n"
        f"🗑️ Emoji eliminate con successo: {eliminate}/{totale}\n"
        f"⚠️ Errori (es. permessi insufficienti): {errori}", 
        ephemeral=True
    )

# ==========================================
# AVVIO
# ==========================================
if TOKEN:
    keep_alive()
    client.run(TOKEN)
else:
    print("❌ Manca il DISCORD_TOKEN.")
