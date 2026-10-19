"""Production must not start with development-default or weak secrets; development stays unaffected."""

import pytest

from app.core.config import Settings

STRONG = "k9Qx2mV7pLr4Zt8WyB3nHd6Fs1JcUe5A"
GOOD = dict(ENVIRONMENT="production", JWT_SECRET_KEY=STRONG)
BAD = ["supersecretjwtkeyforauthservicelocaldvelopment12345", "short", ""]


def build(**over):
    return Settings(_env_file=None, **over)


def test_development_defaults_still_start():
    build()                                           # no ENVIRONMENT set: local development


def test_a_strong_production_configuration_starts():
    build(**GOOD)


@pytest.mark.parametrize("secret", BAD)
def test_production_refuses_default_weak_or_missing_jwt_secrets(secret):
    with pytest.raises(ValueError) as exc:
        build(**{**GOOD, "JWT_SECRET_KEY": secret})
    assert "JWT_SECRET_KEY" in str(exc.value)
    assert secret not in str(exc.value) or secret == ""            # the secret value is never echoed


def test_the_environment_name_is_case_insensitive():
    with pytest.raises(ValueError):
        build(**{**GOOD, "ENVIRONMENT": " Production ", "JWT_SECRET_KEY": "short"})


def test_gateway_verifies_the_token_issuer():
    import time

    import jwt

    from app.core.config import settings
    from app.services.jwt_service import jwt_service

    def mint(**claims):
        return jwt.encode({"sub": "u", "exp": int(time.time()) + 60, **claims}, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    assert jwt_service.decode_token(mint(iss=settings.JWT_ISSUER))["sub"] == "u"
    for bad in (mint(), mint(iss="https://evil.example.com")):        # missing / foreign issuer
        with pytest.raises(jwt.PyJWTError):
            jwt_service.decode_token(bad)
