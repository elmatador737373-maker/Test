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
# GESTIONE BENVENUTO AUTOMATICO (LSPD)
# ==========================================
@bot.event
async def on_member_join(member: discord.Member):
    # ID del canale di benvenuto fornito
    CANALE_BENVENUTO_ID = 1524043683110981724
    guild = member.guild
    
    # Recupera il canale di benvenuto
    welcome_channel = guild.get_channel(CANALE_BENVENUTO_ID)
    
    if welcome_channel is None:
        print(f"Attenzione: Non ho trovato il canale di benvenuto con ID {CANALE_BENVENUTO_ID}")
        return

    # Creazione di un Embed di benvenuto di alto impatto visivo
    embed = discord.Embed(
        title="🚔 BEN_VENUTO NEL SERVIZIO — LSPD VINEWOOD 🚔",
        description=(
            f"Salute, {member.mention}!\n\n"
            "Sei appena entrato nel server ufficiale del **Dipartimento di Polizia di Los Santos — Divisione di Vinewood**.\n"
            "Qui potrai intraprendere la tua carriera per garantire l'ordine, la sicurezza e la giustizia nella nostra città.\n\n"
            "---"
        ),
        color=discord.Color.from_rgb(0, 47, 167)  # Blu Polizia
    )
    
    # Sezione dei primi passi per l'utente
    embed.add_field(
        name="📌 DA DOVE INIZIARE?",
        value=(
            "• **Leggi il Regolamento:** Assicurati di conoscere le regole interne per evitare sanzioni.\n"
            "• **Arruolati nel corpo:** Se desideri unirti alle nostre forze, leggi i requisiti e apri una richiesta colloquio usando i nostri canali dedicati!\n"
            "• **Rispetta la Gerarchia:** Il rispetto reciproco e la disciplina sono alla base del nostro dipartimento."
        ),
        inline=False
    )
    
    # Statistiche rapide sull'utente e sul server
    embed.add_field(
        name="📊 INFO AGGUNTIVE",
        value=(
            f"• **Account creato il:** <t:{int(member.created_at.timestamp())}:D>\n"
            f"• **Sei il membro numero:** `{len(guild.members)}`"
        ),
        inline=False
    )
    
    # Foto profilo dell'utente come miniatura nell'angolo dell'embed
    embed.set_thumbnail(url=member.display_avatar.url)
    

    embed.set_footer(text="Ufficio Accoglienza e Pubbliche Relazioni LSPD | Vinewood")

    # Invia l'embed menzionando l'utente per attirare la sua attenzione
    await welcome_channel.send(content=f"Benvenuto {member.mention}! 👮‍♂️", embed=embed)

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

# COMANDO: Invio di un annuncio personalizzato
@bot.tree.command(name="annuncio", description="Invia un annuncio formattato in questo canale.")
@commands.has_permissions(administrator=True)
@discord.app_commands.describe(
    titolo="Il titolo principale dell'annuncio",
    messaggio="Il testo/contenuto dell'annuncio (usa \\n per andare a capo)"
)
async def annuncio(interaction: discord.Interaction, titolo: str, messaggio: str):
    # Sostituisce eventuali \n digitati dall'utente in veri e propri a capo nel messaggio
    messaggio_formattato = messaggio.replace("\\n", "\n")

    # Creiamo l'embed dell'annuncio con lo stile coordinato dell'LSPD
    embed = discord.Embed(
        title=f"📢 {titolo.upper()}",
        description=messaggio_formattato,
        color=discord.Color.from_rgb(0, 47, 167)  # Blu Polizia
    )
    embed.set_footer(text=f"Dipartimento di Polizia di Los Santos | Vinewood")
    
    # Risposta di conferma effimera (invisibile agli altri utenti)
    await interaction.response.send_message("Annuncio inviato con successo!", ephemeral=True)
    
    # Invia l'annuncio nel canale in cui è stato eseguito il comando
    await interaction.channel.send(embed=embed)

