from telegram import Update
from telegram.ext import (
    CallbackContext,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)

from services import user_service, myxl_service
from .menu_handler import show_main_menu

# Definisikan state untuk conversation
ASKING_NUMBER, ASKING_OTP = range(2)


async def start_login(update: Update, context: CallbackContext) -> int:
  """Memulai alur login, meminta nomor telepon."""
  query = update.callback_query
  await query.answer()
  await query.edit_message_text(
      text="Silakan masukkan nomor XL Anda (format: 628...):"
  )
  return ASKING_NUMBER


async def received_number(update: Update, context: CallbackContext) -> int:
  """Menerima nomor telepon dan meminta OTP."""
  phone_number = update.message.text.strip()

  if not (phone_number.startswith("628") and phone_number.isdigit() and 10 <= len(phone_number) <= 14):
    await update.message.reply_text("Format nomor salah. Harap gunakan format 628... dan coba lagi.")
    return ASKING_NUMBER

  context.user_data['phone_number'] = phone_number

  await update.message.reply_text("Sedang meminta kode OTP, mohon tunggu...")

  subscriber_id = myxl_service.request_otp(phone_number)

  if subscriber_id:
    context.user_data['subscriber_id'] = subscriber_id
    await update.message.reply_text("OTP telah dikirim ke nomor Anda. Silakan masukkan 6 digit kode OTP:")
    return ASKING_OTP
  else:
    await update.message.reply_text("Gagal mengirim OTP. Pastikan nomor benar dan coba lagi nanti.")
    return ConversationHandler.END


async def received_otp(update: Update, context: CallbackContext) -> int:
  """Menerima OTP, memverifikasi, dan menyelesaikan login."""
  otp_code = update.message.text.strip()
  phone_number = context.user_data.get('phone_number')

  if not (otp_code.isdigit() and len(otp_code) == 6):
    await update.message.reply_text("Kode OTP tidak valid. Harap masukkan 6 digit angka.")
    return ASKING_OTP

  await update.message.reply_text("Memverifikasi OTP...")

  try:
    tokens = myxl_service.verify_otp(phone_number, otp_code)

    if tokens and 'refresh_token' in tokens:
      user_id = update.effective_user.id
      user_service.save_refresh_token(
          user_id, tokens['refresh_token'], phone_number)
      await update.message.reply_text("Login berhasil! 🎉")

      # Tampilkan menu utama
      await show_main_menu(update, context)

      return ConversationHandler.END
    else:
      await update.message.reply_text("Login gagal. Kode OTP salah atau telah kedaluwarsa.")
      return ConversationHandler.END
  except Exception as e:
    # Menangkap error dari API key yang tidak valid atau masalah lainnya
    print(f"Terjadi error saat verifikasi OTP: {e}")
    await update.message.reply_text(
        "Terjadi kesalahan di sisi server saat memverifikasi OTP. "
        "Ini mungkin karena konfigurasi API Key yang salah. Silakan hubungi admin bot."
    )
    return ConversationHandler.END


async def cancel(update: Update, context: CallbackContext) -> int:
  """Membatalkan proses login."""
  await update.message.reply_text("Proses login dibatalkan.")
  return ConversationHandler.END


# Membuat ConversationHandler untuk alur login
auth_conversation_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_login, pattern='^login_start$')],
    states={
        ASKING_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_number)],
        ASKING_OTP: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_otp)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
)
