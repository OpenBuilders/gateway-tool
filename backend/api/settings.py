from core.settings import CoreSettings


class ApiSettings(CoreSettings):
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiry: int = 3600
    sentry_dns: str

    internal_cdn_base_url: str


api_settings = ApiSettings()
