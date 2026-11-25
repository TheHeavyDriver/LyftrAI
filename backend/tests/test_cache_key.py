from app.cache_key import build_cache_key

BASE = {
    "model": "gemini/gemini-3.5-flash-lite",
    "messages": [
        {"role": "system", "content": "Be concise."},
        {"role": "user", "content": "What is the capital of France?"},
    ],
    "temperature": 0.2,
    "max_output_tokens": 1024,
}


def key(**overrides):
    return build_cache_key(**{**BASE, **overrides})


def test_identical_inputs_produce_identical_keys():
    assert key() == key()


def test_different_model_misses():
    assert key(model="gemini/gemini-3.5-flash") != key()


def test_different_message_misses():
    messages = [
        BASE["messages"][0],
        {"role": "user", "content": "What is the capital of Italy?"},
    ]
    assert key(messages=messages) != key()


def test_different_history_misses():
    messages = [
        BASE["messages"][0],
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello"},
        BASE["messages"][1],
    ]
    assert key(messages=messages) != key()


def test_different_system_prompt_misses():
    messages = [
        {"role": "system", "content": "Answer in French."},
        BASE["messages"][1],
    ]
    assert key(messages=messages) != key()


def test_different_temperature_misses():
    assert key(temperature=0.7) != key()


def test_different_max_tokens_misses():
    assert key(max_output_tokens=512) != key()


def test_unicode_and_key_order_are_stable():
    messages = [
        {"role": "system", "content": "R\u00e9ponds bri\u00e8vement. \u2728"},
        {"role": "user", "content": "Caf\u00e9?"},
    ]
    first = key(messages=messages)
    second = key(
        messages=[
            {"content": "R\u00e9ponds bri\u00e8vement. \u2728", "role": "system"},
            {"content": "Caf\u00e9?", "role": "user"},
        ]
    )
    assert first == second


def test_key_is_prefixed_and_not_raw_content():
    value = key()
    assert value.startswith("lyftr:v1:")
    assert "France" not in value
    assert len(value) < 100


def test_message_order_matters():
    messages = list(reversed(BASE["messages"]))
    assert key(messages=messages) != key()
