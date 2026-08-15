from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name:str="Revive_Script"
    app_env:str="Development"
    debug:bool=True

    database_url:str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str

    session_secret: str

    model_config=SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings=Settings()