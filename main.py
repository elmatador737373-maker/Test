import os
import asyncio
import threading
import unicodedata
import re
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

# --- MAPPE DI CONVERSIONE UNICODE (Mathematical Italic) ---
ITALIC_UPPER = {
    'A': '𝐴', 'B': '𝐵', 'C': '𝐶', 'D': '𝐷', 'E': '𝐸', 'F': '𝐹', 'G': '𝐺', 'H': '𝐻', 'I': '𝐼', 'J': '𝐽',
    'K': '𝐾', 'L': '𝐿', 'M': '𝑀', 'N': '𝑁', 'O': '𝑂', 'P': '𝑃', 'Q': '𝑄', 'R': '𝑅', 'S': '𝑆', 'T': '𝑇',
    'U': '𝑈', 'V': '𝑉', 'W': '𝑊', 'X': '𝑋', 'Y': '𝑌', 'Z': '𝑍'
}

ITALIC_LOWER = {
    'a': '𝑎', 'b': '𝑏', 'c': '𝑐', 'd': '𝑑', 'e': '𝑒', 'f': '𝑓', 'g': '𝑔', 'h': 'ℎ', 'i': '𝑖', 'j': '𝑗',
    'k': '𝑘', 'l': '𝑙', 'm': '𝑚', 'n': '𝑛', 'o': '𝑜', 'p': '𝑝', 'q': '𝓆', 'r': '𝑟', 's': '𝑠', 't': '𝑡',
    'u': '𝑢', 'v': '𝑣', 'w': '𝑤', 'x': '𝑥', 'y': '𝑦', 'z': '𝑧'
}

def convert_to_italic(text: str) -> str:
    """Converte una stringa di testo normale in Mathematical Italic."""
    result = []
    for char in text:
        if char in ITALIC_UPPER:
            result.append(ITALIC_UPPER[char])
        elif char in ITALIC_LOWER:
            result.append(ITALIC_LOWER[char])
        else:
            result.append(char)
    return "".join(result)

def clean_to_normal_text(text: str) -> str:
    """Converte i caratteri unicode complessi in testo normale A-Z, a-z, 0-9."""
    normalized = unicodedata.normalize('NFKD', text)
    # Rimuove accenti e caratteri decorativi complessi, tiene lettere, numeri e spazi/trattini base
    cleaned = "".join([c for c in normalized if c.isalnum() or c in " -_"])
    return cleaned

def transform_channel_name(old_name: str) -> str:
    """
    Estrae le emoji dal canale, pulisce il testo circostante,
    lo converte nel font Italic e formatta il canale come: [Emoji]∫[Testo1]´[Testo2]
    """
    # 1. Regex per catturare emoji di Discord <:nome:id> o a:nome:id (animate)
    discord_emoji_pattern = re.compile(r'(<a?:\w+:\d+>)')
    
    # Trova eventuali emoji custom di Discord
    discord_emojis = discord_emoji_pattern.findall(old_name)
    
    # Rimuove le emoji custom temporaneamente dal testo per non rovinare la conversione
    text_without_custom = discord_emoji_pattern.sub('', old_name)
    
    # 2. Estrae le emoji Unicode standard (es. 📣, 💬, 🔒) e separa il testo pulito
    standard_emojis = []
    pure_chars = []
    
    for char in text_without_custom:
        # Controlla se il carattere è un'emoji standard o un simbolo speciale non testuale
        if unicodedata.category(char) in ('So', 'Cn') and char not in "∫´":
            standard_emojis.append(char)
        else:
            pure_chars.append(char)
            
    # Unisce tutte le emoji rilevate (daremo la priorità a posizionarle all'inizio)
    all_emojis = "".join(discord_emojis + standard_emojis).strip()
    
    # Ricostruisce il testo originale senza emoji
    remaining_text = "".join(pure_chars).strip()
    
    # 3. Pulisce il testo dal vecchio font strano e lo riporta a caratteri normali
    normal_text = clean_to_normal_text(remaining_text)
    
    # Splitta il testo per gestire i canali composti (es: "annunci staff" o "annunci-staff")
    # Sostituiamo trattini e underscore con spazi per la separazione
    words_split = normal_text.replace('-', ' ').replace('_', ' ').split()
    
    if not words_split:
        return old_name  # Salta se non c'è testo convertibile
        
    # Applica la conversione in Italic su ogni singola parola capitalizzandola (es: "Annunci", "Staff")
    italic_words = [convert_to_italic(word.capitalize()) for word in words_split]
    
    # 4. Ricostruisce il nome usando i separatori speciali richiesti
    # Se ci sono più parole usa il carattere ´ come separatore, altrimenti le unisce direttamente
    formatted_text = "´".join(italic_words)
    
    # Se c'era un'emoji nel canale originario, la aggancia all'inizio seguita da "∫"
    if all_emojis:
        new_name = f"{all_emojis}∫{formatted_text}"
    else:
        # Se non c'erano emoji, usa solo il testo convertito
        new_name = formatted_text
        
    return new_name

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
    """Comando per avviare la conversione di tutti i canali nel nuovo formato"""
    await ctx.send("🔄 Rilevamento canali e conversione in corso... Rimani in attesa.")
    
    success_count = 0
    for channel in ctx.guild.channels:
        if isinstance(channel, discord.CategoryChannel):
            continue  # Ignora le categorie
            
        old_name = channel.name
        new_name = transform_channel_name(old_name)
        
        if old_name != new_name:
            try:
                await channel.edit(name=new_name)
                success_count += 1
                await asyncio.sleep(1.5)  # Delay per evitare il rate limit di Discord
            except Exception as e:
                print(f"Errore nel rinominare il canale {old_name}: {e}")
                
    await ctx.send(f"✅ Conversione completata! {success_count} canali formattati con successo nel nuovo stile (es: 📣∫𝐴𝑛𝑛𝑢𝑛𝑐𝑖´𝑆𝑡𝑎𝑓𝑓).")

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
