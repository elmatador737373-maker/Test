import os
import asyncio
import threading
import requests
from flask import Flask
import discord
from discord import app_commands
from dotenv import load_dotenv

# Carica le variabili d'ambiente (per il token)
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# ======================================================
# 1. CONFIGURAZIONE SERVER FLASK (PER IL KEEP-ALIVE SU RENDER)
# ======================================================
app = Flask('')

@app.route('/')
def home():
    return "Bot Online e Pronto!", 200

def run_flask():
    # Render assegna la porta dinamicamente tramite la variabile PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    # Avvia Flask in un thread separato per non bloccare il bot Discord
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

# ======================================================
# 2. CONFIGURAZIONE BOT DISCORD
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
        # Sincronizza i comandi slash globalmente all'avvio
        await self.tree.sync()
        print(f'✅ Bot correttamente connesso come {self.user}')

client = EmojiCloner()

# ======================================================
# 3. COMANDO: CLONA EMOJI (A BLOCCHI)
# ======================================================
@client.tree.command(name="clona_emoji", description="Copia le emoji a blocchi per evitare blocchi e timeout di Discord.")
@app_commands.describe(
    source_guild_id="L'ID del server da cui vuoi copiare le emoji",
    inizio="Da quale numero di emoji iniziare (es. 1)",
    fine="A quale numero di emoji arrivare (es. 40)"
)
async def clona_emoji(interaction: discord.Interaction, source_guild_id: str, inizio: int, fine: int):
    # Evita il timeout immediato del comando slash (3 secondi)
    await interaction.response.defer(ephemeral=True)

    # Controllo permessi utente
    if not interaction.user.guild_permissions.manage_expressions:
        await interaction.followup.send("❌ Non hai il permesso 'Gestisci espressioni' (emoji) in questo server.", ephemeral=True)
        return

    # Validazione ID Server
    try:
        source_guild = client.get_guild(int(source_guild_id))
    except ValueError:
        await interaction.followup.send("❌ ID server non valido. Inserisci solo numeri.", ephemeral=True)
        return

    if not source_guild:
        await interaction.followup.send("❌ Server sorgente non trovato. Il bot deve essere presente in quel server!", ephemeral=True)
        return

    target_guild = interaction.guild
    tutte_le_emoji = source_guild.emojis

    if not tutte_le_emoji:
        await interaction.followup.send(f"⚠️ Il server `{source_guild.name}` non ha emoji da copiare.", ephemeral=True)
        return

    # Calcolo degli indici per la paginazione
    idx_inizio = max(0, inizio - 1)
    idx_fine = min(len(tutte_le_emoji), fine)
    emojis_to_copy = tutte_le_emoji[idx_inizio:idx_fine]

    if not emojis_to_copy:
        await interaction.followup.send(f"⚠️ Nessuna emoji trovata nell'intervallo {inizio}-{fine}. Il server ha in totale {len(tutte_le_emoji)} emoji.", ephemeral=True)
        return

    await interaction.followup.send(
        f"🔄 Avvio copia del blocco: emoji da {idx_inizio+1} a {idx_fine}.\n"
        f"📦 Elementi da elaborare in questa sessione: {len(emojis_to_copy)} (Totale server: {len(tutte_le_emoji)})", 
        ephemeral=True
    )

    copiate = 0
    errori = 0

    for emoji in emojis_to_copy:
        # Salta se l'emoji con lo stesso nome è già presente nel server di destinazione
        existing = discord.utils.get(target_guild.emojis, name=emoji.name)
        if existing:
            continue

        try:
            response = requests.get(emoji.url)
            if response.status_code == 200:
                await target_guild.create_custom_emoji(name=emoji.name, image=response.content)
                copiate += 1
                # Pausa di sicurezza di 2 secondi tra i caricamenti
                await asyncio.sleep(2)
                
        except discord.RateLimited as e:
            # Gestione dinamica dei rate limit imposti da Discord
            tempo_attesa = e.retry_after
            print(f"⚠️ Rate limit raggiunto. Aspetto {tempo_attesa} secondi...")
            await asyncio.sleep(tempo_attesa)
            
        except discord.HTTPException as e:
            # Errore 30008 = Limite massimo di slot emoji raggiunto nel server di destinazione
            if e.code == 30008: 
                await interaction.followup.send(f"🚨 Slot emoji esauriti sul tuo server! Non puoi aggiungerne altre. (Copiate in questo blocco: {copiate}).", ephemeral=True)
                return
            print(f"Errore HTTP su {emoji.name}: {e}")
            errori += 1
        except Exception as e:
            print(f"Errore generico: {e}")
            errori += 1

    await interaction.followup.send(
        f"✅ Blocco completato!\n"
        f"🔹 Emoji copiate con successo: {copiate}\n"
        f"⚠️ Errori o duplicati saltati: {errori}\n\n"
        f"💡 Se ci sono altre emoji, esegui nuovamente il comando impostando il blocco successivo.", 
        ephemeral=True
    )

# ======================================================
# 4. COMANDO: ELIMINA TUTTE LE EMOJI
# ======================================================
@client.tree.command(name="elimina_tutte_emoji", description="⚠️ CANCELLA TUTTE LE EMOJI DA QUESTO SERVER. Richiede permessi di Amministratore.")
async def elimina_tutte_emoji(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    # Super controllo di sicurezza: solo gli amministratori reali
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
            await asyncio.sleep(0.5)
        except discord.HTTPException as e:
            print(f"Impossibile eliminare l'emoji {emoji.name}: {e}")
            errori += 1

    await interaction.followup.send(
        f"✅ Operazione di pulizia completata!\n"
        f"🗑️ Emoji eliminate: {eliminate}/{totale}\n"
        f"⚠️ Errori (es. permessi del bot insufficienti): {errori}", 
        ephemeral=True
    )

# ======================================================
# 5. AVVIO DEL BOT E DEL SERVER WEB
# ======================================================
if TOKEN:
    # Fa partire Flask sul thread secondario
    keep_alive()
    # Fa partire il bot sul thread principale
    client.run(TOKEN)
else:
    print("❌ Errore critico: DISCORD_TOKEN non configurato o non trovato.")
