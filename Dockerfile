# Use lightweight python image (CPU only)
FROM python:3.11-slim

WORKDIR /app

# Prevent Python cache files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better caching)
COPY requirements.txt .

# Install Python packages (CPU only)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Open ports
EXPOSE 8000
EXPOSE 8501

# Run backend + UI
CMD bash -c "uvicorn main:app --host 0.0.0.0 --port 8000 & streamlit run chat_ui.py --server.port 8501 --server.address 0.0.0.0"