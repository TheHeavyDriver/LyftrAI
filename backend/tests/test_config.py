import pytest
from pydantic import ValidationError

from app.config import ApiKey, Settings


def settings(**overrides):
    values = {
        "llm_api_keys": "alpha,beta,gamma",
        "allowed_origins": "http://localhost:3000,https://lyftr.example",
        "database_url": "sqlite:////data/app.db",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_keys_are_ordered_and_addressed_by_id():
    parsed = settings().api_key_pool
    assert [key.id for key in parsed] == ["key_1", "key_2", "key_3"]
    assert [key.value for key in parsed] == ["alpha", "beta", "gamma"]


def test_key_repr_never_contains_secret_material():
    key = ApiKey(id="key_1", value="super-secret")
    assert "super-secret" not in repr(key)
    assert "super-secret" not in str(key)


def test_blank_entries_are_ignored():
    parsed = settings(llm_api_keys=" alpha , , beta ").api_key_pool
    assert [key.value for key in parsed] == ["alpha", "beta"]


def test_fewer_than_two_keys_is_rejected():
    with pytest.raises(ValidationError, match="at least 2"):
        settings(llm_api_keys="only-one")


def test_duplicate_keys_are_rejected():
    with pytest.raises(ValidationError, match="duplicate"):
        settings(llm_api_keys="same,same")


def test_wildcard_origin_is_rejected():
    with pytest.raises(ValidationError, match="wildcard"):
        settings(allowed_origins="*")


def test_non_sqlite_database_is_rejected():
    with pytest.raises(ValidationError, match="SQLite"):
        settings(database_url="postgresql://user:pass@db/app")


def test_invalid_timeout_and_temperature_are_rejected():
    with pytest.raises(ValidationError):
        settings(key_attempt_timeout_seconds=0)
    with pytest.raises(ValidationError):
        settings(llm_temperature=3)
    with pytest.raises(ValidationError):
        settings(cache_ttl_seconds=0)


def test_origins_are_split_and_trimmed():
    assert settings().allowed_origins_list == [
        "http://localhost:3000",
        "https://lyftr.example",
    ]


def test_blank_default_prompt_is_rejected():
    with pytest.raises(ValidationError, match="DEFAULT_SYSTEM_PROMPT"):
        settings(default_system_prompt="   ")
