from app.simulation import parse_simulation_header

KEY_IDS = ["key_1", "key_2", "key_3"]


def parse(header, enabled=True):
    return parse_simulation_header(header, key_ids=KEY_IDS, enabled=enabled)


def test_single_directive():
    assert parse("key_1=429") == {"key_1": 429}


def test_multiple_directives_and_whitespace():
    assert parse(" key_1 = 429 , key_2=500 ") == {
        "key_1": 429,
        "key_2": 500,
    }


def test_wildcard_expands_to_every_configured_key():
    assert parse("*=429") == {"key_1": 429, "key_2": 429, "key_3": 429}


def test_specific_directive_after_wildcard_wins():
    assert parse("*=500,key_2=429") == {
        "key_1": 500,
        "key_2": 429,
        "key_3": 500,
    }


def test_duplicate_key_last_directive_wins():
    assert parse("key_1=429,key_1=500") == {"key_1": 500}


def test_unknown_keys_and_malformed_pairs_are_ignored():
    assert parse("key_9=429,nonsense,=429,key_1,key_2=abc") == {}


def test_unsupported_status_codes_are_ignored():
    assert parse("key_1=400,key_2=418,key_3=503") == {"key_3": 503}


def test_empty_and_blank_headers_have_no_effect():
    assert parse(None) == {}
    assert parse("") == {}
    assert parse("   ") == {}


def test_disabled_flag_ignores_header_completely():
    assert parse("key_1=429,*=500", enabled=False) == {}


def test_all_supported_statuses_parse():
    for status in (429, 500, 502, 503):
        assert parse(f"key_1={status}") == {"key_1": status}


def test_extra_equals_signs_are_malformed():
    assert parse("key_1=429=500") == {}
