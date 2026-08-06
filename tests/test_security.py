from pydantic import SecretStr

from ai_workflow_lab.security import REDACTED, sanitize


def test_sanitize_redacts_sensitive_keys_and_values_recursively() -> None:
    secret = "sk-test-secret"
    value = {
        "headers": {"Authorization": f"Bearer {secret}", "X-Trace": secret},
        "nested": [{"api-key": secret}, f"request failed for {secret}"],
        "cookieJar": "session=abc",
        "safe": "visible",
    }

    result = sanitize(value, secrets=(secret,))

    assert result == {
        "headers": {"Authorization": REDACTED, "X-Trace": REDACTED},
        "nested": [{"api-key": REDACTED}, f"request failed for {REDACTED}"],
        "cookieJar": REDACTED,
        "safe": "visible",
    }


def test_sanitize_handles_secret_str_and_exception() -> None:
    result = sanitize(
        {"secret_value": SecretStr("hidden"), "error": RuntimeError("token hidden")},
        secrets=("hidden",),
    )

    assert isinstance(result, dict)
    assert result["secret_value"] == REDACTED
    assert result["error"] == {"type": "RuntimeError", "message": f"token {REDACTED}"}