# COMANDO: Esito del Colloquio (Assegnazione Ruolo)
@bot.tree.command(name="esito_colloquio", description="Comunica l'esito del colloquio di un candidato.")
@discord.app_commands.describe(
    utente="Il candidato che ha sostenuto il colloquio",
    esito="Seleziona se il candidato è passato o meno",
    motivazione="Specifica le motivazioni dell'esito (opzionale)"
)
@discord.app_commands.choices(esito=[
    discord.app_commands.Choice(name="🟢 Approvato (Passato)", value="approvato"),
    discord.app_commands.Choice(name="🔴 Bocciato (Non Passato)", value="bocciato")
])
async def esito_colloquio(interaction: discord.Interaction, utente: discord.Member, esito: discord.app_commands.Choice[str], motivazione: str = None):
    # ID del ruolo richiesto per poter eseguire il comando (Staff/Esaminatori)
    RUOLO_STAFF_ID = 1524043601880023090
    
    # Verifica se chi esegue il comando ha il ruolo richiesto
    has_permission = any(role.id == RUOLO_STAFF_ID for role in interaction.user.roles)
    
    if not has_permission:
        await interaction.response.send_message(
            "❌ Non hai i permessi necessari (ruolo richiesto non posseduto) per utilizzare questo comando.", 
            ephemeral=True
        )
        return

    # Ritardiamo la risposta per evitare timeout durante l'aggiunta dei ruoli e l'invio nei canali
    await interaction.response.defer(ephemeral=True)
    
    guild = interaction.guild
    
    # ID del canale dove inviare l'embed del verbale/esito
    CANALE_LOG_ID = 1524043697421811772
    log_channel = guild.get_channel(CANALE_LOG_ID)
    
    if log_channel is None:
        await interaction.followup.send(
            f"⚠️ Errore: Non ho trovato il canale di output con ID `{CANALE_LOG_ID}`.",
            ephemeral=True
        )
        return

    # ID dei 3 ruoli da assegnare in caso di promozione (Approvato)
    RUOLI_PROMOZIONE_IDS = [
        1524043584448364685,
        1524043603297439964,
        1524043604467646597
    ]
    
    testo_motivazione = motivazione if motivazione else "Nessuna motivazione aggiuntiva fornita."

    if esito.value == "approvato":
        ruoli_da_aggiungere = []
        for r_id in RUOLI_PROMOZIONE_IDS:
            ruolo_obj = guild.get_role(r_id)
            if ruolo_obj:
                ruoli_da_aggiungere.append(ruolo_obj)
            else:
                print(f"Attenzione: Non ho trovato il ruolo con ID {r_id} su Discord.")

        if not ruoli_da_aggiungere:
            await interaction.followup.send(
                "⚠️ Errore: Nessuno dei ruoli di promozione configurati è stato trovato sul server.",
                ephemeral=True
            )
            return

        try:
            # Assegna i molteplici ruoli all'utente promosso
            await utente.add_roles(*ruoli_da_aggiungere)
            
            # Crea l'embed di successo per il canale dei log
            embed = discord.Embed(
                title="🚨 ESITO COLLOQUIO — APPROVATO",
                description=(
                    f"Congratulazioni {utente.mention}!\n\n"
                    "Il tuo colloquio per l'**LSPD di Vinewood** è stato valutato con successo e sei stato arruolato.\n\n"
                    f"**Esaminatore:** {interaction.user.mention}\n"
                    f"**Motivazione/Note:**\n*{testo_motivazione}*\n\n"
                    "Preparati per l'addestramento ufficiale!"
                ),
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=utente.display_avatar.url)
            embed.set_footer(text="Dipartimento di Polizia di Los Santos — Vinewood")
            
            # Invia l'esito ufficiale nel canale dei log designato
            await log_channel.send(content=utente.mention, embed=embed)
            
            # Messaggio di conferma privato all'esaminatore che ha digitato il comando
            await interaction.followup.send(
                f"✅ Esito positivo registrato! Ruoli assegnati e notifica inviata in {log_channel.mention}.", 
                ephemeral=True
            )
            
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Non ho i permessi necessari per assegnare questi ruoli. "
                "Assicurati che il ruolo del mio Bot sia posizionato **più in alto** rispetto ai ruoli da assegnare nella lista dei ruoli del server.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.followup.send(f"Si è verificato un errore: {str(e)}", ephemeral=True)

    else:  # Caso: bocciato
        # Crea l'embed di rifiuto per il canale dei log
        embed = discord.Embed(
            title="🚨 ESITO COLLOQUIO — NON APPROVATO",
            description=(
                f"Gentile {utente.mention},\n\n"
                "Ci dispiace informarti che non hai superato l'ultimo colloquio per l'**LSPD di Vinewood**.\n\n"
                f"**Esaminatore:** {interaction.user.mention}\n"
                f"**Motivazione/Note:**\n*{testo_motivazione}*\n\n"
                "Potrai ripresentare la tua candidatura non appena riapriranno i bandi. "
                "Sfrutta questo tempo per studiare al meglio le procedure!"
            ),
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=utente.display_avatar.url)
        embed.set_footer(text="Dipartimento di Polizia di Los Santos — Vinewood")
        
        # Invia la notifica ufficiale nel canale log
        await log_channel.send(content=utente.mention, embed=embed)
        
        # Conferma privata all'esaminatore
        await interaction.followup.send(
            f"❌ Esito negativo registrato! Notifica inviata in {log_channel.mention}.", 
            ephemeral=True
        )

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
