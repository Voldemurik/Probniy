"""Тесты дополнений 06.09: кластеризация вариантов названий, карточка подписки, рекомендации."""
from app.services.naming import canonical_name, merge_clusters_by_embeddings
from app.services.ai import _build_subscription, AIClusterResponse, _heuristic_recommendations, classify_all_expenses
from app.models import Subscription


def test_canonical_name_merges_spelling_variants():
    assert canonical_name("YANDEX.PLUS") == canonical_name("Yandex Plus") == canonical_name("ЯНДЕКС ПЛЮС") == "Яндекс Плюс"
    assert canonical_name("CLOUD.MAIL.RU") == canonical_name("MAIL.RU CLOUD") == canonical_name("VK CLOUD") == "Cloud Mail.ru"
    assert canonical_name("OKKO.TV") == canonical_name("OKKO PREMIUM") == "OKKO"
    assert canonical_name("ООО ИВИ.РУ") == canonical_name("IVI.RU") == "Иви"
    assert canonical_name("EKATERINBURG MAGNIT MM 1158") == canonical_name("Ekaterinburg Magnit Mm 3274") == "Magnit Mm"


def test_build_subscription_card_fields():
    ai = AIClusterResponse(category="subscription", canonical_name="Яндекс Плюс", total_amount=897.0,
                           transaction_count=3, is_subscription=True)
    txs = [
        {"date": "2026-06-13", "amount": 299.0, "merchant": "YANDEX.PLUS"},
        {"date": "2026-07-14", "amount": 299.0, "merchant": "YANDEX PLUS"},
        {"date": "2026-08-13", "amount": 299.0, "merchant": "ЯНДЕКС ПЛЮС"},
    ]
    sub = _build_subscription(ai, txs)
    assert sub.charge_amount == 299.0
    assert sub.charges_count == 3
    assert sub.last_charge == "2026-08-13"
    assert sub.next_charge == "2026-09-13"
    assert sub.frequency == "monthly"
    assert sub.yearly_savings == 3588.0
    assert sub.actual_spent_in_period == 897.0


def test_heuristic_recommendations_only_about_subscriptions():
    subs = [
        Subscription(service_name="VK Play", monthly_cost=999.0, yearly_cost=11988.0, frequency="monthly",
                     confidence="high", alerts=[], transactions=[], actual_spent_in_period=5994.0,
                     charge_amount=999.0, charges_count=6, last_charge="2026-08-20", next_charge="2026-09-20",
                     yearly_savings=11988.0),
        Subscription(service_name="Lesta Games", monthly_cost=1000.0, yearly_cost=12000.0, frequency="monthly",
                     confidence="high", alerts=[], transactions=[], actual_spent_in_period=3000.0,
                     charge_amount=1000.0, charges_count=3, last_charge="2026-08-01", next_charge="2026-09-01",
                     yearly_savings=12000.0),
    ]
    text = _heuristic_recommendations(subs, 6)
    lines = [l for l in text.splitlines() if l.strip()]
    assert 3 <= len(lines) <= 5
    assert "VK Play" in lines[0] and "5 994 ₽" in lines[0]
    assert "игры" in text  # два игровых сервиса → совет оставить один
    assert "всеми ли сервисами" in text.lower()
    for bad in ("продукт", "перевод", "кафе", "такси"):
        assert bad not in text.lower()


def test_embeddings_merge_only_unknown_and_similar_amounts():
    clusters = [
        {"canonical_name": "Netflx", "merchant_variations": ["NETFLX"], "count": 2, "total_amount": 1198.0,
         "category_hint": "", "mcc": None, "transactions": [{"amount": 599.0}, {"amount": 599.0}]},
        {"canonical_name": "Nflx", "merchant_variations": ["NFLX*"], "count": 1, "total_amount": 599.0,
         "category_hint": "", "mcc": None, "transactions": [{"amount": 599.0}]},
        {"canonical_name": "Stolovaya", "merchant_variations": ["STOLOVAYA"], "count": 1, "total_amount": 150.0,
         "category_hint": "Кафе", "mcc": None, "transactions": [{"amount": 150.0}]},
        {"canonical_name": "Яндекс Плюс", "merchant_variations": ["YANDEX PLUS"], "count": 1, "total_amount": 299.0,
         "category_hint": "", "mcc": None, "transactions": [{"amount": 299.0}]},
    ]
    vectors = {"Netflx": [1.0, 0.0], "Nflx": [0.99, 0.14], "Stolovaya": [0.0, 1.0]}
    merged = merge_clusters_by_embeddings(clusters, lambda names: [vectors[n] for n in names])
    names = sorted(c["canonical_name"] for c in merged)
    assert names == ["Netflx", "Stolovaya", "Яндекс Плюс"]
    net = next(c for c in merged if c["canonical_name"] == "Netflx")
    assert net["count"] == 3 and net["total_amount"] == 1797.0


def test_classify_all_expenses_heuristic_finds_known_services(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "unknown")
    monkeypatch.setenv("LLM_EMBEDDINGS", "0")
    txs = [
        {"date": f"2026-0{m}-05", "merchant": name, "amount": 550.0, "category": "", "mcc": None}
        for m, name in ((3, "РОСТЕЛЕКОМ"), (4, "RT.RU"), (5, "РОСТЕЛЕКОМ"))
    ] + [{"date": "2026-05-06", "merchant": "YANDEX TAXI", "amount": 420.0, "category": "Транспорт", "mcc": 4121}]
    clusters, subs = classify_all_expenses(txs)
    assert [s.service_name for s in subs] == ["Ростелеком"]
    assert subs[0].charges_count == 3
