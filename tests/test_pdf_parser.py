from pathlib import Path

from app.services.pdf_parser.base import parse_statement
from app.services.pdf_parser.parser_utils import _classify_category


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "pdf_parser"


def test_parse_statement_mbank_fixture():
    result = parse_statement((FIXTURES_DIR / "mbank_account_statement.pdf").read_bytes())

    assert result.source == "mbank"
    assert result.account_number == "1030120347430992"
    assert result.period_start.strftime("%Y-%m-%d") == "2026-01-01"
    assert result.period_end.strftime("%Y-%m-%d") == "2026-03-31"
    assert result.opening_balance == 9195.61
    assert result.closing_balance == 6828.44
    assert result.total_income == 84000.0
    assert result.total_expense == 86367.17
    assert len(result.transactions) == 177
    assert result.parse_errors == []


def test_parse_statement_simbank_fixture():
    result = parse_statement((FIXTURES_DIR / "statements_CV84OEY7_ru_ru.pdf").read_bytes())

    assert result.source == "simbank"
    assert result.client_name == "Эрмаматов Эрболот Эрмаматович"
    assert result.account_number == "402183****7911"
    assert result.period_start.strftime("%Y-%m-%d") == "2026-01-01"
    assert result.period_end.strftime("%Y-%m-%d") == "2026-04-01"
    assert result.opening_balance == 10470.19
    assert result.closing_balance == 17597.53
    assert result.total_income == 143362.33
    assert result.total_expense == 136169.99
    assert len(result.transactions) == 234
    assert result.parse_errors == []


def test_parse_statement_demir_fixture():
    result = parse_statement((FIXTURES_DIR / "demir_statement_q1_2026.pdf").read_bytes())

    assert result.source == "demir"
    assert result.client_name == "ЭРБОЛОТ ЭРМАМАТОВИЧ ЭРМАМАТОВ"
    assert result.account_number == "1180000247139739"
    assert result.inn == "22212200500079"
    assert result.period_start.strftime("%Y-%m-%d") == "2026-01-01"
    assert result.period_end.strftime("%Y-%m-%d") == "2026-03-31"
    assert result.opening_balance == 5251.56
    assert result.closing_balance == 1137.87
    assert result.total_income == 410603.6
    assert result.total_expense == 414717.29
    assert len(result.transactions) == 227
    assert result.parse_errors == []


def test_classify_category_patterns():
    assert _classify_category("Coffee house", "card_payment") == "food"
    assert _classify_category("Гипермаркет Globus", "card_payment") == "grocery"
    assert _classify_category("Комиссия за платеж", "fee") == "bank_fee"
    assert _classify_category("Перевод по номеру телефона", "transfer_in") == "income"
    assert _classify_category("Оплата в аптеке", "card_payment") == "healthcare"
    assert _classify_category("Megacom balance top up", "card_payment") == "telecom"
    assert _classify_category("Оплата домашнего интернета", "card_payment") == "internet"
    assert _classify_category("Пополнение карты Тулпар", "transfer_out") == "transport_topup"
    assert _classify_category("Перевод по QR", "qr_payment") == "other"
