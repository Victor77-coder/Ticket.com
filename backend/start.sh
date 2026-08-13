#!/usr/bin/env bash
# Plano free não tem preDeployCommand.
#
# A porta TEM que abrir antes do sync do TMDb: o health check do Render
# mata o deploy se o gunicorn ainda não estiver escutando. Por isso o
# bootstrap roda com o servidor já no ar — e não derruba o processo se o
# TMDb falhar (a chave pode ter ficado de fora na criação do Blueprint).
set -euo pipefail

python manage.py migrate --noinput
python manage.py collectstatic --noinput

gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-1}" \
  --timeout 90 &
GUNICORN_PID=$!

if ! python manage.py bootstrap_demo; then
  echo "bootstrap_demo falhou — o serviço continua no ar sem o cenário de demo."
fi

wait "$GUNICORN_PID"
