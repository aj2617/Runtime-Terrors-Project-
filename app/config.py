import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME = "GridWise Energy Optimizer"

    LLM_API_KEY = os.getenv("LLM_API_KEY", "")

    LLM_MODEL = os.getenv("LLM_MODEL", "")


settings = Settings()