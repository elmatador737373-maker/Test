# Usa un'immagine Python ufficiale sottile
FROM python:3.10-slim

# Installa FFmpeg e le dipendenze di sistema necessarie
# ffmpeg è fondamentale per trasmettere l'audio su Discord
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Imposta la cartella di lavoro nel container
WORKDIR /app

# Copia il file dei requisiti
COPY requirements.txt .

# Installa le librerie Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia tutto il resto del codice
COPY . .

# Comando per avviare il bot
# Assicurati che il tuo file principale si chiami main.py
CMD ["python", "main.py"]
