"""
Configuration settings for Crop Insurance Backend
"""

import os
from datetime import timedelta

from dotenv import load_dotenv


# Load environment variables from backend/.env when present.
load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'crop-insurance-secret-key-2025'

    # Database
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DATABASE_PATH = os.path.join(BASE_DIR, 'database', 'crop_insurance.db')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # OpenWeatherMap API
    OPENWEATHER_API_KEY = os.environ.get('OPENWEATHER_API_KEY') or '86d5d1a0b91db3bf4b8db373571ffa5b'
    OPENWEATHER_BASE_URL = 'https://api.openweathermap.org/data/2.5'

    # ML Models Path
    MODELS_PATH = os.path.join(BASE_DIR, 'models')

    # Risk Thresholds (from training)
    DROUGHT_THRESHOLD = 804      # mm annual rainfall
    FLOOD_THRESHOLD = 1645       # mm annual rainfall
    HEATWAVE_TEMP = 38           # °C

    # NDVI Thresholds
    NDVI_HEALTHY_MIN = 0.5       # Healthy vegetation
    NDVI_STRESS_THRESHOLD = 0.35 # Below this = stress
    NDVI_SEVERE_THRESHOLD = 0.2  # Below this = severe damage
    NDVI_DROP_THRESHOLD = 0.3    # 30% drop = trigger

    # Insurance Settings
    MIN_PREMIUM = 1000           # Minimum premium in INR
    MAX_PAYOUT_MULTIPLIER = 10   # Max payout = 10x premium

    # Blockchain (Ganache defaults)
    GANACHE_URL = 'http://127.0.0.1:7545'
    CONTRACT_ADDRESS = '0x7CeC8594DAd1e481264ee1fd70DA19e10a147C18'      # Set after deployment

    # Earth Engine integration (disabled by default for local simulation mode)
    ENABLE_EE = os.environ.get('ENABLE_EE', 'false').lower() == 'true'
    EE_PROJECT = os.environ.get('EE_PROJECT')

    # Scheduler
    WEATHER_CHECK_INTERVAL = timedelta(hours=6)
    NDVI_CHECK_INTERVAL = timedelta(days=5)


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


# Active config
active_config = DevelopmentConfig()
