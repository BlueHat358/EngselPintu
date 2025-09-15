# bot.py
from app.service.bookmark import BookmarkInstance
from app.service.auth import AuthInstance
from app.util import verify_id_username
import os
import logging
import math
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from app.client.engsel import (
    get_balance, get_family, get_package, get_otp, submit_otp, send_api_request,
    # TAMBAHKAN DUA FUNGSI DI BAWAH INI
    purchase_package, send_payment_request
)
from app.client.purchase import (
    get_payment_methods, show_multipayment, show_qris_payment
)

# Muat environment variables dari file .env
load_dotenv()

# Impor instance dan fungsi yang sudah ada dari skrip Anda
# Perhatikan kita mengimpor dari 'service' dan 'client', BUKAN dari 'menus'

# Konfigurasi logging untuk debugging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# State management sederhana untuk alur login
user_state = {}

# --- Helper Functions untuk Membuat Menu ---


async def build_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
  """Membangun dan mengirim menu utama."""
  is_auth = is_authenticated(update)
  if not is_auth:
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id, "Sesi tidak ditemukan atau token kedaluwarsa. Silakan kelola akun Anda.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👥 Kelola Akun", callback_data="manage_account")]]))
    return

  chat_id = update.effective_chat.id
  # Ini akan auto-refresh token jika perlu
  active_user = AuthInstance.get_active_user()

  if not active_user:
    await context.bot.send_message(chat_id, "Sesi tidak ditemukan atau token kedaluwarsa. Silakan kelola akun Anda.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👥 Kelola Akun", callback_data="manage_account")]]))
    return

  balance_info = get_balance(
    AuthInstance.api_key, active_user["tokens"]["id_token"])
  balance_remaining = balance_info.get(
    "remaining", "N/A") if balance_info else "Gagal memuat"

  text = (
      f"👤 **Informasi Akun**\n"
      f"Nomor: `{active_user['number']}`\n"
      f"Sisa Pulsa: `Rp {balance_remaining}`\n\n"
      "Pilih menu di bawah ini:"
  )

  keyboard = [
      [InlineKeyboardButton("💳 Lihat Paket Saya",
                            callback_data="my_packages")],
      [InlineKeyboardButton(
          "🔥 Beli Paket XUT", callback_data="packages_xut:08a3b1e6-8e78-4e45-a540-b40f06871cfe:false")],
      [InlineKeyboardButton("🔍 Beli Paket (Family Code)",
                            callback_data="ask_family_code:false")],
      [InlineKeyboardButton("🏢 Beli Paket (Enterprise)",
                            callback_data="ask_family_code:true")],
      [InlineKeyboardButton("❤️ Bookmark", callback_data="bookmarks_menu")],
      [InlineKeyboardButton("👥 Ganti/Kelola Akun",
                            callback_data="manage_account")],
    ]
  reply_markup = InlineKeyboardMarkup(keyboard)

  # Kirim atau edit pesan menu
  try:
    # Pesan utama disimpan di context.user_data untuk diedit
    message_id = context.user_data.get('main_message_id')
    if message_id:
      await context.bot.edit_message_text(
          chat_id=chat_id, message_id=message_id, text=text,
          reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN
      )
    else:
      raise ValueError("No message to edit")
  except Exception:
    message = await context.bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    context.user_data['main_message_id'] = message.message_id


