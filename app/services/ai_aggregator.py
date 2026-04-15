"""
AI-агрегация доходов: анализ транзакций через LLM (OpenAI / Gemini) или mock-режим.
Фильтрует входящие транзакции, группирует по месяцам, рассчитывает стабильность и тренд.
"""
import json
import logging
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional

from config import settings
from app.services.pdf_parser.base import RawTransaction

logger = logging.getLogger("depter")


@dataclass
class AggregationResult:
    avg_income_3m: float = 0.0
    avg_income_6m: float = 0.0
    income_by_month: Dict[str, float] = field(default_factory=dict)
    income_by_category: Dict[str, float] = field(default_factory=dict)
    stability_coefficient: float = 0.0   # 0.0 - 1.0
    income_trend: float = 0.0            # процент роста/снижения
    ai_explanation: str = ""


# Ключевые слова для исключения внутренних переводов
SELF_TRANSFER_KEYWORDS = [
    "перевод на себя", "перевод между", "пополнение счета",
    "пополнение карты", "own account", "between accounts",
    "перевод собственный", "внутренний перевод",
]


SYSTEM_PROMPT = """Ты финансовый аналитик. Тебе дают месячные данные о доходах заёмщика из Кыргызстана.
Твоя задача: рассчитать реальный средний доход, исключив разовые крупные поступления и
переводы между своими счетами. Отвечай только валидным JSON."""

USER_PROMPT_TEMPLATE = """
Транзакции (сгруппировано по месяцам):
{monthly_summary}

Верни JSON в формате:
{{
  "avg_income_3m": <среднее за последние 3 месяца>,
  "avg_income_6m": <среднее за 6 месяцев>,
  "stability": <коэффициент стабильности 0-1>,
  "income_trend": <тренд, например 0.05 = рост 5%>,
  "explanation": "краткое объяснение на русском"
}}
"""


