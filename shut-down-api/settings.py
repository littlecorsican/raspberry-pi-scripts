import os
from pathlib import Path
from dotenv import load_dotenv

#load .env file if exists
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

#load api settings from env
PORT = int(os.environ.get("API_PORT", 8000))
DELAY_BEFORE_OFF = int(os.environ.get("DELAY_BEFORE_OFF", 2))

#load api auth settings from env
ENABLE_API_AUTH = os.environ.get("ENABLE_API_AUTH", "True").lower() in ('true', '1', 'yes')
API_KEY = os.environ.get("API_KEY", "")