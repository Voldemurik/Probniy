"""
Временные демо-выписки для вертикального среза (пятница).
Заменяются генератором AI-1 (data/generate.py) с разметкой labels.json.

python data/samples/make_demo.py  → student.csv, family.csv, maximalist.csv
Формат: наш эталон csv-ru (см. docs/contract.md, «Формат входного CSV»).
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent
START, END = date(2026, 3, 3), date(2026, 9, 2)
rng = random.Random(42)

NOISE = [
    ("Супермаркеты", ["PYATEROCHKA 1234 EKATERINBURG RUS", "MAGNIT MM EKATERINBURG RUS", "PEREKRESTOK 77 EKATERINBURG"], (350, 2600)),
    ("Кафе и рестораны", ["SHOKOLADNITSA EKATERINBURG", "VKUSNO I TOCHKA 0452", "COFFEE LIKE EKB"], (180, 1400)),
    ("Транспорт", ["YANDEX GO MOSCOW RUS", "EKARTA POPOLNENIE", "AZS GAZPROMNEFT 112"], (45, 3200)),
    ("Маркетплейсы", ["OZON.RU MOSCOW", "WILDBERRIES MOSCOW RUS"], (390, 5900)),
    ("Аптеки", ["APTEKA ZHIVIKA 45", "APTEKA.RU"], (210, 1800)),
]


def money(x: float) -> str:
    return f"{x:.2f}".replace(".", ",")


def month_dates(day: int, count: int, start: date = START, jitter: bool = True) -> list[date]:
    out = []
    y, m = start.year, start.month
    for _ in range(count):
        d = date(y, m, min(day, 28))
        if jitter and d.weekday() >= 5:  # выходные — сдвиг на понедельник
            d += timedelta(days=7 - d.weekday())
        out.append(d)
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return out


def noise_rows(n: int) -> list[tuple[date, str, str, float]]:
    rows = []
    for _ in range(n):
        cat, descs, (lo, hi) = rng.choice(NOISE)
        d = START + timedelta(days=rng.randint(0, (END - START).days))
        rows.append((d, cat, rng.choice(descs), -round(rng.uniform(lo, hi), 2)))
    return rows


def common_negatives() -> list[tuple[date, str, str, float]]:
    rows = []
    for d in month_dates(5, 6, jitter=False):  # аренда — регулярный перевод, но не подписка
        rows.append((d, "Переводы", "Перевод по СБП Смирнова А.В.", -25000.0))
    for d in month_dates(10, 6, jitter=False):  # зарплата
        rows.append((d, "Зачисления", "Зачисление заработной платы", 68000.0))
    for d in month_dates(18, 6, jitter=False):  # ЖКУ с плавающей суммой — не подписка
        rows.append((d, "ЖКХ", "ERC EKATERINBURG KOMMUNALNYE USLUGI", -round(rng.uniform(3900, 6100), 2)))
    for d in month_dates(22, 6, jitter=False):  # снятие наличных
        rows.append((d, "Наличные", "Снятие наличных ATM SBERBANK 60123", -5000.0))
    return rows


def sub_rows(descs: list[str], day: int, amounts: list[float], category: str = "Прочие операции", start: date = START) -> list[tuple[date, str, str, float]]:
    ds = month_dates(day, len(amounts), start=start)
    return [(d, category, descs[i % len(descs)], -a) for i, (d, a) in enumerate(zip(ds, amounts))]


def write(name: str, rows: list[tuple[date, str, str, float]]) -> None:
    rows.sort(key=lambda r: r[0])
    with (OUT / name).open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Дата операции", "Категория", "Описание операции", "Сумма", "Валюта"])
        for d, cat, desc, amt in rows:
            w.writerow([d.strftime("%d.%m.%Y"), cat, desc, money(amt), "RUB"])


def student() -> None:
    rows = common_negatives() + noise_rows(60)
    rows += sub_rows(["YANDEX.PLUS MOSCOW RUS", "Yandex Plus", "ЯНДЕКС ПЛЮС"], 14, [299] * 6, "Развлечения")
    rows += sub_rows(["LITRES.RU MOSCOW"], 3, [1, 299, 299, 299, 299, 299], "Книги")  # пробный период
    rows += sub_rows(["CLOUD.MAIL.RU MOSCOW RUS", "Cloud Mail.ru"], 20, [199] * 6, "Прочие операции")
    write("student.csv", rows)


def family() -> None:
    rows = common_negatives() + noise_rows(80)
    rows += sub_rows(["KINOPOISK MOSCOW RUS", "Кинопоиск"], 7, [399] * 6, "Развлечения")
    rows += sub_rows(["OKKO.TV MOSCOW RUS"], 12, [499] * 3, "Развлечения", start=date(2026, 6, 1))  # начата 3 месяца назад
    rows += sub_rows(["UCHI.RU MOSCOW RUS", "ООО УЧИ.РУ"], 1, [1490] * 6, "Образование")
    rows += sub_rows(["SBERPRIME MOSCOW RUS", "СберПрайм"], 25, [399] * 6, "Прочие операции")
    rows += sub_rows(["MTS PAY MOSCOW RUS"], 9, [650] * 6, "Связь")
    write("family.csv", rows)


def maximalist() -> None:
    rows = common_negatives() + noise_rows(90)
    rows += sub_rows(["KINOPOISK MOSCOW RUS", "KINOPOISK HD"], 2, [399] * 6, "Развлечения")
    rows += sub_rows(["OKKO.TV MOSCOW RUS"], 4, [499] * 6, "Развлечения")
    rows += sub_rows(["PREMIER.ONE MOSCOW"], 6, [599] * 6, "Развлечения")
    rows += sub_rows(["START.RU MOSCOW RUS", "ООО СТАРТ"], 8, [399] * 6, "Развлечения")
    rows += sub_rows(["IVI.RU MOSCOW RUS"], 11, [399] * 6, "Развлечения")
    rows += sub_rows(["ZVUK.COM MOSCOW", "SBERZVUK"], 13, [299] * 6, "Развлечения")
    rows += sub_rows(["VK MUSIC MOSCOW RUS", "ВК МУЗЫКА"], 15, [299] * 6, "Развлечения")
    rows += sub_rows(["YANDEX.DISK MOSCOW RUS"], 17, [249, 249, 249, 399, 399, 399], "Прочие операции")  # рост цены
    rows += sub_rows(["CLOUD.MAIL.RU MOSCOW RUS"], 19, [399] * 6, "Прочие операции")
    rows += sub_rows(["FITMOST.COM MOSCOW"], 21, [3990] * 6, "Спорт")
    rows += sub_rows(["SBERPRIME MOSCOW RUS"], 24, [399] * 6, "Прочие операции")
    rows += sub_rows(["APPLE.COM/BILL ITUNES.COM"], 27, [199] * 6, "Прочие операции")  # скрытое название
    write("maximalist.csv", rows)


if __name__ == "__main__":
    student()
    family()
    maximalist()
    print("ok:", ", ".join(p.name for p in OUT.glob("*.csv")))