async def build_account_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
  """Membangun menu pengelolaan akun."""
  is_auth = is_authenticated(update)
  if not is_auth:
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id, "Sesi tidak ditemukan atau token kedaluwarsa. Silakan kelola akun Anda.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👥 Kelola Akun", callback_data="manage_account")]]))
    return

  chat_id = update.effective_chat.id
  AuthInstance.load_tokens()
  users = AuthInstance.refresh_tokens
  active_user = AuthInstance.get_active_user()

  text = "👥 **Akun Tersimpan**\n\nPilih akun untuk dijadikan aktif atau kelola akun Anda:"
  keyboard = []

  if not users:
    text = "Tidak ada akun tersimpan."
  else:
    for user in users:
      is_active = active_user and user["number"] == active_user["number"]
      active_marker = " ✅" if is_active else ""
      keyboard.append([InlineKeyboardButton(
        f"{user['number']}{active_marker}", callback_data=f"set_active:{user['number']}")])

  keyboard.append([InlineKeyboardButton(
    "➕ Tambah Akun Baru", callback_data="add_account")])
  if active_user:
    keyboard.append([InlineKeyboardButton("❌ Hapus Akun Aktif",
                    callback_data=f"remove_account_confirm:{active_user['number']}")])

  if AuthInstance.get_active_user():
    keyboard.append([InlineKeyboardButton(
      "⬅️ Kembali", callback_data="main_menu")])

  reply_markup = InlineKeyboardMarkup(keyboard)

  await context.bot.edit_message_text(
      chat_id=chat_id, message_id=context.user_data.get('main_message_id'),
      text=text, reply_markup=reply_markup
  )


async def show_my_packages(update: Update, context: ContextTypes.DEFAULT_TYPE):
  """Mengambil dan menampilkan daftar paket aktif pengguna."""
  is_auth = is_authenticated(update)
  if not is_auth:
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id, "Sesi tidak ditemukan atau token kedaluwarsa. Silakan kelola akun Anda.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👥 Kelola Akun", callback_data="manage_account")]]))
    return

  query = update.callback_query

  await query.edit_message_text(text="⏳ Sedang mengambil daftar paket Anda...")

  active_user = AuthInstance.get_active_user()
  if not active_user:
    await query.edit_message_text(text="Sesi tidak valid. Silakan /start ulang.")
    return

  path = "api/v8/packages/quota-details"
  payload = {"is_enterprise": False, "lang": "en", "family_member_id": ""}

  res = send_api_request(
      api_key=AuthInstance.api_key, path=path, payload_dict=payload,
      id_token=active_user["tokens"]["id_token"], method="POST"
  )

  if res.get("status") != "SUCCESS" or "data" not in res or not res["data"].get("quotas"):
    await query.edit_message_text(
        text="Gagal mengambil data paket atau Anda tidak memiliki paket aktif.",
        reply_markup=InlineKeyboardMarkup(
          [[InlineKeyboardButton("⬅️ Kembali", callback_data="main_menu")]])
    )
    return

  quotas = res["data"]["quotas"]
  message_text = "💳 **Paket Aktif Anda:**\n\n"
  keyboard = []

  # PERUBAHAN UTAMA: Gunakan map untuk menyimpan quota_code yang panjang
  package_map = {}

  for i, quota in enumerate(quotas, 1):
    name = quota.get('name', 'N/A')
    quota_code = quota.get('quota_code')

    message_text += f"**{i}. {name}**\n\n"

    if quota_code:
      # Simpan quota_code ke map dengan key berupa nomor urut
      package_map[str(i)] = quota_code
      # Tombol sekarang hanya berisi ID singkat (nomor urut)
      keyboard.append([
          InlineKeyboardButton(
            f"➡️ Lihat Detail: {name}", callback_data=f"show_detail:{i}")
      ])

  # Simpan map ke context agar bisa diakses nanti saat tombol ditekan
  context.user_data['package_map'] = package_map

  keyboard.append([InlineKeyboardButton(
    "⬅️ Kembali ke Menu Utama", callback_data="main_menu")])
  reply_markup = InlineKeyboardMarkup(keyboard)

  await query.edit_message_text(
      text=message_text,
      reply_markup=reply_markup,
      parse_mode=ParseMode.MARKDOWN
  )


