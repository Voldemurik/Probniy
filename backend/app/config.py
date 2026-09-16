import os

MAX_FILE_SIZE = 10 * 1024 * 1024
REQUIRED_COLUMNS = {"operationDate", "merchant", "amount", "type"}

KNOWN_SUBSCRIPTION_SERVICES = {
    "VK Музыка", "СберПрайм", "Звук", "Иви", "START", "PREMIER", "OKKO",
    "КиноПоиск", "Яндекс Диск", "Яндекс Плюс", "VK Cloud", "Cloud Mail.ru",
    "FITMOST", "Apple Services", "Netflix", "Spotify", "Apple Music",
    "YouTube Premium", "YouTube Music", "Telegram Premium", "ChatGPT", "OpenAI",
    "iCloud", "Lesta Games", "VK Play", "Литрес",
}

KNOWN_NON_SUBSCRIPTION_SERVICES = {
    "Skillbox", "Skillbox.ru", "CLOUDPAYMENTS SKILLBOX", "GeekBrains",
    "SkillFactory", "Нетология", "Учи.ру",
}

SUBSCRIPTION_MCC = {5968, 5815, 5816, 5817, 5818}
NON_SUBSCRIPTION_MCC = {5411, 5499, 5812, 5814, 4111, 4131, 5912, 5300, 6011}

EXCLUDED_CATEGORIES = {
    "Продукты", "Транспорт", "Переводы", "Кэшбэк", "Маркетплейсы", "Фастфуд",
    "Хобби", "Дом и ремонт", "Между своими счетами", "Кафе", "Наличные", "Аптеки",
}

EXCLUDED_DESCRIPTION_PATTERNS = [
    "снятие наличных", "банкомат", "atm", "cash withdrawal", "перевод", "оплата по qr",
]

AMOUNT_TOLERANCE = 0.05
PERIOD_RANGES = {
    "weekly": (5, 9),
    "biweekly": (12, 18),
    "monthly": (25, 35),
    "quarterly": (75, 105),
}

ALIASES = {
    "vk music": "VK Музыка", "вк музыка": "VK Музыка", "vk com music": "VK Музыка",
    "vk.com music": "VK Музыка", "vkplay": "VK Play", "vk play": "VK Play",
    "vk play plus": "VK Play", "sberprime": "СберПрайм", "сберпрайм": "СберПрайм",
    "sber prime": "СберПрайм", "sber prime+": "СберПрайм", "zvuk": "Звук",
    "zvuk com": "Звук", "sberzvuk": "Звук", "ivi": "Иви", "ооо иви ру": "Иви",
    "start ru": "START", "ооо старт": "START", "start": "START", "premier": "PREMIER",
    "premier tv": "PREMIER", "premier one": "PREMIER", "okko": "OKKO", "okko tv": "OKKO",
    "okko premium": "OKKO", "kinopoisk": "КиноПоиск", "kinopoisk hd": "КиноПоиск",
    "yandex plus kinopoisk": "КиноПоиск", "yandex disk": "Яндекс Диск", "yandex disk plus": "Яндекс Диск",
    "yandex plus": "Яндекс Плюс", "яндекс плюс": "Яндекс Плюс", "vk cloud": "VK Cloud",
    "cloud mail ru": "Cloud Mail.ru", "fitmost com": "FITMOST", "фитмост": "FITMOST",
    "uchi": "Учи.ру", "uchi ru": "Учи.ру", "ооо учи ру": "Учи.ру", "lesta": "Lesta Games",
    "lesta ru": "Lesta Games", "lesta games": "Lesta Games", "litres": "Литрес",
    "литрес": "Литрес", "ooo litres": "Литрес", "ооо литрес": "Литрес", "litres ru": "Литрес",
    "netflix": "Netflix", "spotify": "Spotify", "apple com bill": "Apple Services",
    "apple services": "Apple Services", "apple music": "Apple Music", "youtube premium": "YouTube Premium",
    "youtube music": "YouTube Music", "telegram premium": "Telegram Premium", "chatgpt": "ChatGPT",
    "openai": "OpenAI", "icloud": "iCloud",
}

BANK_CATEGORY_TO_EXPENSE_CATEGORY = {
    "Продукты": "household_food", "Транспорт": "household_transport", "Кафе": "household_cafe",
    "Фастфуд": "household_cafe", "Аптеки": "household_pharmacy", "Маркетплейсы": "marketplace",
    "Наличные": "cash_withdrawal", "Переводы": "transfer_out",
}


# --- Дополнения 06.09: варианты названий из демо-выписок AI-1 (labels_*.json) -----------------
# Только новые записи и уточнения; существующие алиасы не трогаем.
ALIASES.update({
    # в разметке AI-1 CLOUD.MAIL.RU / MAIL.RU CLOUD / VK CLOUD — одна подписка «Облако Mail.ru»
    "vk cloud": "Cloud Mail.ru",
    "mail ru cloud": "Cloud Mail.ru",
    "ivi ru": "Иви",
    "skillbox": "Skillbox", "skillbox ru": "Skillbox", "cloudpayments skillbox": "Skillbox",
    "одноклассники": "Одноклассники",
    "ростелеком": "Ростелеком", "rt ru": "Ростелеком",
    "duolingo": "Duolingo", "duolingo plus": "Duolingo",
    "priority pass": "Priority Pass", "prioritypass": "Priority Pass",
    "fragment com": "Telegram Premium", "fragment": "Telegram Premium",
})

KNOWN_SUBSCRIPTION_SERVICES |= {"Одноклассники", "Ростелеком", "Duolingo", "Priority Pass"}

# Шумовые токены, которые не несут смысла при сопоставлении названий мерчантов
# (форма собственности, домены, города). Используются в services/naming.py.
NOISE_TOKENS = {
    "ooo", "ооо", "ао", "пао", "ип", "llc", "ltd", "inc", "www", "ru", "com", "рф", "net", "org",
    "moscow", "moskva", "москва", "ekaterinburg", "ekb", "екатеринбург", "rus", "russia", "россия",
    "оплата", "покупка", "payment", "pay",
}

# Категории подписок для поиска дублей в рекомендациях (только известные сервисы)
SUBSCRIPTION_CATEGORY_RU = {
    "видео": {"КиноПоиск", "OKKO", "Иви", "PREMIER", "START", "Netflix", "YouTube Premium"},
    "музыка": {"Звук", "VK Музыка", "Spotify", "Apple Music", "YouTube Music"},
    "облако": {"Яндекс Диск", "Cloud Mail.ru", "VK Cloud", "iCloud"},
    "игры": {"VK Play", "Lesta Games"},
    "обучение": {"Skillbox", "Учи.ру", "Duolingo"},
    "экосистема": {"Яндекс Плюс", "СберПрайм", "Telegram Premium"},
}
