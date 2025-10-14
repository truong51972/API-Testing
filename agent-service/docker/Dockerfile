FROM python:3.12.11-slim

# fix CVE-2025-6020
RUN apt-get update \
    && apt-get install -y --only-upgrade libpam-modules libpam-modules-bin libpam-runtime libpam0g \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y \
    pkg-config \
    default-libmysqlclient-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app

RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

EXPOSE 8000

CMD ["gunicorn", "--config", "gunicorn.conf.py", "main:app"]