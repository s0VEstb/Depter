import io
import logging
from datetime import datetime
from decimal import Decimal
import re
from typing import Optional

import pdfplumber

logger = logging.getLogger(__name__)

TELECOM_PATTERN = re.compile(
    r"(megacom|mega\b|beeline|o!|мегаком|сим[ -]?карт|мобильн\w*|связ\w*|balance)"
)
INTERNET_PATTERN = re.compile(
    r"(homeline|internet|интернет\w*|wifi|wi-fi|оптоволокн\w*|home ?line)"
)
HEALTHCARE_PATTERN = re.compile(
    r"(apteka|аптек\w*|медиц\w*|daryger|doctor|clinic|клиник\w*|hospital)"
)
TRANSPORT_PATTERN = re.compile(
    r"(тулпар\w*|tulpar|el\s?qr|pay24|проезд\w*|(?<!\w)bus(?!\w)|автобус\w*|transport)"
)
GROCERY_PATTERN = re.compile(
    r"(\bmarket\b|маркет\w*|гипермаркет\w*|gipermarket|магазин\w*|store\b|"
    r"supermarket|супермаркет\w*|sabina|bimar|globus)"
)
FOOD_PATTERN = re.compile(
    r"(\bcafe\b|каф[еэ]\w*|restaurant|ресторан\w*|coffee|кофе\w*|"
    r"lagman\w*|\bfood\b|\bеда\b|обед\w*|ужин\w*|завтрак\w*|fast[ -]?food|"
    r"столов\w*|doner|diner|pizza|burger|shawarma|шаурм\w*)"
)


def _clean_amount(raw: str) -> float:
    """'- 1 000,00' → -1000.0 | '+84 000,00' → 84000.0"""
    s = raw.strip().replace(" ", "").replace("\xa0", "")
    s = s.replace(",", ".")
    # знак может быть перед числом или отдельным символом
    negative = s.startswith("-")
    s = s.lstrip("+-").strip()
    try:
        val = float(s)
        return -val if negative else val
    except ValueError:
        return 0.0
    

def _parse_phone(text: str) -> Optional[str]:
    """Ищет 996XXXXXXXXX в строке описания"""
    m = re.search(r"99[67]\d{9}", text)
    return m.group(0) if m else None
 
 
def _parse_uuid(text: str) -> Optional[str]:
    """Ищет UUID типа 019b7874-301e-7333-aab8-1469b57efa37"""
    m = re.search(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        text, re.IGNORECASE
    )
    return m.group(0) if m else None
 
 
def _classify_txn(description: str, direction: str, source: str) -> str:
    """
    Возвращает TXNType value по описанию.
    Порядок важен — от специфичного к общему.
    """
    desc = description.lower()
 
    if any(x in desc for x in ["комиссия", "commission", "fee"]):
        return "fee"
    if any(x in desc for x in ["налог", "госпошлина", "нбкр", "tunduk", "госуслуги"]):
        return "tax"
    if any(x in desc for x in ["cash-in", "cashin", "кэшин", "наличн", "банкомат", "atm"]):
        return "cash"
    if any(x in desc for x in ["кредит", "loan", "рассрочка"]):
        return "loan_repayment"
    if "qr" in desc or "elqr" in desc:
        return "qr_payment"
    if any(x in desc for x in ["pos", "операции по карте", "покупка"]):
        return "card_payment"
    if direction == "in":
        return "transfer_in"
    if direction == "out":
        return "transfer_out"
    return "other"
 
 
def _classify_category(description: str, txn_type: str) -> str:
    """Категория для аналитики дохода"""
    desc = description.lower()

    if txn_type == "fee":
        return "bank_fee"
    if txn_type == "tax":
        return "government"
    if TELECOM_PATTERN.search(desc):
        return "telecom"
    if INTERNET_PATTERN.search(desc):
        return "internet"
    if HEALTHCARE_PATTERN.search(desc):
        return "healthcare"
    if TRANSPORT_PATTERN.search(desc):
        return "transport_topup"
    if GROCERY_PATTERN.search(desc):
        return "grocery"
    if FOOD_PATTERN.search(desc):
        return "food"
    if txn_type == "transfer_in" and "cash" not in desc:
        return "income"
    return "other"


def detect_bank(pdf_bytes: bytes) -> str:
    """
    Определяет банк по тексту первой страницы.
    Возвращает SourceEnum value.
    """
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        first_page_text = pdf.pages[0].extract_text() or ""
 
    # Отладка: логируем начало текста первой страницы для диагностики
    logger.info("detect_bank first_page text (500 chars): %s", first_page_text[:500])

    text = first_page_text.lower()
 
    # SimBank: проверяем много паттернов, т.к. реальные PDF могут не содержать слово "simbank"
    if (
        "simbank" in text
        or "дос-кредобанк" in text
        or "dos-credobank" in text
        or ("выписка по карте" in text and "имя клиента" in text)
        or ("номер карты клиента" in text)
        or ("остаток на начало периода" in text and "остаток на конец периода" in text)
    ):
        return "simbank"
    if (
        "demirbank" in text
        or "дкиб" in text
        or "демир" in text
        or "внешний номер счета" in text
        or "всего зачислено на счет" in text
    ):
        return "demir"
    if re.search(r"\bmbank\b", text) or "мбанк" in text or "mbank.kg" in text:
        return "mbank"
    if "элсом" in text or "elsom" in text:
        return "elsom"
    if "odengi" in text or "o!dengi" in text or "o!деньги" in text:
        return "o!"
    if "бакай" in text or "bakai" in text:
        return "bakai"
    if "элдик" in text or "eldik" in text:
        return "eldik"
    if "рск" in text or "rsk" in text:
        return "rsk"
    if "компаньон" in text or "kompanion" in text:
        return "kompanion"
 
    logger.warning("Банк не распознан, используется 'other'")
    return "other"
