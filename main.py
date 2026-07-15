import os
import asyncio
import threading
import unicodedata
from flask import Flask
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Carica le variabili d'ambiente dal file .env se presente localmente
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
PORT = int(os.getenv("PORT", 8080))

# --- FLASK WEB SERVER ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!", 200

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

# --- FUNZIONE DI CONVERSIONE FONT ---
def convert_to_normal_font(text: str) -> str:
    """
    Prende una stringa e converte SOLO i caratteri appartenenti a font matematici/strani
    nei corrispettivi caratteri standard (A-Z, a-z, 0-9), lasciando intatti simboli,
    emoji, spazi e caratteri speciali come '〃', '▰', '∫', '´'.
    """
    result = []
    for char in text:
        # Applichiamo la normalizzazione NFKD carattere per carattere
        normalized = unicodedata.normalize('NFKD', char)
        
        # Se il carattere normalizzato diventa una lettera standard o un numero, lo usiamo
        if normalized.isalnum():
            result.append(normalized)
        else:
            # Altrimenti manteniamo il carattere originale (emoji, spazi, simboli speciali)
            result.append(char)
            
    return "".join(result)


# --- DISCORD BOT SETUP ---
intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'🤖 Bot Discord connesso come {bot.user}')

# --- COMANDO RUOLI ---
@bot.command()
@commands.has_permissions(manage_roles=True)
async def cambiaruoli(ctx):
    """Rinomina i ruoli convertendo solo il font speciale in font normale, lasciando tutto il resto intatto"""
    await ctx.send("🔄 Avvio la conversione del font dei ruoli... Lascerò invariati simboli, emoji e spazi.")
    
    success_count = 0
    skipped_count = 0
    
    for role in ctx.guild.roles:
        # 1. Salta il ruolo @everyone
        if role.is_default():
            continue
            
        # 2. Ignora i ruoli che contengono il divisore "▰" (come richiesto in precedenza)
        if "▰" in role.name:
            skipped_count += 1
            continue
            
        # 3. Controllo gerarchia (il bot non può modificare ruoli sopra di lui)
        if role >= ctx.guild.me.top_role:
            print(f"Saltato {role.name}: posizione gerarchica superiore o uguale al bot.")
            continue
            
        old_name = role.name
        # Converte solo le lettere "strane" in lettere normali
        new_name = convert_to_normal_font(old_name)
        
        if old_name != new_name:
            try:
                await role.edit(name=new_name)
                success_count += 1
                await asyncio.sleep(1.5)  # Previene i rate limit di Discord
            except Exception as e:
                print(f"Impossibile modificare il ruolo {old_name}: {e}")
                
    await ctx.send(f"✅ Conversione completata!\n🔹 Ruoli con font normalizzato: {success_count}.\n🔸 Ruoli ignorati (contenevano '▰'): {skipped_count}.")


# --- MAIN ---
if __name__ == "__main__":
    if not TOKEN:
        print("❌ ERRORE: DISCORD_TOKEN mancante.")
        exit(1)

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print(f"🌐 Server Flask avviato sulla porta {PORT}")

    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"❌ Errore d'avvio del bot: {e}")
