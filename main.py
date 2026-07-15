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

# --- FLASK WEB SERVER (Per mantenere vivo il servizio su Render) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!", 200

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

# --- MAPPE DI CONVERSIONE UNICODE (Mathematical Italic) ---
# Mappa di conversione per caratteri standard
ITALIC_UPPER = {
    'A': '𝐴', 'B': '𝐵', 'C': '𝐶', 'D': '𝐷', 'E': '𝐸', 'F': '𝐹', 'G': '𝐺', 'H': '𝐻', 'I': '𝐼', 'J': '𝐽',
    'K': '𝐾', 'L': '𝐿', 'M': '𝑀', 'N': '𝑁', 'O': '𝑂', 'P': '𝑃', 'Q': '𝑄', 'R': '𝑅', 'S': '𝑆', 'T': '𝑇',
    'U': '𝑈', 'V': '𝑉', 'W': '𝑊', 'X': '𝑋', 'Y': '𝑌', 'Z': '𝑍'
}

# In Unicode Math Italic, la 'h' normale usa il carattere standard U+210E (ℎ)
ITALIC_LOWER = {
    'a': '𝑎', 'b': '𝑏', 'c': '𝑐', 'd': '𝑑', 'e': '𝑒', 'f': '𝑓', 'g': '𝑔', 'h': 'ℎ', 'i': '𝑖', 'j': '𝑗',
    'k': '𝑘', 'l': '𝑙', 'm': '𝑚', 'n': '𝑛', 'o': '𝑜', 'p': '𝑝', 'q': '𝑞', 'r': '𝑟', 's': '𝑠', 't': '𝑡',
    'u': '𝑢', 'v': '𝑣', 'w': '𝑤', 'x': '𝑥', 'y': '𝑦', 'z': '𝑧'
}

def clean_to_normal_text(text: str) -> str:
    """
    Rimuove i font Unicode speciali e li converte in testo standard A-Z, a-z.
    Sfrutta la normalizzazione NFKD di Unicode per 'smontare' i font matematici complessi.
    """
    normalized = unicodedata.normalize('NFKD', text)
    # Rimuove i modificatori mantenendo solo caratteri alfanumerici, spazi, trattini e underscore
    cleaned = "".join([c for c in normalized if c.isalnum() or c in " -_"])
    return cleaned

def convert_to_italic(text: str) -> str:
    """
    Converte il testo normale in Mathematical Italic.
    """
    result = []
    for char in text:
        if char in ITALIC_UPPER:
            result.append(ITALIC_UPPER[char])
        elif char in ITALIC_LOWER:
            result.append(ITALIC_LOWER[char])
        else:
            result.append(char)  # Mantiene numeri, trattini, spazi o emoji invariati
    return "".join(result)


# --- DISCORD BOT SETUP ---
intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'🤖 Bot Discord connesso come {bot.user}')

@bot.command()
@commands.has_permissions(manage_channels=True)
async def cambiafont(ctx):
    """Comando per avviare la conversione di tutti i canali del server"""
    await ctx.send("🔄 Avvio la conversione dei canali... Potrebbe richiedere del tempo per via dei limiti di frequenza (rate limit) di Discord.")
    
    success_count = 0
    for channel in ctx.guild.channels:
        # Ignoriamo le categorie per mantenere pulito il layout, rimuovi questo blocco se vuoi includerle
        if isinstance(channel, discord.CategoryChannel):
            continue
            
        old_name = channel.name
        
        # 1. Pulizia dal vecchio font Unicode al testo normale
        normal_name = clean_to_normal_text(old_name)
        
        # 2. Conversione nel nuovo font desiderato
        new_name = convert_to_italic(normal_name)
        
        if old_name != new_name:
            try:
                await channel.edit(name=new_name)
                success_count += 1
                await asyncio.sleep(1.5)  # Breve pausa per prevenire rate limit aggressivi
            except Exception as e:
                print(f"Impossibile rinominare il canale {old_name}: {e}")
                
    await ctx.send(f"✅ Conversione completata! Aggiornati {success_count} canali in stile *Mathematical Italic*.")


# --- MAIN EXECUTION ---
if __name__ == "__main__":
    if not TOKEN:
        print("❌ ERRORE: La variabile d'ambiente DISCORD_TOKEN non è configurata.")
        exit(1)

    # Avvia Flask in un thread separato
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print(f"🌐 Server Flask avviato sulla porta {PORT}")

    # Avvia il bot di Discord sul thread principale
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"❌ Errore durante l'avvio del bot Discord: {e}")
