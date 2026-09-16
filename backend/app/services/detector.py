import pandas as pd
from typing import List, Optional


def detect_frequency(dates: List[pd.Timestamp]) -> Optional[str]:
    """Определяет периодичность платежей по интервалам между датами."""
    from app.config import PERIOD_RANGES

    if len(dates) < 2:
        return None
    dates = sorted(dates)
    intervals = [(dates[i] - dates[i - 1]).days for i in range(1, len(dates))]
    if not intervals:
        return None

    candidates = []
    for frequency, (low, high) in PERIOD_RANGES.items():
        matching = [interval for interval in intervals if low <= interval <= high]
        match_count = len(matching)
        if len(intervals) >= 2 and match_count < 2:
            continue
        elif match_count < 1:
            continue
        score = match_count / len(intervals)
        candidates.append((score, match_count, frequency))

    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return candidates[0][2]


def detect_alerts(transactions: pd.DataFrame) -> List[str]:
    """Формирует полезные алерты по истории платежей: окончание пробного периода, изменение цены."""
    alerts = []
    if transactions.empty:
        return alerts

    transactions = transactions.sort_values("date")
    amounts = transactions["amount"].tolist()

    if amounts and amounts[0] == 1:
        alerts.append("Возможно, закончился пробный период")

    if len(amounts) >= 2:
        previous, latest = amounts[-2], amounts[-1]
        if previous > 0:
            if latest > previous * 1.10:
                alerts.append("Обнаружено повышение цены в последнем платеже")
            elif latest < previous * 0.90:
                alerts.append("Обнаружено снижение цены в последнем платеже")

    return alerts