async def show_package_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, package_code: str):
  """Mengambil dan menampilkan detail dari satu paket beserta opsi pembelian."""
  is_auth = is_authenticated(update)
  if not is_auth:
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id, "Sesi tidak ditemukan atau token kedaluwarsa. Silakan kelola akun Anda.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👥 Kelola Akun", callback_data="manage_account")]]))
    return

  query = update.callback_query
  await query.edit_message_text(text=f"⏳ Mengambil detail untuk paket...")

  active_user = AuthInstance.get_active_user()
  if not active_user:
    await query.edit_message_text(text="Sesi tidak valid. Silakan /start ulang.")
    return

  package_data = get_package(
      api_key=AuthInstance.api_key,
      tokens=active_user["tokens"],
      package_option_code=package_code
  )

  if not package_data:
    await query.edit_message_text(
        "Gagal mengambil detail paket.",
        reply_markup=InlineKeyboardMarkup(
          [[InlineKeyboardButton("⬅️ Kembali", callback_data="my_packages")]])
    )
    return

  # Ekstrak informasi penting untuk transaksi
  option = package_data.get("package_option", {})
  family = package_data.get("package_family", {})
  variant = package_data.get("package_detail_variant", {})

  title = f"{variant.get('name', '')} {option.get('name', '')}".strip()
  price = option.get("price", 0)
  validity = option.get("validity", "N/A")
  token_confirmation = package_data.get("token_confirmation")

  # Simpan data transaksi sementara di context.user_data
  context.user_data['purchase_info'] = {
      'package_code': package_code,
      'item_name': title,
      'price': price,
      'token_confirmation': token_confirmation,
      'payment_for': family.get('payment_for', 'BUY_PACKAGE')
  }

  message_text = (
      f"📦 **Detail Paket**\n\n"
      f"**Nama:** {title}\n"
      f"**Harga:** `Rp {price}`\n"
      f"**Masa Aktif:** {validity}\n\n"
      "Pilih metode pembayaran:"
  )

  keyboard = [
      [InlineKeyboardButton("💰 Beli dengan Pulsa",
                            callback_data="ask_override:pulsa")],
      [InlineKeyboardButton("💳 Beli dengan E-Wallet",
                            callback_data="ask_override:ewallet")],
      [InlineKeyboardButton("📱 Bayar dengan QRIS",
                            callback_data="ask_override:qris")],
      [InlineKeyboardButton("⬅️ Kembali ke Daftar Paket",
                            callback_data="my_packages")]
  ]
  reply_markup = InlineKeyboardMarkup(keyboard)

  await query.edit_message_text(text=message_text, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)


async def build_bookmark_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
  """Membangun menu bookmark."""
  is_auth = is_authenticated(update)
  if not is_auth:
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id, "Sesi tidak ditemukan atau token kedaluwarsa. Silakan kelola akun Anda.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👥 Kelola Akun", callback_data="manage_account")]]))
    return

  chat_id = update.effective_chat.id
  bookmarks = BookmarkInstance.get_bookmarks()
  text = "❤️ **Bookmark Paket**\n\nPilih bookmark untuk melihat detail paket."
  keyboard = []

  if not bookmarks:
    text = "Anda belum memiliki bookmark."
  else:
    for i, bm in enumerate(bookmarks):
      # Membuat nama yang lebih deskriptif
      label = f"{bm['variant_name']} {bm['option_name']}".strip()
      # Callback data akan berisi index dari bookmark untuk memudahkan penghapusan
      keyboard.append([
          InlineKeyboardButton(
            label, callback_data=f"buy_family:{bm['family_code']}:{str(bm['is_enterprise']).lower()}"),
          InlineKeyboardButton("🗑️", callback_data=f"remove_bookmark:{i}")
      ])

  keyboard.append([InlineKeyboardButton(
    "⬅️ Kembali", callback_data="main_menu")])
  reply_markup = InlineKeyboardMarkup(keyboard)
  await context.bot.edit_message_text(
      chat_id=chat_id, message_id=context.user_data.get('main_message_id'),
      text=text, reply_markup=reply_markup
  )


#  --- Payments Methods ---

