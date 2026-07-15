#!/usr/bin/env bash
set -o errexit

python manage.py migrate --noinput
gunicorn aiops_project.wsgi:application --bind "0.0.0.0:${PORT:-8000}"
