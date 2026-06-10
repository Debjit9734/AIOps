def generate_django_dockerfile():
    return """\
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "projectname.wsgi:application"]
"""


def generate_nginx_conf():
    return """\
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://web:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static/ {
        alias /app/static/;
    }
}
"""


def generate_django_compose():
    return """\
version: '3'

services:
  web:
    build: .
    command: gunicorn projectname.wsgi:application --bind 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"

  nginx:
    image: nginx:latest
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - ./static:/app/static
    depends_on:
      - web
"""
