FROM python:3.12-slim
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libpq-dev \
    gcc \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*
ENV PYTHONDONTWRITEBYTECODE 1

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/


EXPOSE 9000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
