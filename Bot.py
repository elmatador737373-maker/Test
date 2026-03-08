import os
import discord
import subprocess
import threading
from flask import Flask
from locust import HttpUser, task

# -------- TOKEN DALLE VARIABILI D'AMBIENTE --------
TOKEN = os.environ.get("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("Devi impostare la variabile d'ambiente DISCORD_TOKEN su Render!")

# -------- LOCUST TEST --------
class SiteUser(HttpUser):

    @task
    def index(self):
        self.client.get("/")

# -------- DISCORD BOT --------
bot = discord.Bot()

@bot.slash_command(name="test", description="Avvia test sul sito")
async def test(ctx, url: str):

    await ctx.respond("Test avviato...")

    subprocess.run([
        "locust",
        "-f", "bot.py",
        "--headless",
        "-u", "20",
        "-r", "5",
        "-t", "20s",
        "-H", url
    ])

    await ctx.followup.send("Test completato")

# -------- SERVER WEB PER UPTIMEROBOT --------
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot attivo"

def run_web():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run_web).start()

# -------- START BOT --------
bot.run(TOKEN)
