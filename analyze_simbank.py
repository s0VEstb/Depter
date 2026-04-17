import json, logging, sys
logging.basicConfig(level=logging.WARNING)
from app.services.pdf_parser.base import parse_statement
from app.services.ai_scoring.math_metrics import calculate_fallback_metrics

with open(r'C:\Users\bEKA\Downloads\statements_VUqDPSvG_ru_ru.pdf', 'rb') as f:
    data = f.read()

result = parse_statement(data)
lines = []
lines.append(f'Parsed {len(result.transactions)} transactions from {result.source}')
lines.append('')
metrics = calculate_fallback_metrics(result.transactions)

lines.append('=== MATH-BASED METRICS ===')
for key in ('total_income', 'total_expense', 'avg_expense_monthly',
            'expense_to_income_ratio', 'net_cashflow_monthly',
            'overdraft_count', 'max_overdraft_amount', 'income_anomaly_detected'):
    lines.append(f'  {key}: {metrics[key]}')

lines.append('')
lines.append('=== COMPARISON ===')
expected = {
    'total_income': 21326.49,
    'total_expense': 21676.20,
    'avg_expense_monthly': 7225.40,
    'expense_to_income_ratio': 1.016,
    'net_cashflow_monthly': -116.57,
}
for key, exp_val in expected.items():
    actual = metrics[key]
    match = 'OK' if abs(actual - exp_val) < 1.0 else 'MISMATCH'
    lines.append(f'  {key}: actual={actual}, expected={exp_val} [{match}]')

lines.append(f'  overdraft_count: {metrics["overdraft_count"]} (should be >=3)')
lines.append(f'  income_anomaly: {metrics["income_anomaly_detected"]} (should be True)')

with open('verify_output.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print('Done')
