web: python manage.py migrate --noinput && python manage.py ensure_admin && python manage.py collectstatic --noinput && gunicorn giftme.wsgi --bind 0.0.0.0:$PORT