class AIAggregator:
    """Агрегатор доходов с поддержкой нескольких AI-провайдеров."""

    def __init__(self):
        self.provider = settings.AI_PROVIDER

    async def aggregate(self, transactions: List[RawTransaction]) -> AggregationResult:
        """Главный метод: агрегирует транзакции и возвращает результат анализа."""
        # 1. Фильтруем только входящие (credit), исключаем внутренние переводы
        income_txns = self._filter_income(transactions)
        if not income_txns:
            logger.warning("Нет входящих транзакций для агрегации")
            return AggregationResult(ai_explanation="Входящие транзакции не найдены")

        # 2. Группируем по месяцам
        monthly = self._group_by_month(income_txns)

        # 3. Группируем по категориям
        categories = self._group_by_category(income_txns)

        # 4. Рассчитываем через AI или mock
        if self.provider == "openai":
            result = await self._aggregate_openai(monthly)
        elif self.provider == "gemini":
            result = await self._aggregate_gemini(monthly)
        else:
            # mock — статистический расчёт без LLM
            result = self._aggregate_mock(monthly)

        result.income_by_month = monthly
        result.income_by_category = categories

        return result

    def _filter_income(self, transactions: List[RawTransaction]) -> List[RawTransaction]:
        """Фильтрация: оставляем только входящие, исключаем внутренние переводы."""
        filtered = []
        for txn in transactions:
            if txn.direction != "credit":
                continue
            if txn.is_duplicate:
                continue
            # Исключаем переводы между своими счетами
            desc_lower = txn.description.lower() if txn.description else ""
            if any(kw in desc_lower for kw in SELF_TRANSFER_KEYWORDS):
                continue
            filtered.append(txn)

        logger.info(f"После фильтрации: {len(filtered)} входящих транзакций")
        return filtered

    def _group_by_month(self, transactions: List[RawTransaction]) -> Dict[str, float]:
        """Группировка суммы доходов по месяцам."""
        monthly = defaultdict(float)
        for txn in transactions:
            key = txn.txn_date.strftime("%Y-%m")
            # Приводим к KGS (упрощённо — считаем что amount уже в KGS)
            monthly[key] += txn.amount
        return dict(sorted(monthly.items()))

    def _group_by_category(self, transactions: List[RawTransaction]) -> Dict[str, float]:
        """Группировка по категориям транзакций."""
        categories = defaultdict(float)
        for txn in transactions:
            cat = txn.category or self._infer_category(txn.description)
            categories[cat] += txn.amount
        return dict(categories)

    @staticmethod
    def _infer_category(description: str) -> str:
        """Простая категоризация по описанию."""
        if not description:
            return "прочее"
        desc_lower = description.lower()

        category_map = {
            "торговля": ["торг", "продаж", "товар", "маркет", "магаз", "дордой", "базар"],
            "переводы": ["перевод", "p2p", "transfer"],
            "зарплата": ["зарплат", "salary", "оклад", "з/п"],
            "услуги": ["услуг", "service", "сервис"],
            "аренда": ["аренд", "rent", "найм"],
            "инвестиции": ["инвест", "дивиденд", "депозит", "процент"],
        }

        for cat, keywords in category_map.items():
            if any(kw in desc_lower for kw in keywords):
                return cat

        return "прочее"

    def _aggregate_mock(self, monthly: Dict[str, float]) -> AggregationResult:
        """Mock-режим: статистический расчёт без LLM."""
        if not monthly:
            return AggregationResult(ai_explanation="Нет данных для анализа")

        months_sorted = sorted(monthly.keys(), reverse=True)
        values = [monthly[m] for m in months_sorted]

        # Средний доход за 3 и 6 месяцев
        avg_3m = statistics.mean(values[:3]) if len(values) >= 1 else 0.0
        avg_6m = statistics.mean(values[:6]) if len(values) >= 1 else 0.0

        # Коэффициент стабильности: 1 - (stdev / mean), ограничен [0, 1]
        if len(values) >= 2 and avg_6m > 0:
            stdev = statistics.stdev(values[:6]) if len(values) >= 2 else 0
            stability = max(0.0, min(1.0, 1.0 - (stdev / avg_6m)))
        else:
            stability = 0.5

        # Тренд: (среднее последних 3 мес - среднее предыдущих 3 мес) / среднее предыдущих
        if len(values) >= 4:
            recent = statistics.mean(values[:3])
            older = statistics.mean(values[3:6]) if len(values) >= 6 else statistics.mean(values[3:])
            trend = (recent - older) / older if older > 0 else 0.0
        else:
            trend = 0.0

        explanation = (
            f"Mock-анализ: средний доход за 3 мес = {avg_3m:,.0f} KGS, "
            f"за 6 мес = {avg_6m:,.0f} KGS. "
            f"Стабильность = {stability:.2f}, тренд = {trend:+.1%}."
        )

        logger.info(f"Mock агрегация: avg_3m={avg_3m:.0f}, avg_6m={avg_6m:.0f}, stability={stability:.2f}")

        return AggregationResult(
            avg_income_3m=round(avg_3m, 2),
            avg_income_6m=round(avg_6m, 2),
            stability_coefficient=round(stability, 4),
            income_trend=round(trend, 4),
            ai_explanation=explanation,
        )

    async def _aggregate_openai(self, monthly: Dict[str, float]) -> AggregationResult:
        """Агрегация через OpenAI GPT."""
        try:
            import openai

            client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            prompt = USER_PROMPT_TEMPLATE.format(
                monthly_summary=json.dumps(monthly, ensure_ascii=False)
            )

            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=500,
            )

            content = response.choices[0].message.content.strip()
            # Убираем возможные markdown-обёртки
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]

            data = json.loads(content)
            logger.info(f"OpenAI агрегация: {data}")

            return AggregationResult(
                avg_income_3m=float(data.get("avg_income_3m", 0)),
                avg_income_6m=float(data.get("avg_income_6m", 0)),
                stability_coefficient=float(data.get("stability", 0.5)),
                income_trend=float(data.get("income_trend", 0)),
                ai_explanation=data.get("explanation", ""),
            )

        except Exception as e:
            logger.error(f"OpenAI ошибка, fallback на mock: {e}")
            return self._aggregate_mock(monthly)

    async def _aggregate_gemini(self, monthly: Dict[str, float]) -> AggregationResult:
        """Агрегация через Google Gemini."""
        try:
            import google.generativeai as genai

            genai.configure(api_key=settings.GOOGLE_API_KEY)
            model = genai.GenerativeModel("gemini-1.5-flash")

            prompt = (
                SYSTEM_PROMPT + "\n\n" +
                USER_PROMPT_TEMPLATE.format(
                    monthly_summary=json.dumps(monthly, ensure_ascii=False)
                )
            )

            response = await model.generate_content_async(prompt)
            content = response.text.strip()

            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]

            data = json.loads(content)
            logger.info(f"Gemini агрегация: {data}")

            return AggregationResult(
                avg_income_3m=float(data.get("avg_income_3m", 0)),
                avg_income_6m=float(data.get("avg_income_6m", 0)),
                stability_coefficient=float(data.get("stability", 0.5)),
                income_trend=float(data.get("income_trend", 0)),
                ai_explanation=data.get("explanation", ""),
            )

        except Exception as e:
            logger.error(f"Gemini ошибка, fallback на mock: {e}")
            return self._aggregate_mock(monthly)
