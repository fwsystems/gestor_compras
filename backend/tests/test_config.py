import pytest
from pydantic import ValidationError

from app.core.config import AppEnvironment, Settings


def test_invalid_environment_is_rejected() -> None:
    with pytest.raises(ValidationError, match="APP_ENV|app_env"):
        Settings(app_env="production", _env_file=None)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("environment", "expected_debug"),
    [
        (AppEnvironment.DEV, True),
        (AppEnvironment.HML, False),
        (AppEnvironment.PRD, False),
    ],
)
def test_debug_default_depends_on_environment(
    environment: AppEnvironment,
    expected_debug: bool,
) -> None:
    settings = Settings(app_env=environment, _env_file=None)
    assert settings.debug is expected_debug


def test_explicit_debug_value_is_preserved() -> None:
    settings = Settings(app_env=AppEnvironment.PRD, debug=True, _env_file=None)
    assert settings.debug is True


def test_invalid_debug_value_uses_environment_default() -> None:
    settings = Settings(
        app_env=AppEnvironment.PRD,
        debug="release",  # type: ignore[arg-type]
        _env_file=None,
    )
    assert settings.debug is False


def test_wildcard_cors_origin_is_rejected() -> None:
    with pytest.raises(ValidationError, match="wildcard"):
        Settings(cors_origins=["*"], _env_file=None)


def test_dev_starts_without_database_configuration() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_env is AppEnvironment.DEV
    assert settings.db_host is None
    assert settings.db_name is None
    assert settings.db_user is None
    assert settings.db_password is None
    assert settings.db_driver is None


def test_database_defaults_are_safe_and_bounded() -> None:
    settings = Settings(_env_file=None)

    assert settings.db_port == 1433
    assert settings.db_connect_timeout == 5
    assert settings.db_query_timeout == 30
    assert settings.db_encrypt is True
    assert settings.db_trust_server_certificate is False
    assert settings.db_application_intent_read_only is False
    assert settings.gestor_prd_read_only_validation is False


def test_database_boolean_options_are_parsed() -> None:
    settings = Settings(
        db_encrypt="no",  # type: ignore[arg-type]
        db_trust_server_certificate="yes",  # type: ignore[arg-type]
        db_application_intent_read_only="true",  # type: ignore[arg-type]
        gestor_prd_read_only_validation="true",  # type: ignore[arg-type]
        _env_file=None,
    )

    assert settings.db_encrypt is False
    assert settings.db_trust_server_certificate is True
    assert settings.db_application_intent_read_only is True
    assert settings.gestor_prd_read_only_validation is True


@pytest.mark.parametrize("suffix", ["010; DROP TABLE", "010_", "010 020"])
def test_invalid_protheus_table_suffix_is_rejected(suffix: str) -> None:
    with pytest.raises(ValidationError, match="DB_PROTHEUS_TABLE_SUFFIX"):
        Settings(db_protheus_table_suffix=suffix, _env_file=None)


def test_protheus_table_suffix_is_optional_and_normalized() -> None:
    assert Settings(db_protheus_table_suffix="", _env_file=None).db_protheus_table_suffix is None
    assert (
        Settings(db_protheus_table_suffix=" t10 ", _env_file=None).db_protheus_table_suffix
        == "T10"
    )