async def execute_purchase_with_pulsa(update: Update, context: ContextTypes.DEFAULT_TYPE):
  """Fungsi akhir untuk mengeksekusi pembelian dengan pulsa."""
  is_auth = is_authenticated(update)
  if not is_auth:
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id, "Sesi tidak ditemukan atau token kedaluwarsa. Silakan kelola akun Anda.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👥 Kelola Akun", callback_data="manage_account")]]))
    return

  query = update.callback_query
  await query.edit_message_text("⏳ Memproses pembelian dengan pulsa...")

  active_user = AuthInstance.get_active_user()
  purchase_info = context.user_data.get('purchase_info', {})

  if not active_user or not purchase_info:
    await query.edit_message_text("Sesi pembelian tidak valid. Silakan ulangi dari awal.")
    return

  # Panggil fungsi purchase_package yang sudah ada
  # Fungsi ini sudah menangani semua logika, termasuk membuat payload dan mengirim request
  # Kita hanya perlu memastikan semua argumennya benar
  try:
    purchase_result = purchase_package(
        api_key=AuthInstance.api_key,
        tokens=active_user['tokens'],
        package_option_code=purchase_info['package_code'],
        # Kita set is_enterprise ke False sebagai default
        is_enterprise=False,
        # Berikan harga override jika ada
        price_override=purchase_info.get('override_amount')
    )

    # Hapus info pembelian setelah selesai
    del context.user_data['purchase_info']

    if purchase_result and purchase_result.get("status") == "SUCCESS":
      message = "✅ Pembelian berhasil! Silakan cek aplikasi MyXL Anda."
    else:
      error_msg = purchase_result.get('message', 'Alasan tidak diketahui.')
      message = f"❌ Pembelian Gagal.\n\nAlasan: `{error_msg}`"

  except Exception as e:
    logger.error(f"Error during pulsa purchase: {e}")
    message = f"❌ Terjadi error saat memproses pembelian: {e}"

  keyboard = [[InlineKeyboardButton(
    "⬅️ Kembali ke Menu Utama", callback_data="main_menu")]]
  await query.edit_message_text(text=message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)


# --- Family Methods ---

# GANTI FUNGSI LAMA DENGAN VERSI BARU INI DI bot.py

async def display_packages_from_family(update: Update, context: ContextTypes.DEFAULT_TYPE, family_code: str, is_enterprise: bool, page: int = 1):
  """Mengambil dan menampilkan daftar paket dari family code tertentu dengan sistem halaman."""
  query = update.callback_query

  # Menampilkan pesan loading
  if query:
    await query.edit_message_text(f"⏳ Mencari paket... (Halaman {page})", parse_mode=ParseMode.MARKDOWN)
  else:
    await update.message.reply_text(f"⏳ Mencari paket...", parse_mode=ParseMode.MARKDOWN)

  active_user = AuthInstance.get_active_user()
  if not active_user:
    await (query or update.message).reply_text("Sesi tidak valid. Silakan /start ulang.")
    return

  # --- Logika Caching untuk Pagination ---
  # Cek apakah daftar paket sudah ada di cache untuk family code ini
  cached_packages = context.user_data.get('family_packages', {})
  if cached_packages.get('family_code') != family_code:
    # Jika family code berbeda, panggil API dan buat cache baru
    family_data = get_family(
        api_key=AuthInstance.api_key, tokens=active_user['tokens'],
        family_code=family_code, is_enterprise=is_enterprise
    )
    if not family_data or not family_data.get("package_variants"):
      error_text = f"Tidak ditemukan paket untuk family code `{family_code}` atau kode tidak valid."
      await (query.edit_message_text if query else update.message.reply_text)(
          text=error_text,
          reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Kembali", callback_data="main_menu")]]),
          parse_mode=ParseMode.MARKDOWN
      )
      return

    # Proses dan simpan hasil API ke dalam list yang lebih sederhana
    all_packages = []
    for variant in family_data["package_variants"]:
      for option in variant["package_options"]:
        all_packages.append({
            'name': option.get("name"), 'price': option.get("price"),
            'code': option.get("package_option_code")
        })

    context.user_data['family_packages'] = {
      'family_code': family_code, 'packages': all_packages}

  # Ambil daftar paket dari cache
  all_packages = context.user_data['family_packages']['packages']

  # --- Logika Pagination ---
  page_size = 20
  total_packages = len(all_packages)
  total_pages = math.ceil(total_packages / page_size)

  start_index = (page - 1) * page_size
  end_index = start_index + page_size
  packages_on_page = all_packages[start_index:end_index]

  family_name = "Daftar Paket"  # Nama generik
  message_text = f"📦 **{family_name}** — Halaman **{page}** dari **{total_pages}**\n\nPilih paket yang tersedia:"
  keyboard = []

  package_map = {}
  for i, pkg in enumerate(packages_on_page, start=start_index):
    if all(pkg.get(k) for k in ['name', 'price', 'code']):
      label = f"{pkg['name']} - Rp {pkg['price']}"
      map_key = str(i)
      package_map[map_key] = pkg['code']
      keyboard.append([InlineKeyboardButton(
        label, callback_data=f"show_detail:{map_key}")])

  context.user_data['package_map'] = package_map

  # --- Membuat Tombol Navigasi ---
  nav_buttons = []
  if page > 1:
    nav_buttons.append(InlineKeyboardButton(
      "⬅️ Sebelumnya", callback_data=f"family_page:{family_code}:{is_enterprise}:{page - 1}"))
  if page < total_pages:
    nav_buttons.append(InlineKeyboardButton(
      "Berikutnya ➡️", callback_data=f"family_page:{family_code}:{is_enterprise}:{page + 1}"))

  if nav_buttons:
    keyboard.append(nav_buttons)

  keyboard.append([InlineKeyboardButton(
    "⬅️ Kembali ke Menu Utama", callback_data="main_menu")])
  reply_markup = InlineKeyboardMarkup(keyboard)

  # Kirim atau edit pesan
  if query:
    await query.edit_message_text(message_text, reply_markup=reply_markup)
  else:
    await update.message.reply_text(message_text, reply_markup=reply_markup)

