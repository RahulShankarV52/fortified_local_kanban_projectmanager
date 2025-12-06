# 1. Base Image (Lightweight Python)
FROM python:3.11-slim

# 2. System Dependencies (Required for YARA and Postgres)
RUN apt-get update && apt-get install -y \
    build-essential \
    libyara-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 3. Work Directory
WORKDIR /code

# 4. Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# 5. Copy Application Code
COPY ./app ./app
COPY ./init_db.py .

# 6. Create Uploads Directory (For persistence)
RUN mkdir -p uploads

# 7. Run Command
# We use host 0.0.0.0 so the container is accessible from outside
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
