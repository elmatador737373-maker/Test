# Usa un'immagine Python ufficiale stabile
FROM python:3.10-slim

# Installa FFmpeg e le dipendenze per compilare PyNaCl (fondamentale per l'audio)
RUN apt-get update && \
    apt-get install -y ffmpeg gcc python3-dev libffi-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Imposta la cartella di lavoro
WORKDIR /app

# Copia i requisiti e installali
# Installiamo prima i requisiti per sfruttare la cache di Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia tutto il resto del codice nel container
COPY . .

# Comando per avviare il bot
# Assicurati che il file principale sia main.py
CMD ["python", "main.py"]
