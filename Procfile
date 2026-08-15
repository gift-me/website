release: python manage.py migrate --noinput && python manage.py ensure_admin
web: python manage.py collectstatic --noinput && python manage.py compress --force && gunicorn giftme.wsgi --bind 0.0.0.0:$PORT
