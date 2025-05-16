import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("PNW_API_KEY")
if not API_KEY:
    raise ValueError("API key not found. Please set PNW_API_KEY in .env file.")

# Default raid target filters
MIN_INACTIVE_DAYS = 1  # 36 hours minimum inactive time to avoid counters
IGNORE_DNR = False  # If True, will show nations with alliances too (DNR = Do Not Raid)
MAX_PAGES = 10  # Maximum number of pages to fetch from the API

# Raid war specific settings (optimized for loot)
MIN_SCORE_RATIO = 0.75  # Can down-declare to 25% of your score for raid wars
MAX_SCORE_RATIO = 1.5  # Can up-declare to 150% of your score for raid wars

# Military requirements
MAX_SOLDIER_RATIO = 0.75  # Target must have less than 10% of your troops to minimize casualties
MAX_SPIES_RATIO = 5.0  # Target must have less than 100% of your spies to minimize losses

# Web app settings
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
