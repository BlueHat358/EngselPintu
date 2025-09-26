import logging
from logging.handlers import RotatingFileHandler
import os
import time
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from telegram.error import TelegramError

# Impor konfigurasi dan handler
import config
from handlers.menu_handler import (
  start, logout, placeholder_handler, show_my_packages, start_rebuy_flow,
  handle_overwrite_choice, handle_price_input, handle_payment_choice, show_main_menu,
  handle_ewallet_selection, handle_ewallet_number_input
)
from handlers.hot_handler import hot_conversation_handler
from handlers.family_handler import family_conversation_handler
from handlers.auth_handler import auth_conversation_handler

# Konfigurasi logging untuk debugging
log_file_path = os.path.expanduser('~/bot.log')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

formatter = logging.Formatter(
  '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

file_handler = RotatingFileHandler(
    log_file_path, maxBytes=3 * 1024 * 1024, backupCount=2)
file_handler.setFormatter(formatter)

if not logger.hasHandlers():
  logger.addHandler(console_handler)
  logger.addHandler(file_handler)


def main() -> None:
  """Fungsi utama untuk menjalankan bot."""
  # Buat aplikasi bot
  application = Application.builder().token(config.TELEGRAM_TOKEN).build()

  # Daftarkan handler
  # Perintah /start
  application.add_handler(CommandHandler("start", start))

  # Conversation handler untuk login
  application.add_handler(auth_conversation_handler)

  # Callback query handler untuk menu
  application.add_handler(CallbackQueryHandler(logout, pattern='^logout$'))

  # Handler sementara untuk tombol lain
  application.add_handler(CallbackQueryHandler(
    show_my_packages, pattern='^my_packages$'))
  # Tambahkan handler baru untuk aksi rebuy
  application.add_handler(CallbackQueryHandler(
    start_rebuy_flow, pattern='^rebuy_'))
  application.add_handler(CallbackQueryHandler(
    handle_overwrite_choice, pattern='^overwrite_'))
  application.add_handler(CallbackQueryHandler(
    handle_payment_choice, pattern='^pay_'))
  application.add_handler(CallbackQueryHandler(
    handle_ewallet_selection, pattern='^ewallet_select_'))
  application.add_handler(CallbackQueryHandler(
    handle_payment_choice, pattern='^cancel_purchase$'))  # Handler untuk batal
  application.add_handler(hot_conversation_handler)
  application.add_handler(family_conversation_handler)

  # Message handler untuk menerima input harga baru
  application.add_handler(MessageHandler(
    filters.TEXT & ~filters.COMMAND, handle_price_input))

  # Handler input nomor e-wallet harus didaftarkan SEBELUM handler input harga
  application.add_handler(MessageHandler(
    filters.TEXT & ~filters.COMMAND, handle_ewallet_number_input))  # <-- TAMBAHKAN INI
  application.add_handler(MessageHandler(
    filters.TEXT & ~filters.COMMAND, handle_price_input))

  # Mulai bot
  logger.info("Bot is starting...")
  application.run_polling()


if __name__ == '__main__':
  while True:  # 3. Buat loop tak terbatas
    try:
      # Jalankan fungsi main yang berisi logika bot
      main()

    except TelegramError as e:
      # Tangkap error spesifik jika koneksi internet putus
      logger.error(f"Koneksi internet terputus! Error: {e}")
      print("Koneksi internet terputus. Mencoba lagi dalam 15 detik...")
      # Tunggu sebentar sebelum mencoba menjalankan lagi
      time.sleep(15)

    except Exception as e:
      # Tangkap semua error lain yang mungkin terjadi agar bot tidak mati
      logger.error(f"Terjadi error tak terduga: {e}")
      print(f"Terjadi error tak terduga: {e}. Merestart bot dalam 30 detik...")
      # Tunggu lebih lama untuk error yang tidak diketahui
      time.sleep(30)
