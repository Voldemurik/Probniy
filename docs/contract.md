# Контракт данных «Подписки-сканер» — v0.1

Единственный источник правды о том, какими данными обмениваются бэкенд, фронтенд, AI-сервисы и стенд качества.
Код контракта — `backend/app/models.py` (pydantic), типы для фронтенда — `frontend/src/types.ts`, мок — `frontend/src/mock/result.json`.
Тест `backend/tests/test_contract_mock.py` проверяет, что мок соответствует моделям.

**Правило изменения.** Сначала сообщение в чат команды («меняю контракт: …»), затем правка `models.py` + этого файла + `types.ts` + мока в одном PR. Поле `contract_version` в ответе растёт при любом несовместимом изменении.

---

## 1. Термины и договорённости

| Термин | Что значит |
|---|---|
| Транзакция | одна строка выписки после разбора файла |
| Подписка | группа списаний одного сервиса с регулярным интервалом и стабильной суммой (правила — `docs/detection.md`) |
| Кластер | варианты написания одного сервиса, объединённые в одну подписку (`merchant_raw_variants`) |
| Опорная дата | последняя дата в выписке (`meta.period_to`). Именно от неё считаются `status`, `next_charge_expected` и «продление скоро», а не от «сегодня» — иначе результат на демо-файлах менялся бы каждый день |
| Списание | транзакция с отрицательной суммой; в анализ попадают только списания |

Идентификаторы: `t_000123` — транзакция, где число — **порядковый номер строки в исходном файле (0-based)**. Это позволяет стенду AI-1 сопоставлять результат с `labels.json` (`tx_indices`). `s_001` — подписка, номер по порядку после сортировки.

Даты — ISO `YYYY-MM-DD`. Суммы — числа в рублях с двумя знаками; в транзакциях знак значим, в подписках всегда положительные.

---

## 2. API

Базовый адрес: `http://localhost:8000`. Документация: `/docs`.

| Метод и путь | Вход | Выход | Кто делает |
|---|---|---|---|
| `GET /api/health` | — | `{status, contract_version, llm_provider, llm_model}` | готово |
| `POST /api/scan` | multipart `file` (CSV; PDF — с воскресенья) | `ScanResult` | готово (CSV) |
| `GET /api/samples` | — | `SampleInfo[]` | готово |
| `GET /api/samples/{id}/scan` | — | `ScanResult` по демо-файлу | готово |
| `POST /api/subscriptions/cancel-plan` | `CancelPlanRequest` | `CancelPlan` | AI-2 + BE, воскресенье |
| `POST /api/subscriptions/cancel-plan/bulk` | `BulkCancelRequest` | `BulkCancelPlan` | AI-2 + BE, воскресенье |
| `GET /api/quality` | — | отчёт стенда (`eval/report.json`, формат за AI-1) | AI-1, воскресенье |

Ошибки — всегда JSON `ErrorResponse`, фронтенд показывает `error` как есть, `hint` — второй строкой:

```json
{ "error": "В файле не найдены колонки: сумма", "hint": "Нужны колонки «Дата операции», «Описание операции», «Сумма»" }
```

Коды: `400` — файл не разобран, `413` — больше 10 МБ, `404` — нет такого демо-профиля, `422` — тело запроса не по контракту, `503` — модель недоступна и ответа нет в кэше.

---

## 3. Модели

### Transaction

```json
{
  "id": "t_000123",
  "date": "2026-03-14",
  "amount": -299.0,
  "currency": "RUB",
  "description": "YANDEX.PLUS MOSCOW RUS",
  "category_bank": "Развлечения",
  "mcc": 5968
}
```

`amount` отрицательный — списание. `category_bank` и `mcc` — если банк их дал, иначе `null`.

### Subscription

```json
{
  "id": "s_009",
  "name": "Яндекс Диск",
  "merchant_raw_variants": ["YANDEX.DISK MOSCOW RUS"],
  "category": "cloud",
  "period": "monthly",
  "amount_current": 399.0,
  "amount_history": [
    { "date": "2026-03-17", "amount": 249.0 },
    { "date": "2026-06-17", "amount": 399.0 }
  ],
  "charges": ["t_000014", "t_000044", "t_000073", "t_000103", "t_000131", "t_000162"],
  "first_charge": "2026-03-17",
  "last_charge": "2026-08-17",
  "next_charge_expected": "2026-09-16",
  "status": "active",
  "confidence": 0.99,
  "flags": ["price_increase", "duplicate"],
  "decoded": { "guess": null, "confidence": null, "reason": null },
  "monthly_cost": 399.0,
  "yearly_cost": 4788.0
}
```

| Поле | Значения и смысл |
|---|---|
| `period` | `weekly` · `monthly` · `quarterly` · `yearly` |
| `status` | `active` — списания продолжаются; `inactive` — последнее старше 1,5 периода от опорной даты (тогда `next_charge_expected = null`) |
| `confidence` | 0–1. UI: ≥ 0,8 зелёный «уверены», 0,5–0,8 жёлтый «проверьте», < 0,5 серый «предположение» |
| `flags` | `price_increase`, `price_decrease`, `trial_converted`, `duplicate`, `renewal_soon`, `gap`, `decoded`, `inactive` |
| `category` | `video` · `music` · `cloud` · `books` · `education` · `games` · `fitness` · `ecosystem` · `telecom` · `software` · `other` (русские подписи — `CATEGORY_LABELS_RU` в `models.py`) |
| `amount_history` | первая точка — первое «настоящее» списание (пробное за 1 ₽ не считается), далее по точке на каждое изменение цены |
| `decoded` | заполняет AI-2, когда название скрыто за агрегатором (`APPLE.COM/BILL` → «iCloud 50 ГБ»); `reason` — фраза для интерфейса |
| `monthly_cost` / `yearly_cost` | `yearly = amount_current × {52, 12, 4, 1}`, `monthly = yearly / 12` |

