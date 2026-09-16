import os
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

DEMO_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "statement_student_alexey.csv")


def test_parse_csv_comma_separator():
    """Тест CSV с запятой."""
    csv_content = "operationDate,merchant,amount,type\n15.01.2024,YANDEX,299,Списание".encode("utf-8")

    from app.services.parser import parse_csv
    df = parse_csv(csv_content)

    assert len(df) == 1
    assert df.iloc[0]["merchant"] == "YANDEX"


def test_parse_csv_semicolon_separator():
    """Тест CSV с точкой с запятой (демо-выписки)."""
    csv_content = "operationDate;merchant;amount;type\n15.01.2024;YANDEX;299;Списание".encode("utf-8")

    from app.services.parser import parse_csv
    df = parse_csv(csv_content)

    assert len(df) == 1
    assert df.iloc[0]["merchant"] == "YANDEX"


def test_analyze_endpoint_with_demo_file():
    """Сквозной тест с демо-выпиской (пропускается, если файла нет в data/)."""
    if not os.path.exists(DEMO_CSV_PATH):
        import pytest
        pytest.skip(f"Демо-файл не найден: {DEMO_CSV_PATH}")

    with open(DEMO_CSV_PATH, "rb") as f:
        response = client.post(
            "/api/v1/analyze",
            files={"file": ("test.csv", f, "text/csv")},
            data={"period": "6m"},
        )

    assert response.status_code == 200
    data = response.json()

    assert "subscriptions" in data
    assert "total_monthly_savings_potential" in data
    assert len(data["subscriptions"]) > 0


def test_transaction_date_is_string():
    """Тест, что даты конвертируются в строку."""
    from app.models import Transaction

    tx = Transaction(
        date="2024-01-15",
        amount=299.0,
        raw_description="YANDEX",
    )

    assert isinstance(tx.date, str)
