import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackContext,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
)

import services.user_service as user_service
import services.myxl_service as myxl_service

# Definisikan state yang benar
SHOWING_COMBOS, AWAITING_PAYMENT_CHOICE = range(2)


async def start_hot_2_flow(update: Update, context: CallbackContext) -> int:
  """Memulai alur, menampilkan daftar combo."""
  query = update.callback_query
  await query.answer()
  await query.edit_message_text("🔥 Mengambil daftar combo Hot 2...")

  combos = myxl_service.get_hot_packages_2()
  if not combos:
    await query.edit_message_text("Gagal mengambil data paket Hot 2.")
    return ConversationHandler.END

  context.user_data['hot_2_combos'] = combos

  keyboard = []
  for i, combo in enumerate(combos):
    # --- LOGIKA EKSTRAKSI HARGA DENGAN REGEX ---
    price_str = str(combo.get('price', '0'))  # Ambil harga sebagai string
    try:
      # 1. Temukan semua blok angka dalam string
      # Contoh: "Rp1000 (refund)" -> ['1000']
      digits = re.findall(r'\d+', price_str)

      # 2. Jika ada angka yang ditemukan, gabungkan dan ubah jadi integer
      if digits:
        price_int = int("".join(digits))
      else:
        price_int = 0
    except (ValueError, TypeError):
      price_int = 0

    price_formatted = f"Rp {price_int:,}".replace(',', '.')
    # --- AKHIR LOGIKA EKSTRAKSI ---

    keyboard.append([
        InlineKeyboardButton(
          f"{combo.get('name')} - {price_formatted}", callback_data=f"hot_2_combo_{i}")
    ])
  keyboard.append([InlineKeyboardButton(
    "❌ Batalkan", callback_data='hot_2_cancel')])

  await query.edit_message_text(
      "🔥 **Paket Hot 2**\n\nPilih salah satu combo di bawah ini:",
      reply_markup=InlineKeyboardMarkup(keyboard)
  )
  return SHOWING_COMBOS


async def select_combo(update: Update, context: CallbackContext) -> int:
  """Memproses combo, merakit item pembayaran, lalu menampilkan pilihan pembayaran."""
  query = update.callback_query
  await query.answer()
  await query.edit_message_text("⏳ Memproses semua sub-paket... Ini mungkin butuh waktu lama.")

  combo_index = int(query.data.split('_')[-1])
  selected_combo = context.user_data.get('hot_2_combos', [])[combo_index]
  sub_packages_to_resolve = selected_combo.get("packages", [])

  if not sub_packages_to_resolve:
    await query.edit_message_text("Combo ini tidak memiliki rincian paket.")
    return ConversationHandler.END

  # Ambil harga utama HANYA dari data combo
  total_price = 0
  try:
    price_str = str(selected_combo.get('price', '0'))
    digits = re.findall(r'\d+', price_str)
    total_price = int("".join(digits)) if digits else 0
  except (ValueError, TypeError):
    await query.edit_message_text("Gagal memproses harga combo.")
    return ConversationHandler.END

  user_id = update.effective_user.id
  tokens = myxl_service.get_new_token(user_service.get_refresh_token(user_id))

  payment_items = []
  for sub_pkg_info in sub_packages_to_resolve:
    details = myxl_service.get_package_details_from_hot_list(
      tokens['id_token'], sub_pkg_info)
    if not details:
      await query.edit_message_text(f"Gagal memproses salah satu sub-paket ({sub_pkg_info.get('family_code')}). Pembelian dibatalkan.")
      return ConversationHandler.END

    option = details['package_option']
    payment_items.append({
        "item_code": option['package_option_code'],
        "item_price": option['price'],
        "item_name": option['name'],
        "tax": 0
    })

  context.user_data['hot_2_payment_items'] = payment_items
  context.user_data['hot_2_total_price'] = total_price

  price_formatted = f"Rp {total_price:,}".replace(',', '.')
  text = (
      f"**Konfirmasi Pembelian Combo**\n\n"
      f"Nama: `{selected_combo.get('name')}`\n"
      f"Total Harga: `{price_formatted}`\n"
      f"Jumlah Item: `{len(payment_items)}`\n\n"
      f"Silakan pilih metode pembayaran:"
  )

  keyboard = [
      [InlineKeyboardButton("💳 Pulsa", callback_data='hot_2_pay_pulsa')],
      [InlineKeyboardButton("E-Wallet", callback_data='hot_2_pay_ewallet')],
      [InlineKeyboardButton("QRIS", callback_data='hot_2_pay_qris')],
      [InlineKeyboardButton("⬅️ Batal", callback_data='hot_2_cancel')]
  ]
  await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
  return AWAITING_PAYMENT_CHOICE


