# ИИще · Подписки-сканер

ИИ-ассистент в виде чата: пользователь загружает банковскую выписку (CSV или PDF), а через 10–15 секунд получает
разбор расходов, список подписок с датами списаний и стоимостью, и персональные рекомендации — что отменить и сколько
это сэкономит за год. Анализ выполняет нейросеть **GigaChat** (Сбер) через официальный API.

Проект команды **ИИще** на хакатоне **ТОП ИИ 2026** (ИРИТ-РТФ УрФУ), кейс 4 «Подписки-сканер», партнёр — Сбер.

- Репозиторий: https://gitverse.ru/iische/probniy
- Сайт (Vercel): https://website-final-ei2pk4hz1-ii-sche.vercel.app — актуальный адрес production-деплоя смотрите в панели Vercel проекта `website-final`
- Проверка состояния бэкенда: `https://<домен>/api/v1/health?deep=1`

---

## Как это выглядит для пользователя

1. Открывает сайт — экран чата с ассистентом.
2. Нажимает «Загрузить файл», выбирает выписку по карте (CSV или PDF) и нажимает «Отправить».
3. Через 10–15 секунд ассистент отвечает тремя сообщениями:
   - **Расходы** — общий расход за период и разбивка по типам: подписки, переводы (в том числе себе), остальные расходы одной суммой.
   - **Подписки** — карточка на каждую: название, цена подписки, последнее списание, ожидаемое следующее списание,
     уже потрачено за период, экономия за год при отказе, как отменить.
   - **Рекомендации по подпискам** — 3–5 пунктов от GigaChat: общие («всеми ли сервисами вы пользуетесь?») и конкретные
     («за 6 месяцев вы потратили 5 994 ₽ на VK Play — играете ли вы постоянно?»).
4. Кнопки быстрых сценариев: «Мои активные подписки», «Расходы за 1 / 3 / 6 / 12 месяцев» (пересчёт за другой период),
   «Рекомендации», «Скачать отчёт .txt».

Файл не сохраняется на сервере — живёт только во время запроса. В GigaChat уходят названия мерчантов, суммы, даты и
категория банка — без ФИО, номеров карт и счетов.

## Как это работает

```
выписка (CSV / PDF)
   │  parser.py — разбор файла (кодировка и разделитель определяются сами), только выполненные списания
   ▼
транзакции
   │  naming.py — нормализация названий + словарь алиасов: YANDEX.PLUS / Yandex Plus / ЯНДЕКС ПЛЮС → «Яндекс Плюс»,
   │              CLOUD.MAIL.RU / MAIL.RU CLOUD / VK CLOUD → «Cloud Mail.ru»; для незнакомых названий — эмбеддинги GigaChat (опционально)
   ▼
кластеры расходов
   │  ai.py — GigaChat: категория из 12, признак подписки, совместимость с картами МИР, инструкция по отмене;
   │          ответ проверяется по схеме (pydantic); при недоступности API — классификация по правилам (словари, MCC-коды)
   ▼
   │  detector.py — периодичность (неделя / 2 недели / месяц / квартал), алерты: пробный период, рост или снижение цены
   ▼
JSON для интерфейса: расходы по типам + карточки подписок
   │  ai.py — GigaChat: рекомендации только по подпискам (общие + конкретные); без API — рекомендации по правилам
   ▼
три сообщения в чате (+ TXT-отчёт по кнопке)
```

Категории расходов: `subscription`, `recurring_payment`, `transfer_out`, `transfer_in`, `household_food`,
`household_transport`, `household_cafe`, `household_pharmacy`, `marketplace`, `cash_withdrawal`, `entertainment`, `other`.
Рассрочки за обучение (Skillbox, Учи.ру и т.п.) по правилам проекта — регулярные платежи, а не подписки.

## Стек

| Слой | Технологии |
|---|---|
| Бэкенд | Python 3.11+, FastAPI, pandas, pdfplumber, pydantic |
| ИИ | GigaChat API (SDK `gigachat`); модель подбирается автоматически из доступных на тарифе (на бесплатном тарифе физлица — GigaChat-2-Max) |
| Фронтенд | Чат на HTML / CSS / JavaScript (`design/website final/public/app.html`), макеты — Figma Make; светлая и тёмная тема |
| Деплой | Vercel: сайт (сборка Vite) и бэкенд (Python serverless-функция `api/index.py`) в одном проекте |
| Данные для демо | 9 синтетических выписок в формате экспорта банка + разметка подписок (`data/samples`) |

