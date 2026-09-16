"""Каноническое имя мерчанта и объединение вариантов написания одного сервиса.

Два уровня:
1. Детерминированный — нормализация строки + словарь алиасов из config.py
   (точное совпадение, совпадение по набору токенов, совпадение без шумовых токенов).
   Так «YANDEX.PLUS», «Yandex Plus» и «ЯНДЕКС ПЛЮС» попадают в один кластер без сети.
2. Эмбеддинги (векторные представления текста) GigaChat — только для названий,
   которых нет в словаре: два кластера объединяются, если векторы названий почти
   совпадают И суммы списаний близки. Любая ошибка сети → пропускаем шаг молча.
"""
from __future__ import annotations

import math
import re
from statistics import median
from typing import Callable, Dict, List, Sequence

from app.config import ALIASES, NOISE_TOKENS

_ALIAS_BY_TOKENS: Dict[tuple, str] = {}


def _tokens(text: str) -> List[str]:
    return [t for t in text.split() if t]


def _build_alias_index() -> None:
    """Индекс алиасов по отсортированному набору токенов (с шумом и без)."""
    for key, canonical in ALIASES.items():
        toks = _tokens(normalize(key))
        if toks:
            _ALIAS_BY_TOKENS.setdefault(tuple(sorted(toks)), canonical)
        clean = [t for t in toks if t not in NOISE_TOKENS]
        if clean:
            _ALIAS_BY_TOKENS.setdefault(tuple(sorted(clean)), canonical)


def normalize(raw: str) -> str:
    """Нижний регистр, ё→е, любая пунктуация (точки, слэши, плюсы, звёздочки) → пробел."""
    text = str(raw or "").lower().replace("ё", "е").strip()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    text = text.replace("_", " ")
    return re.sub(r"\s+", " ", text).strip()


def canonical_name(raw: str) -> str:
    """Имя кластера для сырого названия мерчанта из выписки."""
    norm = normalize(raw)
    if not norm:
        return ""
    if norm in ALIASES:
        return ALIASES[norm]
    toks = _tokens(norm)
    hit = _ALIAS_BY_TOKENS.get(tuple(sorted(toks)))
    if hit:
        return hit
    clean = [t for t in toks if t not in NOISE_TOKENS and not t.isdigit()]
    if clean:
        key = " ".join(clean)
        if key in ALIASES:
            return ALIASES[key]
        hit = _ALIAS_BY_TOKENS.get(tuple(sorted(clean)))
        if hit:
            return hit
        return " ".join(w.capitalize() for w in clean)
    return " ".join(w.capitalize() for w in toks)


def is_known(canonical: str) -> bool:
    return canonical in _KNOWN_CANONICALS


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if not na or not nb:
        return 0.0
    return dot / (na * nb)


def _median_amount(cluster: Dict) -> float:
    amounts = [abs(float(t.get("amount", 0) or 0)) for t in cluster.get("transactions", [])]
    return float(median(amounts)) if amounts else 0.0


def merge_clusters_by_embeddings(
    clusters: List[Dict],
    embed: Callable[[List[str]], List[List[float]]],
    threshold: float = 0.95,
    amount_tolerance: float = 0.15,
) -> List[Dict]:
    """Объединяет кластеры с НЕИЗВЕСТНЫМИ названиями по близости эмбеддингов.

    clusters — список словарей из ai._simple_cluster. Известные (из словаря) кластеры
    не участвуют: их уже объединил словарь, а разные продукты одного бренда
    (Яндекс Плюс / Яндекс Диск) эмбеддингами объединять нельзя.
    """
    candidates = [i for i, c in enumerate(clusters) if not is_known(c.get("canonical_name", ""))]
    if len(candidates) < 2:
        return clusters

    names = [clusters[i]["canonical_name"] for i in candidates]
    vectors = embed(names)
    if not vectors or len(vectors) != len(names):
        return clusters

    parent = {i: i for i in candidates}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a in range(len(candidates)):
        for b in range(a + 1, len(candidates)):
            ia, ib = candidates[a], candidates[b]
            if _cosine(vectors[a], vectors[b]) < threshold:
                continue
            ma, mb = _median_amount(clusters[ia]), _median_amount(clusters[ib])
            if ma and mb and abs(ma - mb) / max(ma, mb) > amount_tolerance:
                continue
            parent[find(ia)] = find(ib)

    groups: Dict[int, List[int]] = {}
    for i in candidates:
        groups.setdefault(find(i), []).append(i)

    merged_into: Dict[int, int] = {}
    for members in groups.values():
        if len(members) < 2:
            continue
        head = max(members, key=lambda i: clusters[i].get("count", 0))
        for i in members:
            if i != head:
                merged_into[i] = head

    if not merged_into:
        return clusters

    result: List[Dict] = []
    for i, cluster in enumerate(clusters):
        if i in merged_into:
            continue
        item = dict(cluster)
        variations = list(cluster.get("merchant_variations", []))
        txs = list(cluster.get("transactions", []))
        for j, head in merged_into.items():
            if head != i:
                continue
            variations.extend(clusters[j].get("merchant_variations", []))
            txs.extend(clusters[j].get("transactions", []))
        item["merchant_variations"] = sorted(set(variations))
        item["transactions"] = txs
        item["count"] = len(txs)
        item["total_amount"] = round(sum(float(t.get("amount", 0) or 0) for t in txs), 2)
        result.append(item)
    return result


_KNOWN_CANONICALS = set(ALIASES.values())
_build_alias_index()
