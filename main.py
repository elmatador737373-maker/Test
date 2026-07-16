import os
import threading
from flask import Flask
import discord
from discord.ext import commands
from discord.ui import Button, View

# ==========================================
# 1. CONFIGURAZIONE FLASK (Keep-Alive per Render)
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "LSPD Bot è online e attivo su Render!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# 2. CONFIGURAZIONE BOT DISCORD & VIEW PERSISTENTI
# ==========================================

class LSPDAdmissionView(View):
    def __init__(self):
        super().__init__(timeout=None)  # Rende la view persistente

    @discord.ui.button(
        label="📩 Apri Richiesta Colloquio", 
        style=discord.ButtonStyle.blurple, 
        custom_id="lspd_ticket_button"
    )
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user

        # Evita che l'interazione vada in timeout
        await interaction.response.defer(ephemeral=True)

        # ID della categoria fornito dall'utente
        CATEGORY_ID = 1524043623551733911
        
        # Recupera la categoria tramite l'ID
        category = guild.get_channel(CATEGORY_ID)
        
        if not isinstance(category, discord.CategoryChannel):
            # Se il bot non trova la categoria (magari l'ID è errato o non ha accesso), risponde con un errore
            await interaction.followup.send(
                "Errore: Categoria dei ticket non trovata. Contatta un amministratore.", 
                ephemeral=True
            )
            return

        channel_name = f"colloquio-{member.name.lower()}"
        
        # Creiamo il canale SENZA definire "overwrites". 
        # Passando la categoria, erediterà in automatico tutti i suoi permessi (Sincronizzazione automatica).
        ticket_channel = await guild.create_text_channel(
            name=channel_name, 
            category=category
        )

        # Embed di benvenuto all'interno del ticket
        welcome_embed = discord.Embed(
            title="🚔 COLLOQUIO RECLUTAMENTO LSPD",
            description=(
                f"Benvenuto {member.mention} all'interno del tuo ticket personale.\n\n"
                "Un membro dell'**Alto Comando** o del reparto **Risorse Umane** si prenderà cura di te a breve.\n\n"
                "**Nel frattempo, scrivi qui sotto le seguenti informazioni:**\n"
                "• Nome e Cognome del tuo personaggio (IC)\n"
                "• Breve descrizione del tuo BG (Background / Storia del personaggio)\n"
                "• Motivazione principale per cui vuoi unirti al dipartimento"
            ),
            color=discord.Color.from_rgb(0, 47, 167)
        )
        
        # Pulsante persistente per chiudere il ticket
        class CloseTicketView(View):
            def __init__(self):
                super().__init__(timeout=None)
            
            @discord.ui.button(
                label="🔒 Chiudi Ticket", 
                style=discord.ButtonStyle.red, 
                custom_id="close_ticket_btn"
            )
            async def close(self, inter: discord.Interaction, btn: discord.ui.Button):
                await inter.response.send_message("Il ticket verrà chiuso a breve...", ephemeral=True)
                await inter.channel.delete()

        # Invia il messaggio di benvenuto nel canale del ticket
        await ticket_channel.send(content=member.mention, embed=welcome_embed, view=CloseTicketView())
        
        # Feedback privato all'utente
        await interaction.followup.send(f"Ticket creato con successo! Vai qui: {ticket_channel.mention}", ephemeral=True)


class LSPDBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(LSPDAdmissionView())
        await self.tree.sync()

bot = LSPDBot()

@bot.event
async def on_ready():
    print(f'Bot LSPD connesso con successo come: {bot.user.name}')

# ==========================================
# 3. COMANDO SLASH PER GENERARE IL PANNELLO COMPLETO
# ==========================================
@bot.tree.command(name="setup_pannello", description="Invia il pannello completo per i colloqui LSPD Vinewood.")
@commands.has_permissions(administrator=True)
async def setup_pannello(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🚔 DIPARTIMENTO DI POLIZIA DI LOS SANTOS",
        description=(
            "### 🏛️ Divisione Vinewood — Ufficio Reclutamento e Risorse Umane\n\n"
            "Benvenuto nel portale ufficiale per le richieste di colloquio dell'LSPD di Vinewood. "
            "Se sei qui, significa che vuoi fare il passo successivo per proteggere e servire la nostra comunità.\n\n"
            "---"
        ),
        color=discord.Color.from_rgb(0, 47, 167)
    )
    
    embed.add_field(
        name="📌 REQUISITI MINIMI PRIMA DI APRIRE IL TICKET",
        value=(
            "• **Fedina penale pulita** (o reati minori ampiamente prescritti).\n"
            "• **Patente di guida** in corso di validità.\n"
            "• **Età minima** richiesta dal regolamento cittadino.\n"
            "• Ottima conoscenza del **Codice Penale** e delle procedure base di Roleplay.\n"
            "• Disponibilità a lavorare in team e a rispettare la gerarchia."
        ),
        inline=False
    )
    
    embed.add_field(
        name="📝 COSA PREPARARE PER IL COLLOQUIO",
        value=(
            "1. **Documento d'identità** e Licenze (es. Porto d'armi, se richiesto).\n"
            "2. Il tuo **Curriculum Vitae** in formato testuale o link.\n"
            "3. Una breve presentazione del tuo personaggio (Backstory e motivazioni)."
        ),
        inline=False
    )
    
    embed.add_field(
        name="⏱️ COME FUNZIONA IL PROCESSO",
        value=(
            "• **Fase 1:** Clicca sul pulsante qui sotto per aprire il tuo ticket privato.\n"
            "• **Fase 2:** Compila il modulo automatico che ti verrà fornito dal bot.\n"
            "• **Fase 3:** Un Reclutatore o un Membro dell'Alto Comando prenderà in carico la tua richiesta ed fisserà una data per il colloquio orale."
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚠️ NOTA BENE",
        value="I ticket aperti per scherzo, senza i requisiti o lasciati inattivi per più di 24 ore verranno chiusi automaticamente e potrebbero compromettere future candidature.",
        inline=False
    )
    
    embed.set_footer(text="Scegli la tua strada. Entra nel corpo. Proteggi Vinewood. | Premi il bottone qui sotto")

    await interaction.response.send_message("Pannello completo generato con successo!", ephemeral=True)
    await interaction.channel.send(embed=embed, view=LSPDAdmissionView())

# ==========================================
# 4. AVVIO IN PARALLELO
# ==========================================
if __name__ == "__main__":
    t = threading.Thread(target=run_flask)
    t.start()
    
    token = os.environ.get("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("ERRORE CRITICO: La variabile d'ambiente 'DISCORD_TOKEN' non è impostata.")
