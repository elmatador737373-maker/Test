import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Carica le variabili d'ambiente dal file .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Configurazione delle intenzioni (Intents) obbligatorie
intents = discord.Intents.default()
intents.guilds = True
intents.guild_messages = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Definizione dei ruoli (dal più basso al più alto per l'ordinamento nativo di Discord)
ROLES_TO_CREATE = [
    {"name": "🔰 Recruit / Recluta", "color": discord.Color.from_rgb(128, 128, 128)},
    
    {"name": "✈️ A1C | Airman First Class", "color": discord.Color.from_rgb(70, 130, 180)},
    {"name": "🪖 PFC | Private First Class", "color": discord.Color.from_rgb(75, 83, 32)},
    
    {"name": "🚁 MSgt | Master Sergeant", "color": discord.Color.from_rgb(70, 130, 180)},
    {"name": "🎯 SFC | Sergeant First Class", "color": discord.Color.from_rgb(75, 83, 32)},
    
    {"name": "🚀 CPT | Captain (Air Force)", "color": discord.Color.from_rgb(30, 144, 255)},
    {"name": "⚡ CPT | Captain (Army)", "color": discord.Color.from_rgb(107, 142, 35)},
    
    {"name": "🦅 COL | Colonel (Air Force)", "color": discord.Color.from_rgb(25, 25, 112)},
    {"name": "🦅 COL | Colonel (Army)", "color": discord.Color.from_rgb(34, 139, 34)},
    
    {"name": "🎖️ GEN | General (Air Force)", "color": discord.Color.from_rgb(255, 215, 0)},
    {"name": "🎖️ GEN | General (Army)", "color": discord.Color.from_rgb(212, 175, 55)}
]

@bot.event
async def on_ready():
    print(f"🤖 Bot connesso con successo come {bot.user}")

@bot.command()
@commands.has_permissions(administrator=True)
async def crearuoli(ctx):
    await ctx.send("⏳ Inizio la creazione dei ruoli militari in ordine gerarchico...")
    
    for role_data in ROLES_TO_CREATE:
        try:
            new_role = await ctx.guild.create_role(
                name=role_data["name"], 
                color=role_data["color"], 
                hoist=True
            )
            await ctx.send(f"✅ Creato ruolo: {new_role.name}")
        except Exception as e:
            await ctx.send(f"❌ Errore nella creazione di {role_data['name']}: {e}")
            
    await ctx.send("🎯 **Fatto!** Tutti i ruoli sono pronti e ordinati dal più alto al più basso.")

# Controllo di sicurezza sul Token prima di avviare
if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ ERRORE: DISCORD_TOKEN non trovato nel file .env. Verifica la configurazione.")
