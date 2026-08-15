release: python manage.py migrate --noinput && python manage.py ensure_admin
web: python manage.py collectstatic --noinput && COMPRESS_OFFLINE=true python manage.py compress --force && COMPRESS_OFFLINE=true gunicorn giftme.wsgi --bind 0.0.0.0:$PORT
