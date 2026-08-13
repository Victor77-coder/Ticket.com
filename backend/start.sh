#!/usr/bin/env bash
# Plano free não tem preDeployCommand: migrate, estáticos e seed rodam aqui,
# antes do gunicorn. bootstrap_demo é idempotente — na segunda subida (e a
# cada acordar do free tier) não apaga a grade.
set -euo pipefail

python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py bootstrap_demo

exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --timeout 90