# --- Command & Message Handlers ---


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
  """Handler untuk command /start."""
  is_auth = is_authenticated(update)
  if not is_auth:
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id, "Sesi tidak ditemukan atau token kedaluwarsa. Silakan kelola akun Anda.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👥 Kelola Akun", callback_data="manage_account")]]))
    return

  # Hapus pesan sebelumnya untuk memulai sesi bersih
  context.user_data.clear()

  AuthInstance.load_tokens()
  active_user = AuthInstance.get_active_user()

  if is_auth:
    await context.bot.send_message(update.effective_chat.id, "Selamat datang kembali!")
    await build_main_menu(update, context)
  else:
    keyboard = [[InlineKeyboardButton(
      "➕ Login / Tambah Akun", callback_data="add_account")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = await context.bot.send_message(
        update.effective_chat.id,
        "Selamat datang! Anda belum memiliki akun. Silakan login terlebih dahulu.",
        reply_markup=reply_markup
    )
    context.user_data['main_message_id'] = message.message_id


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
  """Menangani pesan teks biasa, terutama untuk alur login & input family code."""
  is_auth = is_authenticated(update)
  if not is_auth:
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id, "Sesi tidak ditemukan atau token kedaluwarsa. Silakan kelola akun Anda.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👥 Kelola Akun", callback_data="manage_account")]]))
    return

  chat_id = update.effective_chat.id
  text = update.message.text.strip()
  current_state = user_state.get(chat_id)

  if current_state == "WAITING_FOR_PHONE":
    if not text.startswith("628") or len(text) < 10:
      await update.message.reply_text("Nomor tidak valid. Coba lagi (contoh: 628123...).")
      return

    await update.message.reply_text("Meminta OTP...")
    context.user_data['login_phone'] = text

    if get_otp(text):
      await update.message.reply_text("OTP telah dikirim. Silakan masukkan 6 digit kode OTP:")
      user_state[chat_id] = "WAITING_FOR_OTP"
    else:
      await update.message.reply_text("Gagal mengirim OTP. Silakan coba lagi nanti.")
      del user_state[chat_id]

  elif current_state == "WAITING_FOR_OTP":
    phone_number = context.user_data.get('login_phone')
    if not text.isdigit() or len(text) != 6:
      await update.message.reply_text("Format OTP salah. Harus 6 digit angka. Coba lagi.")
      return

    await update.message.reply_text("Memverifikasi OTP...")
    tokens = submit_otp(AuthInstance.api_key, phone_number, text)

    if tokens:
      AuthInstance.add_refresh_token(
        int(phone_number), tokens["refresh_token"])
      AuthInstance.set_active_user(int(phone_number))
      await update.message.reply_text("✅ Login berhasil!")

      del user_state[chat_id]
      del context.user_data['login_phone']
      await build_main_menu(update, context)  # Langsung ke menu utama
    else:
      await update.message.reply_text("❌ Gagal login. OTP salah. Coba masukkan lagi.")

  elif current_state == "WAITING_FOR_PRICE_OVERRIDE":
    try:
      override_amount = int(text)
      purchase_info = context.user_data.get('purchase_info', {})
      payment_method = purchase_info.get('payment_method')

      # Simpan harga override
      context.user_data['purchase_info']['override_amount'] = override_amount

      # Hapus state agar tidak menunggu input lagi
      del user_state[chat_id]

      if payment_method == "pulsa":
        await execute_purchase_with_pulsa(update, context)
      else:
        await update.message.reply_text(f"Metode pembayaran {payment_method} belum diimplementasikan.")

    except ValueError:
      await update.message.reply_text("Input tidak valid. Harap masukkan angka saja.")
    except Exception as e:
      await update.message.reply_text(f"Terjadi error: {e}")

  elif current_state == "WAITING_FOR_FAMILY_CODE":
    family_code = text.strip()
    is_enterprise = context.user_data.get('is_enterprise_request', False)

    # Hapus state dan cache lama
    if chat_id in user_state:
      del user_state[chat_id]
    if 'is_enterprise_request' in context.user_data:
      del context.user_data['is_enterprise_request']
    context.user_data.pop('family_packages', None)  # Hapus cache

    # Panggil fungsi yang baru kita buat dengan halaman 1
    await display_packages_from_family(update, context, family_code, is_enterprise, page=1)


