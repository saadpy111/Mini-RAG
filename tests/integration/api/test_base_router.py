from src.helpers.config import settings


def test_root_returns_standardized_success(client, assert_api_envelope):
    response = client.get("/api/v1/")

    body = assert_api_envelope(response, is_success=True, status_code=200)

    assert body["message"] == "Application information retrieved successfully."
    assert set(body["data"]) == {"APP_NAME", "APP_VERSION"}
    assert body["data"]["APP_NAME"] == settings.app_name
    assert body["data"]["APP_VERSION"] == settings.app_version
