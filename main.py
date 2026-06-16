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
# CONFIGURAZIONE BOT DISCORD ORIGINAL
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
# COMANDO CLONA CON LOG PROGRESSIVI EPHEMERAL
# ==========================================
@client.tree.command(name="clona_emoji", description="Copia le emoji mostrando l'avanzamento solo a te ogni 10 elementi.")
@app_commands.describe(source_guild_id="L'ID del server da cui vuoi copiare le emoji")
async def clona_emoji(interaction: discord.Interaction, source_guild_id: str):
    # Risposta iniziale Ephemeral (visibile solo a chi fa il comando)
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
        await interaction.followup.send("❌ Server sorgente non trovato. Il bot è presente anche lì?", ephemeral=True)
        return

    emojis_to_copy = source_guild.emojis
    target_guild = interaction.guild
    totale_emoji = len(emojis_to_copy)

    if not emojis_to_copy:
        await interaction.followup.send(f"⚠️ Il server `{source_guild.name}` non ha emoji.", ephemeral=True)
        return

    # Salviamo il messaggio iniziale in una variabile per poterlo modificare in seguito
    status_message = await interaction.followup.send(
        f"🔄 **Clonazione avviata!**\n"
        f"📦 Server sorgente: `{source_guild.name}`\n"
        f"🔮 Totale emoji da verificare: **{totale_emoji}**\n"
        f"⏳ Preparazione del processo in corso...", 
        ephemeral=True
    )

    copiate = 0
    errori = 0
    gia_presenti = 0
    analizzate = 0
    
    lista_log_recenti = []

    for emoji in emojis_to_copy:
        analizzate += 1
        existing = discord.utils.get(target_guild.emojis, name=emoji.name)
        if existing:
            gia_presenti += 1
            lista_log_recenti.append(f"🔁 Saltata `{emoji.name}` (Già presente)")
        else:
            try:
                response = requests.get(emoji.url)
                if response.status_code == 200:
                    await target_guild.create_custom_emoji(name=emoji.name, image=response.content)
                    copiate += 1
                    lista_log_recenti.append(f"✅ Copiata: `{emoji.name}`")
                    await asyncio.sleep(1.5)
                    
            except discord.RateLimited as e:
                lista_log_recenti.append(f"⚠️ Rate limit: attesa di {int(e.retry_after)}s...")
                await asyncio.sleep(e.retry_after)
                
            except discord.HTTPException as e:
                if e.code == 30008: 
                    lista_log_recenti.append("🚨 Spazio esaurito sul server destinazione!")
                    break
                lista_log_recenti.append(f"❌ Errore Discord su `{emoji.name}` (Codice {e.code})")
                errori += 1
            except Exception:
                lista_log_recenti.append(f"❌ Errore caricamento `{emoji.name}`")
                errori += 1

        # Manteniamo solo gli ultimi 8 log storici nel testo per non superare i limiti di caratteri di Discord
        if len(lista_log_recenti) > 8:
            lista_log_recenti.pop(0)

        # AGGIORNAMENTO OGNI 10 EMOJI ANALIZZATE (o all'ultima emoji del server)
        if analizzate % 10 == 0 or analizzate == totale_emoji:
            testo_cronologia = "\n".join(lista_log_recenti)
            
            # Calcolo di una barra di caricamento visiva elementare
            percentuale = int((analizzate / totale_emoji) * 100)
            quadratini = int(percentuale / 10)
            barra = "🟩" * quadratini + "⬛" * (10 - quadratini)

            # Modifica il messaggio ephemeral esistente senza inviarne di nuovi
            await status_message.edit(content=f"🔄 **Clonazione in corso...**\n"
                                              f"📊 Avanzamento: {barra} **{percentuale}%** ({analizzate}/{totale_emoji})\n\n"
                                              f"🔹 Nuove aggiunte: **{copiate}**\n"
                                              f"🔁 Già presenti (saltate): **{gia_presenti}**\n"
                                              f"⚠️ Errori riscontrati: **{errori}**\n\n"
                                              f"📋 **Ultime azioni:**\n"
                                              f"```text\n{testo_cronologia}\n```")

    # REPORT FINALE COMPLETO (Modifica finale del messaggio al termine del ciclo)
    await status_message.edit(content=f"🏆 **Clonazione Completata!**\n"
                                      f"📊 Stato finale: **100%** ({totale_emoji}/{totale_emoji})\n\n"
                                      f"✨ Nuove emoji aggiunte: **{copiate}**\n"
                                      f"🔁 Già presenti nel server: **{gia_presenti}**\n"
                                      f"⚠️ Errori totali: **{errori}**\n\n"
                                      f"💡 *Se l'operazione si è interrotta a metà a causa del timeout di 3 minuti di Discord, ti basta rieseguire lo stesso comando. Il bot salterà istantaneamente quelle già copiate e riprenderà da dove si era fermato!*")

if TOKEN:
    keep_alive()
    client.run(TOKEN)
else:
    print("❌ Manca il DISCORD_TOKEN.")