# --- Callback Query Handler (INTI DARI BOT) ---

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
  """Menangani semua klik tombol."""
  is_auth = is_authenticated(update)
  if not is_auth:
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id, "Sesi tidak ditemukan atau token kedaluwarsa. Silakan kelola akun Anda.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("👥 Kelola Akun", callback_data="manage_account")]]))
    return

  query = update.callback_query
  await query.answer()
  data = query.data
  chat_id = update.effective_chat.id

  logger.info(f"Callback received: {data}")

  if data == "main_menu":
    await build_main_menu(update, context)

  # --- Bagian Akun ---
  elif data == "manage_account":
    await build_account_menu(update, context)
  elif data.startswith("set_active:"):
    number = int(data.split(":")[1])
    success = AuthInstance.set_active_user(number)
    if success:
      await query.message.reply_text(f"Akun {number} sekarang aktif.", quote=False)
      await build_main_menu(update, context)
    else:
      await query.message.reply_text(f"Gagal mengaktifkan akun {number}. Token mungkin sudah tidak valid.", quote=False)
      await build_account_menu(update, context)
  elif data == "add_account":
    user_state[chat_id] = "WAITING_FOR_PHONE"
    await query.message.reply_text("Silakan kirim nomor XL Anda (Contoh: 6281234567890):")
  elif data.startswith("remove_account_confirm:"):
    number = int(data.split(":")[1])
    keyboard = [
        [
            InlineKeyboardButton(
              "✅ Ya, Hapus", callback_data=f"remove_account_do:{number}"),
            InlineKeyboardButton("❌ Batal", callback_data="manage_account")
        ]
    ]
    await query.edit_message_text(f"Anda yakin ingin menghapus akun {number}?", reply_markup=InlineKeyboardMarkup(keyboard))
  elif data.startswith("remove_account_do:"):
    number = int(data.split(":")[1])
    AuthInstance.remove_refresh_token(number)
    await query.message.reply_text(f"Akun {number} telah dihapus.", quote=False)
    await build_account_menu(update, context)

  # --- Bagian Bookmark ---
  elif data == "bookmarks_menu":
    await build_bookmark_menu(update, context)
  elif data.startswith("remove_bookmark:"):
    index_to_remove = int(data.split(":")[1])
    bookmarks = BookmarkInstance.get_bookmarks()
    if 0 <= index_to_remove < len(bookmarks):
      bm_to_remove = bookmarks[index_to_remove]
      BookmarkInstance.remove_bookmark(
          bm_to_remove['family_code'], bm_to_remove['is_enterprise'],
          bm_to_remove['variant_name'], bm_to_remove['option_name']
      )
      await query.message.reply_text("Bookmark dihapus.", quote=False)
      await build_bookmark_menu(update, context)  # Refresh menu

  # --- Bagian Lihat Paket Saya ---
  elif data == "my_packages":
    await show_my_packages(update, context)

  elif data.startswith("show_detail:"):
    # Ambil ID singkat dari tombol
    package_key = data.split(":")[1]

    # Cari quota_code yang sesuai dari map yang kita simpan di context
    package_map = context.user_data.get('package_map', {})
    package_code = package_map.get(package_key)

    if package_code:
      # Jika ditemukan, panggil fungsi untuk menampilkan detailnya
      await show_package_detail(update, context, package_code)
    else:
      # Jika tidak ditemukan (misal bot baru restart), minta pengguna mengulang
      await query.answer("Sesi Anda mungkin sudah berakhir, silakan coba lagi.", show_alert=True)
      await build_main_menu(update, context)

  elif data.startswith("ask_override:"):
    payment_method = data.split(":")[1]
    purchase_info = context.user_data.get('purchase_info', {})
    price = purchase_info.get('price', 'N/A')

    context.user_data['purchase_info']['payment_method'] = payment_method

    text = f"Harga asli paket ini adalah `Rp {price}`.\nApakah Anda ingin menggunakan harga ini atau memasukkan harga lain?"
    keyboard = [
        [InlineKeyboardButton("Gunakan Harga Asli",
                              callback_data="do_purchase:no_override")],
        [InlineKeyboardButton("Masukkan Harga Lain",
                              callback_data="do_purchase:with_override")]
    ]
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

  elif data.startswith("do_purchase:"):
    override_choice = data.split(":")[1]
    payment_method = context.user_data.get(
      'purchase_info', {}).get('payment_method')

    if override_choice == "no_override":
      if payment_method == "pulsa":
        await execute_purchase_with_pulsa(update, context)
      else:
        await query.answer(f"Metode pembayaran {payment_method} belum diimplementasikan.", show_alert=True)

    elif override_choice == "with_override":
      user_state[chat_id] = "WAITING_FOR_PRICE_OVERRIDE"
      await query.edit_message_text("Silakan kirimkan jumlah harga yang Anda inginkan (contoh: 5000):")

  elif data.startswith("ask_family_code:"):
    is_enterprise = data.split(":")[1] == 'true'
    context.user_data['is_enterprise_request'] = is_enterprise

    user_state[chat_id] = "WAITING_FOR_FAMILY_CODE"
    await query.edit_message_text("Silakan kirimkan Family Code yang ingin Anda cari:")

  # Kita ubah juga handler XUT agar langsung memanggil fungsi baru
  elif data.startswith("packages_xut:"):
    _, family_code, is_enterprise_str = data.split(":")
    is_enterprise = is_enterprise_str == 'true'
    # Hapus cache lama sebelum menampilkan data baru
    context.user_data.pop('family_packages', None)
    await display_packages_from_family(update, context, family_code, is_enterprise, page=1)

  # TAMBAHKAN ELIF BARU INI UNTUK MENANGANI TOMBOL NEXT/PREV
  elif data.startswith("family_page:"):
    _, family_code, is_enterprise_str, page_str = data.split(":")
    is_enterprise = is_enterprise_str == 'true'
    page = int(page_str)
    await display_packages_from_family(update, context, family_code, is_enterprise, page=page)


def is_authenticated(update: Update):
  user_id = update.effective_user.id
  username = update.effective_user.username
  data = verify_id_username(user_id, username)
  return data


def main():
  token = os.getenv("TELEGRAM_BOT_TOKEN")
  if not token:
    logger.error("TELEGRAM_BOT_TOKEN tidak ditemukan di file .env!")
    return

  application = Application.builder().token(token).build()
  application.add_handler(CommandHandler("start", start))
  application.add_handler(CallbackQueryHandler(button_callback_handler))
  application.add_handler(MessageHandler(
    filters.TEXT & ~filters.COMMAND, message_handler))

  logger.info("Bot starting...")
  application.run_polling()


if __name__ == "__main__":
  main()
