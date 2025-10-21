# Etap 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Instalacja zależności
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Etap 2: Runtime
FROM python:3.11-slim

# Zmienne środowiskowe
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/root/.local/bin:$PATH

WORKDIR /app

# Kopiowanie zależności z buildera
COPY --from=builder /root/.local /root/.local

# Kopiowanie aplikacji
COPY app.py .
COPY test_app.py .

# Tworzenie użytkownika bez uprawnień root
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Expose port
EXPOSE 5000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# Uruchomienie aplikacji
CMD ["python", "app.py"]
