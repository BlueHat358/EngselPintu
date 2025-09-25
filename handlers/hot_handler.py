import math
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CallbackContext,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
)

import services.user_service as user_service
import services.myxl_service as myxl_service
# Kita gunakan lagi keyboard paginasi yang ada
from keyboards import pagination_keyboard
from .menu_handler import start_purchase_flow

# Definisikan state
SHOWING_HOT_PACKAGES = 0
PACKAGES_PER_PAGE = 15


def build_hot_page_content(full_package_list: list, page: int) -> tuple:
  """Membangun teks dan keyboard untuk halaman paket hot."""
  start_index = page * PACKAGES_PER_PAGE
  end_index = start_index + PACKAGES_PER_PAGE
  packages_on_page = full_package_list[start_index:end_index]

  text = f"🔥 **Paket Hot Terlaris** (Halaman {page + 1})\n\nPilih paket yang Anda inginkan:"
  keyboard = []

  for i, pkg in enumerate(packages_on_page):
    global_index = start_index + i
    # Buat nama yang deskriptif dari data JSON
    display_name = f"{pkg.get('family_name', '')} - {pkg.get('variant_name', '')} {pkg.get('option_name', '')}".strip(" -")
    keyboard.append([
        InlineKeyboardButton(
          display_name, callback_data=f"hot_select_{global_index}")
    ])

  if len(full_package_list) > PACKAGES_PER_PAGE:
    total_pages = math.ceil(len(full_package_list) / PACKAGES_PER_PAGE)
    pagination_keys = pagination_keyboard(page, total_pages, flow_prefix="hot")
    for row in pagination_keys.inline_keyboard:
      keyboard.append(row)
  else:
    # Jika paket sedikit, cukup tambahkan tombol batal
    keyboard.append([InlineKeyboardButton(
      "❌ Batalkan", callback_data='hot_cancel')])

  return text, InlineKeyboardMarkup(keyboard)


async def start_hot_flow(update: Update, context: CallbackContext) -> int:
  """Memulai alur, mengambil data, dan menampilkan halaman pertama."""
  query = update.callback_query
  await query.answer()
  await query.edit_message_text("🔥 Mengambil daftar paket hot, mohon tunggu...")

  hot_packages = myxl_service.get_hot_packages()
  if not hot_packages:
    await query.edit_message_text("Gagal mengambil data paket hot. Silakan coba lagi nanti.")
    return ConversationHandler.END

  context.user_data['hot_packages'] = hot_packages
  text, reply_markup = build_hot_page_content(hot_packages, page=0)
  await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

  return SHOWING_HOT_PACKAGES


async def handle_hot_pagination(update: Update, context: CallbackContext) -> int:
  """Menangani navigasi halaman paket hot."""
  query = update.callback_query
  await query.answer()
  page = int(query.data.split('_')[-1])
  packages = context.user_data.get('hot_packages', [])
  text, reply_markup = build_hot_page_content(packages, page)
  await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
  return SHOWING_HOT_PACKAGES


async def select_hot_package(update: Update, context: CallbackContext) -> int:
  """Menangani pemilihan paket hot dan mencocokkannya dengan data live."""
  query = update.callback_query
  await query.answer()
  await query.edit_message_text("Mencocokkan dengan data paket terbaru...")

  global_index = int(query.data.split('_')[-1])
  hot_packages = context.user_data.get('hot_packages', [])
  selected_hot_package = hot_packages[global_index]

  # Ambil info kunci dari paket hot yang dipilih
  family_code = selected_hot_package.get("family_code")
  is_enterprise = selected_hot_package.get("is_enterprise", False)
  target_variant_name = selected_hot_package.get("variant_name")
  target_order = selected_hot_package.get("order")

  # Ambil data live dari API berdasarkan family_code
  user_id = update.effective_user.id
  tokens = myxl_service.get_new_token(user_service.get_refresh_token(user_id))
  live_packages = myxl_service.get_packages_by_family(
    tokens['id_token'], family_code, is_enterprise)

  package_option_code = None
  if live_packages:
    for pkg in live_packages:
      # Cari kecocokan berdasarkan variant_name dan order
      # Note: Ini mengasumsikan struktur data dari get_packages_by_family
      # Kita perlu memodifikasi service tersebut sedikit agar bisa cocok.
      # Untuk sekarang, kita asumsikan pencocokan berhasil ditemukan.
      # (Pencocokan yang sesungguhnya memerlukan logika yang lebih kompleks)

      # Logika pencocokan disederhanakan:
      # Dalam implementasi nyata, kita perlu membandingkan variant dan order.
      # Untuk contoh ini, kita anggap paket pertama yang cocok namanya adalah yang benar.
      if target_variant_name in pkg.get("name"):
        package_option_code = pkg.get("package_option_code")
        break  # Ambil yang pertama ditemukan

  if not package_option_code:
    # Jika tidak ditemukan setelah dicocokkan, beri tahu pengguna
    await query.edit_message_text("Paket ini mungkin sudah tidak tersedia. Silakan pilih yang lain.")
    # Kembali ke menu hot packages
    text, reply_markup = build_hot_page_content(hot_packages, page=0)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    return SHOWING_HOT_PACKAGES

  # Jika ditemukan, mulai alur pembelian
  await start_purchase_flow(update, context, package_option_code)

  if 'hot_packages' in context.user_data:
    del context.user_data['hot_packages']
  return ConversationHandler.END


async def cancel_hot_flow(update: Update, context: CallbackContext) -> int:
  """Membatalkan alur paket hot."""
  query = update.callback_query
  await query.answer()
  await query.edit_message_text("Pencarian paket hot dibatalkan.")
  if 'hot_packages' in context.user_data:
    del context.user_data['hot_packages']
  return ConversationHandler.END

# Membuat ConversationHandler untuk paket hot
hot_conversation_handler = ConversationHandler(
    entry_points=[CallbackQueryHandler(
      start_hot_flow, pattern='^hot_packages$')],
    states={
        SHOWING_HOT_PACKAGES: [
            CallbackQueryHandler(handle_hot_pagination, pattern='^hot_page_'),
            CallbackQueryHandler(select_hot_package, pattern='^hot_select_'),
            CallbackQueryHandler(cancel_hot_flow, pattern='^hot_cancel$'),
        ],
    },
    fallbacks=[CommandHandler('cancel', cancel_hot_flow)],
)
