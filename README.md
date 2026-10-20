# Заметки — Flask + SQLite

## Запуск

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
python app.py
```

Открыть http://localhost:3000

## Продакшен

```bash
pip install waitress
waitress-serve --port=3000 app:app
```