FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update \
    && apt-get install -y libpq-dev gcc curl build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install pip dependencies from the server subfolder
COPY server/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy only the server directory into the container for the Django app
COPY server/ /app/

EXPOSE 8000

CMD ["/bin/sh", "/app/entrypoint.sh", "gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]
