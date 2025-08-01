Commands to use:

gunicorn --workers 4 --bind 0.0.0.0:5000 --timeout 300 app:app

source venv/bin/activate