async def handle_hot_2_payment(update: Update, context: CallbackContext) -> int:
  """Menangani eksekusi pembayaran multi-paket."""
  query = update.callback_query
  await query.answer()

  method = query.data.split('_')[-1]
  payment_items = context.user_data.get('hot_2_payment_items')
  total_price = context.user_data.get('hot_2_total_price')
  tokens = myxl_service.get_new_token(
    user_service.get_refresh_token(update.effective_user.id))

  if method == 'pulsa':
    await query.edit_message_text(f"Memproses pembelian {len(payment_items)} item dengan pulsa...")
    result = myxl_service.purchase_multi_package_with_balance(
      tokens, payment_items, total_price)
    if result and result.get("status") == "SUCCESS":
      await query.edit_message_text(f"✅ **Berhasil!**\n\n{result.get('data', {}).get('message', 'Pembelian berhasil!')}")
    else:
      await query.edit_message_text(f"❌ **Gagal!**\n\nPesan: `{result.get('message', 'Terjadi kesalahan.')}`")

  elif method == 'qris':
    await query.edit_message_text(f"Membuat kode QRIS untuk {len(payment_items)} item...")
    success, data = myxl_service.generate_qris_payment_multi(
      tokens, payment_items, total_price)
    if success:
      await query.delete_message()
      await context.bot.send_photo(update.effective_chat.id, photo=data, caption=f"Pindai QRIS untuk membayar total Rp {total_price:,}.")
    else:
      await query.edit_message_text(f"**❌ Gagal membuat QRIS!**\n\n{data}", parse_mode='Markdown')

  elif method == 'ewallet':
    await query.edit_message_text("Memproses pembayaran E-Wallet...")
    result = myxl_service.initiate_ewallet_payment_multi(
      tokens, payment_items, total_price, "GOPAY")  # Default ke GoPay
    if result and result.get("status") == "SUCCESS":
      deeplink = result.get("data", {}).get("deeplink", "")
      await query.edit_message_text(f"✅ **Berhasil!**\n\nBuka [link ini]({deeplink}) untuk bayar.", parse_mode='Markdown')
    else:
      await query.edit_message_text(f"❌ **Gagal!**\n\nPesan: `{result.get('message', 'Error')}`", parse_mode='Markdown')

  # Hapus data sesi setelah selesai
  for key in ['hot_2_combos', 'hot_2_payment_items', 'hot_2_total_price']:
    if key in context.user_data:
      del context.user_data[key]

  return ConversationHandler.END


async def cancel_hot_2_flow(update: Update, context: CallbackContext) -> int:
  query = update.callback_query
  await query.answer()
  await query.edit_message_text("Pembelian paket Hot 2 dibatalkan.")
  for key in ['hot_2_combos', 'hot_2_payment_items', 'hot_2_total_price']:
    if key in context.user_data:
      del context.user_data[key]
  return ConversationHandler.END

hot_2_conversation_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(
      start_hot_2_flow, pattern='^hot_packages_2$')],
    states={
        SHOWING_COMBOS: [CallbackQueryHandler(select_combo, pattern='^hot_2_combo_')],
        AWAITING_PAYMENT_CHOICE: [CallbackQueryHandler(
          handle_hot_2_payment, pattern='^hot_2_pay_')]
    },
    fallbacks=[
        CallbackQueryHandler(cancel_hot_2_flow, pattern='^hot_2_cancel$'),
        CommandHandler('cancel', cancel_hot_2_flow)
    ],
)
