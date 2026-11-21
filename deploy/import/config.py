import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

API_URL = "https://localhost:8443/api"
SCRAPER_RESULTS_PATH = Path(__file__).resolve().parents[2] / "scraper-results"
LOGIN = (
    os.getenv("PS_WEBSERVICE_KEY"),
    "",
)  # API key as username, empty password

HOME_CATEGORY_ID = 2

TAX_RULES_GROUP_FOR_VAT_RATE = {23: 1, 8: 2, 5: 3, 0: 4}

RANDOM_SEED = 6112026


VARIANTS = {
    # kable sprzedawane na metry
    3848: {"Kolor": ["Czarny", "Czerwony", "Niebieski"]},  # HPC130 Przewód instrumentalny Proel
    3177: {"Kolor": ["Czarny", "Szary"]},  # HPC80 Kabel mikrofonowy instalacyjny Proel
    3842: {"Kolor": ["Czarny", "Czerwony"]},  # HPC620 Przewód kolumnowy 2x2,5mm2 Proel
    # pokrowce i nakrycia
    1146: {"Kolor": ["Czarny", "Niebieski", "Czerwony"]},  # UB-S Pokrowiec na ukulele sopranowe Ever Play
    1147: {"Kolor": ["Czarny", "Niebieski", "Czerwony"]},  # UB-C Pokrowiec na ukulele koncertowe Ever Play
    1148: {"Kolor": ["Czarny", "Niebieski", "Czerwony"]},  # UB-T Pokrowiec na ukulele tenorowe Ever Play
    3941: {"Kolor": ["Czarny", "Bordowy", "Granatowy"]},  # NK-4 Nakrycie na instrument klawiszowy Yaro
    3942: {"Kolor": ["Czarny", "Bordowy", "Granatowy"]},  # NK-3 Nakrycie na instrument klawiszowy Yaro
    3714: {"Kolor": ["Czarny", "Biały"]},  # USK-01 Statyw na ukulele
    # harmonijki chromatyczne
    3746: {"Tonacja": ["C", "G"], "Kolor": ["Czarny", "Złoty"]},  # CX12 Harmonijka chromatyczna Hohner
    3909: {"Tonacja": ["C", "G"]},  # Discovery 48 Harmonijka chromatyczna Hohner
    # struny
    6471: {"Rozmiar ukulele": ["Sopranowe", "Koncertowe", "Tenorowe"]},  # RS85 Struny do ukulele Rotosound
}

LOGGING_PATH = Path(__file__).parent

MAX_WORKERS = 8
TIMEOUT = 10
