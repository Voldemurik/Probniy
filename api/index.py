"""Точка входа для Vercel: одна serverless-функция, внутри — наше FastAPI-приложение.

Vercel сам находит переменную `app` (ASGI-приложение) в файле api/index.py.
Код бэкенда живёт в backend/app и не дублируется — просто добавляем папку backend в sys.path.
Маршруты /api/v1/*, /docs, /openapi.json направляются сюда правилами rewrites в vercel.json;
сама страница ассистента (app.html) отдаётся Vercel как статический файл из сборки Vite.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND = os.path.join(ROOT, "backend")
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from app.main import app  # noqa: E402  (ASGI-приложение, которое ищет Vercel)
