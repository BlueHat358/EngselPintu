import math
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackContext,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)

import services.user_service as user_service
import services.myxl_service as myxl_service
from keyboards import pagination_keyboard
from .menu_handler import start_purchase_flow

# Definisikan state untuk conversation
ASKING_FAMILY_CODE, SHOWING_PACKAGES = range(2)
PACKAGES_PER_PAGE = 15


async def start_family_flow(update: Update, context: CallbackContext) -> int:
  """Memulai alur, meminta family code, dan MENDETEKSI TIPE (reguler/enterprise)."""
  query = update.callback_query
  await query.answer()

  # Cek apakah callback_data mengandung 'enterprise'
  is_enterprise = 'enterprise' in query.data
  # Simpan pilihan ini di memori untuk digunakan di langkah selanjutnya
  context.user_data['is_enterprise_flow'] = is_enterprise

  tipe_teks = "**Enterprise**" if is_enterprise else "**Reguler**"

  await query.edit_message_text(
      text=f"Anda memilih pencarian Family Code tipe {tipe_teks}.\n\n"
      "Silakan masukkan **Family Code** yang ingin Anda cari:",
      parse_mode='Markdown'
  )
  return ASKING_FAMILY_CODE


def build_page_content(full_package_list: list, page: int) -> tuple:
  """Membangun teks dan keyboard untuk halaman paket."""

  start_index = page * PACKAGES_PER_PAGE
  end_index = start_index + PACKAGES_PER_PAGE
  packages_on_page = full_package_list[start_index:end_index]

  if not packages_on_page:
    return "Tidak ada paket di halaman ini.", None

  text = f"📝 **Daftar Paket** (Halaman {page + 1})\n\n"
  keyboard = []

  for i, pkg in enumerate(packages_on_page):
    global_index = start_index + i
    price_formatted = f"Rp {pkg.get('price', 0):,}".replace(',', '.')

    # Tombol untuk setiap paket
    keyboard.append([
        InlineKeyboardButton(
            f"{pkg.get('name')} - {price_formatted}",
            callback_data=f"fam_select_{global_index}"
        )
    ])

  if len(full_package_list) > PACKAGES_PER_PAGE:
    total_pages = math.ceil(len(full_package_list) / PACKAGES_PER_PAGE)
    pagination_keys = pagination_keyboard(
        page, total_pages, flow_prefix="fam")
    for row in pagination_keys.inline_keyboard:
      keyboard.append(row)
  else:
    # Jika paket sedikit, cukup tambahkan tombol batal
    keyboard.append([InlineKeyboardButton(
      "❌ Batalkan", callback_data='fam_cancel')])

  return text, InlineKeyboardMarkup(keyboard)


async def received_family_code(update: Update, context: CallbackContext) -> int:
  """Menerima family code, mengambil data, dan menampilkan halaman pertama."""
  family_code = update.message.text.strip()
  await update.message.reply_text(f"⏳ Mencari paket untuk Family Code: `{family_code}`...", parse_mode='Markdown')

  user_id = update.effective_user.id
  refresh_token = user_service.get_refresh_token(user_id)
  tokens = myxl_service.get_new_token(refresh_token)

  if not tokens:
    await update.message.reply_text("Sesi Anda berakhir. Silakan /start ulang.")
    return ConversationHandler.END

  # Ambil pilihan yang tadi disimpan dari memori
  is_enterprise = context.user_data.get('is_enterprise_flow', False)

  # Gunakan pilihan tersebut saat memanggil service
  packages = myxl_service.get_packages_by_family(
      id_token=tokens['id_token'],
      family_code=family_code,
      is_enterprise=is_enterprise
  )

  if not packages:
    await update.message.reply_text("Paket tidak ditemukan atau Family Code salah. Coba lagi atau ketik /cancel.")
    return ASKING_FAMILY_CODE

  context.user_data['family_packages'] = packages

  text, reply_markup = build_page_content(packages, page=0)
  await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

  return SHOWING_PACKAGES


async def handle_pagination(update: Update, context: CallbackContext) -> int:
  """Menangani navigasi halaman."""
  query = update.callback_query
  await query.answer()

  page = int(query.data.split('_')[-1])
  packages = context.user_data.get('family_packages', [])

  if not packages:
    await query.edit_message_text("Data paket tidak ditemukan. Silakan mulai lagi.")
    return ConversationHandler.END

  text, reply_markup = build_page_content(packages, page)
  await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

  return SHOWING_PACKAGES


async def select_package(update: Update, context: CallbackContext) -> int:
  """Menangani saat pengguna memilih paket dari daftar."""
  query = update.callback_query
  await query.answer()

  global_index = int(query.data.split('_')[-1])
  packages = context.user_data.get('family_packages', [])

  if not packages or global_index >= len(packages):
    await query.edit_message_text("Paket yang dipilih tidak valid. Silakan mulai lagi.")
    return ConversationHandler.END

  selected_package = packages[global_index]
  package_option_code = selected_package['package_option_code']

  # Panggil alur pembelian yang sudah ada
  await start_purchase_flow(update, context, package_option_code=package_option_code)

  # Hapus data sementara setelah selesai
  if 'family_packages' in context.user_data:
    del context.user_data['family_packages']
  if 'family_code' in context.user_data:
    del context.user_data['family_code']

  return ConversationHandler.END


async def cancel_flow(update: Update, context: CallbackContext) -> int:
  """Membatalkan conversation."""
  query = update.callback_query
  if query:
    await query.answer()
    await query.edit_message_text("Pencarian paket dibatalkan.")
  else:
    await update.message.reply_text("Pencarian paket dibatalkan.")

  # Hapus data sementara
  if 'family_packages' in context.user_data:
    del context.user_data['family_packages']
  if 'family_code' in context.user_data:
    del context.user_data['family_code']

  return ConversationHandler.END

# Membuat ConversationHandler
family_conversation_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(
      start_family_flow, pattern='^buy_family_code$')],
    states={
        ASKING_FAMILY_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, received_family_code)],
        SHOWING_PACKAGES: [
            CallbackQueryHandler(handle_pagination, pattern='^fam_page_'),
            CallbackQueryHandler(select_package, pattern='^fam_select_'),
            CallbackQueryHandler(cancel_flow, pattern='^fam_cancel$'),
        ],
    },
    fallbacks=[CommandHandler('cancel', cancel_flow)],
)
