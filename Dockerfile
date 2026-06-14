FROM python:3.11-slim

# Install system deps: ttfautohint + build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    ttfautohint \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY scripts/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt flask

# Copy scripts & app
COPY scripts/kobofix.py scripts/kobofix.py
COPY scripts/fixvn.py   scripts/fixvn.py
COPY app.py             app.py
COPY templates/         templates/

# Create ots-sanitize wrapper (required by kobofix)
RUN printf '#!/bin/sh\npython3 -m ots "$@"\n' > /usr/local/bin/ots-sanitize \
    && chmod +x /usr/local/bin/ots-sanitize

EXPOSE 5000

CMD ["python3", "app.py"]
