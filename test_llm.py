"""Dump full Ollama response + test with format=json."""
import asyncio, json, time
from urllib import request

OLLAMA_URL = "http://192.168.23.6:11434/api/generate"

def test_raw():
    # Test 1: Simple prompt
    payload1 = {
        "model": "gemma4:e4b",
        "prompt": 'Ответь одним словом "Привет"',
        "stream": False,
    }
    print("=== TEST 1: Simple prompt ===")
    body = json.dumps(payload1).encode()
    req = request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.time()
    with request.urlopen(req, timeout=60) as r:
        raw = r.read().decode()
    print(f"Time: {time.time()-t0:.1f}s")
    result = json.loads(raw)
    print(f"Keys: {list(result.keys())}")
    print(f"response field: '{result.get('response', 'MISSING')}'")
    print(f"Full result: {json.dumps(result, ensure_ascii=False, indent=2)[:1000]}")

    # Test 2: JSON format with simpler prompt  
    payload2 = {
        "model": "gemma4:e4b",
        "prompt": 'Return a JSON object: {"score": 42, "message": "hello"}',
        "stream": False,
        "format": "json",
    }
    print("\n=== TEST 2: format=json ===")
    body = json.dumps(payload2).encode()
    req = request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.time()
    with request.urlopen(req, timeout=60) as r:
        raw = r.read().decode()
    print(f"Time: {time.time()-t0:.1f}s")
    result = json.loads(raw)
    print(f"response: '{result.get('response', 'MISSING')}'")

    # Test 3: Our actual prompt but with format=json
    from app.services.pdf_parser.base import parse_statement
    from app.services.ai_scoring.math_metrics import calculate_fallback_metrics
    from app.services.ai_scoring.llm_metrics import _build_llm_prompt

    with open(r'C:\Users\bEKA\Downloads\statements_VUqDPSvG_ru_ru.pdf', 'rb') as f:
        data = f.read()
    result_parse = parse_statement(data)
    fallback = calculate_fallback_metrics(result_parse.transactions)
    prompt = _build_llm_prompt(result_parse.transactions, fallback)

    payload3 = {
        "model": "gemma4:e4b",
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.3, "num_predict": 1024},
    }
    print(f"\n=== TEST 3: actual prompt + format=json ({len(prompt)} chars) ===")
    body = json.dumps(payload3).encode()
    req = request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.time()
    with request.urlopen(req, timeout=180) as r:
        raw = r.read().decode()
    elapsed = time.time() - t0
    print(f"Time: {elapsed:.1f}s")
    result = json.loads(raw)
    resp = result.get("response", "")
    print(f"Response length: {len(resp)} chars")
    print(f"Response: {resp[:500]}")

    with open('llm_raw_output.txt', 'w', encoding='utf-8') as f:
        f.write(json.dumps(result, ensure_ascii=False, indent=2))

test_raw()
