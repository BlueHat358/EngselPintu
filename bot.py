import logging
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

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
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


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
  main()