### ScanResult

```json
{
  "contract_version": "0.1",
  "meta": {
    "period_from": "2026-03-03",
    "period_to": "2026-09-02",
    "months": 6.0,
    "tx_count": 186,
    "debit_count": 72,
    "source_format": "csv-ru",
    "warnings": []
  },
  "totals": { "count": 12, "monthly": 8279.0, "yearly": 99348.0 },
  "subscriptions": [ "…Subscription, отсортированы: активные по yearly_cost ↓, затем неактивные…" ],
  "insights": [
    { "type": "price_increase", "subscription_ids": ["s_009"], "text": "«Яндекс Диск» подорожал с 249 ₽ до 399 ₽ (17.06.2026)" },
    { "type": "duplicate", "subscription_ids": ["s_002", "s_003", "s_004"], "text": "3 активные подписки категории «Видео»: … — возможно, достаточно одной" }
  ]
}
```

`totals` считаются только по активным подпискам. `insights` — готовые фразы для блока «Стоит проверить»; фронтенд их не сочиняет, а показывает. `meta.warnings` — замечания разбора, показываются под итогами («В файле нет знака списаний — все операции считаем расходами»).

Полный пример — `frontend/src/mock/result.json` (профиль «Максималист»).

### Модели AI-сервисов (AI-2)

`EnrichedCluster` — ответ `enrich_cluster(variants, amount, period)`:

```json
{
  "display_name": "iCloud 50 ГБ",
  "category": "cloud",
  "is_subscription_likelihood": 0.9,
  "decoded_guess": "iCloud 50 ГБ",
  "decoded_confidence": 0.7,
  "decoded_reason": "Списание 199 ₽ ежемесячно через APPLE.COM/BILL — типичная цена тарифа iCloud 50 ГБ",
  "cancellation_channel": "app"
}
```

`CancelPlan` — ответ `cancel_plan(subscription)`:

```json
{
  "subscription_id": "s_009",
  "service_name": "Яндекс Диск",
  "channel": "site",
  "steps": [
    { "order": 1, "text": "Откройте disk.yandex.ru → Настройки → Тариф" },
    { "order": 2, "text": "Нажмите «Отключить автопродление» и подтвердите" }
  ],
  "letter": "Здравствуйте! Прошу отключить автопродление подписки на аккаунте [e-mail аккаунта] …",
  "yearly_savings": 4788.0
}
```

`BulkCancelPlan` — `{ plans: CancelPlan[], total_yearly_savings, summary }`, где `summary` — текст «что отменить» для копирования одним нажатием.

Запросы: `CancelPlanRequest { subscription: Subscription, tone: "neutral" | "polite" | "firm" }`, `BulkCancelRequest { subscriptions: Subscription[], tone }`.

### SampleInfo

`{ id: "student", title: "Студент", description: "…", file: "student.csv" }` — фронтенд рисует кнопки «Загрузить пример» из этого списка, а не хардкодит.

---

## 4. Формат входного CSV

Колонки узнаются по названиям (регистр и порядок не важны), разделитель `;` или `,`, кодировка UTF-8 или Windows-1251, десятичный разделитель `,` или `.`.

**Эталон (csv-ru)** — так пишет генератор AI-1 и так выглядят демо-файлы:

```
Дата операции;Категория;Описание операции;Сумма;Валюта
14.03.2026;Развлечения;YANDEX.PLUS MOSCOW RUS;-299,00;RUB
15.03.2026;Супермаркеты;PYATEROCHKA 1234 EKATERINBURG;-1 245,60;RUB
05.03.2026;Переводы;Перевод по СБП Смирнова А.В.;-25000,00;RUB
```

**csv-en** — формат из `ai research/main.py` (тоже принимается):

```
operationDate,merchant,amount,type,status,category,mcc
14.03.2026,YANDEX.PLUS MOSCOW RUS,299,Списание,Выполнен,Развлечения,5968
```

Знак суммы: есть колонка «тип» → «Списание» минус, «Пополнение» плюс; нет — берём знак числа; если все суммы неотрицательные, считаем всё списаниями и пишем предупреждение. Строки со статусом, отличным от «Выполнен», пропускаются, но нумерация `t_…` сохраняет исходные номера строк.

Синонимы колонок — `COLUMN_SYNONYMS` в `backend/app/services/parser.py`; новые названия банков добавляются туда.

---

## 5. Связь с разметкой стенда (AI-1)

`labels.json` описывает подписки через `tx_indices` — номера строк в объединённом массиве транзакций. Чтобы стенд работал без преобразований:

1. индексы в `labels.json` должны быть **внутри файла профиля** (0-based номер строки без заголовка), а не сквозными по всем профилям — тогда `t_{index}` из ответа совпадает напрямую;
2. подписка считается найденной, если ≥ 80 % её `tx_indices` попали в `charges` одной найденной подписки;
3. для случаев, которые по правилам не должны находиться (например, две транзакции у «Литрес»), в разметке нужен признак `expected_detectable: false`.

---

## 6. Что фронтенду нужно знать

* Работайте от `types.ts` и мока; переключатель `VITE_USE_MOCK=1` читает `src/mock/result.json`, иначе — `VITE_API_URL`.
* Кнопка «Это не подписка» — клиентское действие: подписка скрывается, `totals` пересчитываются на клиенте по оставшимся активным (`monthly_cost`, `yearly_cost`), на бэкенд ничего не отправляется.
* Суммы форматируются как `8 279 ₽` (неразрывный пробел между разрядами), цифры моноширинные.
* Порядок подписок в ответе уже правильный — не пересортировывайте.
