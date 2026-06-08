from app.config import settings


def test_settings_has_database_url():
    assert settings.database_url is not None


def test_settings_has_api_keys():
    assert settings.football_data_api_key is not None
