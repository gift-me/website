release: python manage.py migrate --noinput && python manage.py ensure_admin
web: python manage.py collectstatic --noinput && gunicorn giftme.wsgi --bind 0.0.0.0:$PORT
