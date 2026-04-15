from enum import Enum


class OccupationEnum(str, Enum):
    PATENT = "patent"
    EMPLOYED = "employed"
    SELF_EMPLOYED = "self_employed"
    IP = "ip"
    OTHER = "other"


class SourceEnum(str, Enum):
    MBANK = "mbank"
    ELSOM = "elsom"
    ODENGI = "o!dengi"
    BAKAI = "bakai"
    SIMBANK = "simbank"
    ELDIK = "eldik"
    KOMPANYON = "kompanion"
    DEMIR = "demir"
    RSK = "rsk"


class CurrencyEnum(str, Enum):
    KGS = "KGS"
    USD = "USD"
    EUR = "EUR"
    TL = "TL"


class TXNType(str, Enum):
    QR_PAYMENT = "qr_payment"
    CARD_PAYMENT = "card_payment"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
    TAX = "tax"
    FEE = "fee"
    CASH = "cash"
    LOAN_REPAYMENT = "loan_repayment"
    OTHER = "other"


class FraudFlagType(str, Enum):
    METADATA_MISMATCH = "metadata_mismatch"
    ROUND_AMOUNTS = "round_amounts"
    BALANCE_MISMATCH = "balance_mismatch"
    NIGHT_TRANSFERS = "night_transfers"
    CROSS_SOURCE_DUPLICATE = "cross_source_duplicate"
    DATE_ANOMALY = "date_anomaly"
    FREQUENCY_ANOMALY = "frequency_anomaly"


class FraudSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class JobStatus(str, Enum):
    PENDING = "pending"
    PARSING = "parsing"
    AGGREGATING = "aggregating"
    SCORING = "scoring"
    DONE = "done"
    FAILED = "failed"