## Быстрый старт локально

```bash
git clone https://gitverse.ru/iische/probniy.git
cd probniy
copy .env.example .env             # Linux/macOS: cp .env.example .env — вписать LLM_API_KEY

cd backend
python -m venv .venv
.venv\Scripts\activate             # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Открыть http://localhost:8000/ — это и есть ассистент. Документация API: http://localhost:8000/docs.
Проверка ключа GigaChat: http://localhost:8000/api/v1/health?deep=1 → `"llm_check": {"ok": true}`.
Тесты: `pytest` из папки `backend` (15 тестов).

Без ключа сервис работает в режиме правил: результат тот же по форме, но в карточках кластеров стоит
`"reason": "Эвристическая классификация (LLM недоступен)"`, а рекомендации строятся шаблонно.

## Переменные окружения

Файл `.env` в корне репозитория (в `.gitignore`, не коммитится). Шаблон — `.env.example`.

| Переменная | Значение | Зачем |
|---|---|---|
| `LLM_PROVIDER` | `gigachat` | провайдер |
| `LLM_API_KEY` | Authorization key из кабинета developers.sber.ru | ключ GigaChat |
| `LLM_MODEL` | `GigaChat-2-Max` | если модели нет на тарифе, бэкенд сам выберет доступную |
| `LLM_VERIFY_SSL` | `1` локально, `0` на хостинге | на Vercel нет сертификатов Минцифры; на Vercel по умолчанию `0` |
| `LLM_TIMEOUT_S` | `45` | таймаут запроса к модели |
| `LLM_EMBEDDINGS` | `0` | эмбеддинги GigaChat для незнакомых названий; на бесплатном тарифе платные — выключены |
| `GIGACHAT_SCOPE` | `GIGACHAT_API_CORP` | только для корпоративного ключа; для личного не нужен |
| `APP_HOST`, `APP_PORT`, `MAX_UPLOAD_MB` | `0.0.0.0`, `8000`, `10` | параметры сервера |

## Деплой на Vercel

Сайт и бэкенд разворачиваются одним проектом: `vercel.json` собирает `design/website final` (Vite) и публикует
`api/index.py` как Python-функцию, которая импортирует `backend/app`. Зависимости функции — корневой `requirements.txt`.

```bash
npm i -g vercel
vercel login
vercel link          # команда ii-sche, проект website-final (или новый проект)
vercel --prod        # из корня репозитория
```

Переменные окружения проекта (Vercel → Settings → Environment Variables, Production): `LLM_PROVIDER=gigachat`,
`LLM_API_KEY=<ключ>` (тип Secret), `LLM_MODEL=GigaChat-2-Max`, `LLM_VERIFY_SSL=0`, `LLM_TIMEOUT_S=45`, `LLM_EMBEDDINGS=0`.
После изменения переменных нужен новый `vercel --prod`. Проверка: `https://<домен>/api/v1/health?deep=1`.

## API

| Метод | Путь | Что делает |
|---|---|---|
| `GET` | `/api/v1/health` | Состояние сервиса и настроек LLM; `?deep=1` — пробный запрос к GigaChat, список доступных моделей, текст ошибки без ключа |
| `POST` | `/api/v1/analyze` | Анализ выписки. `multipart/form-data`: `file` (CSV или PDF), `period` — `1m` · `3m` · `6m` · `1y` · `ytd` · `all` |
| `POST` | `/api/v1/report` | Рекомендации по подпискам. JSON: `subscriptions`, `total_spent`, `total_income`, `period` → строка текста |

Пример:

```bash
curl -F "file=@data/samples/statement_student_alexey.csv" -F "period=6m" http://localhost:8000/api/v1/analyze
```

Карточка подписки в ответе `/analyze`:

