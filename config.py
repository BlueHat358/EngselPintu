# config.py
import os
from dotenv import load_dotenv

# Muat variabel dari file .env
load_dotenv()

# Ambil konfigurasi dengan nilai default jika tidak ada
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CRYPTO_API_KEY = os.getenv("CRYPTO_API_KEY")
MYXL_API_KEY = os.getenv("MYXL_API_KEY")
BASE_API_URL = os.getenv("BASE_API_URL")
BASE_CIAM_URL = os.getenv("BASE_CIAM_URL")
BASIC_AUTH = os.getenv("BASIC_AUTH")

UA = os.getenv("UA")

# Pastikan variabel penting sudah diisi
if not all([TELEGRAM_TOKEN, CRYPTO_API_KEY, MYXL_API_KEY, BASE_API_URL, BASE_CIAM_URL, BASIC_AUTH, UA]):
  raise ValueError(
    "Pastikan semua variabel di file .env sudah terisi dengan benar.")
