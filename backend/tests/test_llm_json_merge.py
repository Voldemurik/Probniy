from app.services.ai import _extract_json, _merge_llm_with_clusters, AIClusterResponse


def test_extract_json_handles_fences_and_prose():
    raw = 'Вот результат:\n```json\n{"clusters": [{"id": 0, "category": "subscription"}]}\n```\nГотово.'
    assert _extract_json(raw)["clusters"][0]["category"] == "subscription"
    assert _extract_json('[{"id": 1}]') == {"clusters": [{"id": 1}]}


def test_merge_fills_missing_clusters_and_keeps_our_sums():
    clusters = [
        {"canonical_name": "Яндекс Плюс", "merchant_variations": ["YANDEX PLUS"], "count": 6, "total_amount": 1794.0,
         "category_hint": "Видео", "mcc": None, "transactions": [{"amount": 299.0}] * 6},
        {"canonical_name": "Ozon", "merchant_variations": ["OZON"], "count": 1, "total_amount": 3028.77,
         "category_hint": "Маркетплейсы", "mcc": 5300, "transactions": [{"amount": 3028.77}]},
    ]
    items = [AIClusterResponse(id=0, category="subscription", canonical_name="яндекс плюс", total_amount=1.0,
                               transaction_count=1, is_subscription=True, cancellation_guide="Яндекс ID → Плюс")]
    merged = _merge_llm_with_clusters(items, clusters)
    assert [m.canonical_name for m in merged] == ["Яндекс Плюс", "Ozon"]
    assert merged[0].total_amount == 1794.0 and merged[0].transaction_count == 6 and merged[0].is_subscription
    assert merged[1].category == "marketplace" and not merged[1].is_subscription