```json
{
  "service_name": "Яндекс Плюс",
  "charge_amount": 299.0,            "frequency": "monthly",
  "charges_count": 6,                "last_charge": "2026-08-13",
  "next_charge": "2026-09-13",       "actual_spent_in_period": 1794.0,
  "yearly_savings": 3588.0,          "monthly_cost": 299.0,
  "cancellation_guide": "Яндекс ID → Плюс → Отключить автопродление",
  "confidence": "high",              "alerts": [],
  "transactions": [ { "date": "2026-03-13", "amount": 299.0, "raw_description": "YANDEX.PLUS" } ]
}
```

Сводка `spending_overview`: `total_spent`, `total_subscriptions`, `total_recurring`, `total_household`,
`total_transfers_out`, `subscriptions_count`, `categories` (кластеры с категорией и пояснением модели).
Ошибки — `{"detail": "текст по-русски"}` с кодами `400` (файл не разобран), `413` (больше 10 МБ), `500`.

## Формат выписки

CSV с колонками `operationDate; merchant; amount; type` (обязательные) и `status; category; mcc` (желательные) —
так выгружает, например, Альфа-Банк; разделитель `;` или `,`, кодировка UTF-8 или Windows-1251. В анализ попадают
строки с типом «Списание» и статусом «Выполнен». PDF разбирается по таблицам: заголовки «Дата», «Описание», «Сумма», «Тип».

## Демо-данные и качество

`data/samples/` — девять синтетических профилей за март–сентябрь 2026 в реальном банковском формате: студент,
фрилансер, семья, геймер, максималист, пенсионер, путешественник, молодой специалист, пара. К каждой выписке —
`labels_<профиль>.json` с разметкой подписок (34 подписки суммарно). В режиме правил (без нейросети) находятся
31 из 34; три оставшиеся — Skillbox и Учи.ру, которые по правилам проекта относятся к регулярным платежам.
Файлы для демонстрации на защите: `statement_maximalist_viktor.csv` (11 подписок), `statement_student_alexey.csv` (3).

## Структура репозитория

```
api/index.py                       точка входа Vercel → backend/app
backend/app/main.py                приложение FastAPI, отдаёт страницу ассистента
backend/app/routers/scan.py        /api/v1/health, /api/v1/analyze
backend/app/routers/report.py      /api/v1/report
backend/app/services/parser.py     CSV и PDF → транзакции
backend/app/services/naming.py     нормализация названий, словарь алиасов, эмбеддинги
backend/app/services/ai.py         GigaChat: классификация, карточки подписок, рекомендации; фолбэк на правилах
backend/app/services/llm.py        адаптер провайдеров, автоподбор модели, самодиагностика
backend/app/services/detector.py   периодичность и алерты
backend/app/models.py              модели ответа (pydantic)
backend/app/config.py              словари сервисов, алиасы, MCC-коды, категории подписок
backend/tests/                     тесты pytest
design/website final/              сайт (Figma Make + Vite); public/app.html — чат-ассистент
web/design/website final/public/   копия app.html для локального запуска через uvicorn
data/samples/                      демо-выписки и разметка
docs/                              журнал решений, ТЗ, дневники правок интерфейса
vercel.json, requirements.txt, .vercelignore   деплой на Vercel
```

## Ограничения

- Бесплатный тариф GigaChat обрабатывает запросы в один поток: одновременные анализы встают в очередь (+10–15 с).
- Эмбеддинги на бесплатном тарифе платные — шаг выключен, варианты названий объединяются словарём и нормализацией.
- На Vercel размер запроса до 4,5 МБ, время функции до 60 с; период анализа считается от текущей даты.
- PDF-выписки поддерживаются только табличные (без сканов).

## Команда ИИще

Тимлид и интеграция (Voldemurik) · AI-интегратор — GigaChat, промпты, адаптер LLM (greaterdustyyy) · Backend — FastAPI,
парсеры, слияние с фронтом (olegas) · Frontend — чат-интерфейс (Danil2) · UI/UX-дизайнер — макеты Figma Make, сайт,
презентация (gohefi) · Аналитик / продакт-менеджер — ТЗ, спорные случаи классификации (TREgor).
Часть интеграции, кластеризация названий, карточки подписок и деплой на Vercel сделаны с помощью ИИ-ассистента Claude.

## Лицензия

MIT — см. файл `LICENSE`.
