from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def start_keyboard():
  """Keyboard yang ditampilkan saat pengguna memulai bot."""
  keyboard = [[
      InlineKeyboardButton("➡️ Login dengan Nomor XL",
                           callback_data='login_start')
  ]]
  return InlineKeyboardMarkup(keyboard)


def main_menu_keyboard():
  """Keyboard menu utama setelah pengguna berhasil login."""
  keyboard = [
      [InlineKeyboardButton("📦 Lihat Paket Saya",
                            callback_data='my_packages')],
      [
          InlineKeyboardButton("🔥 Hot 1", callback_data='hot_packages'),
          InlineKeyboardButton(
            "🔥 Hot 2", callback_data='hot_packages_2')  # <-- TOMBOL BARU
      ],
      [
          InlineKeyboardButton("Beli (Family Code)",
                               callback_data='buy_family_code'),
          InlineKeyboardButton("Beli (Enterprise)",
                               callback_data='buy_family_code_enterprise')
      ],
      [InlineKeyboardButton("❌ Logout", callback_data='logout')]
  ]
  return InlineKeyboardMarkup(keyboard)


def rebuy_keyboard(package_index: int):
  """Keyboard untuk menampilkan tombol 'Beli Lagi' untuk sebuah paket."""
  keyboard = [[
      InlineKeyboardButton("🔄 Beli Lagi",
                           # Gunakan indeks paket, bukan kode yang panjang
                           callback_data=f'rebuy_{package_index}')
  ]]
  return InlineKeyboardMarkup(keyboard)


def ask_overwrite_keyboard(package_index: int):
  """Keyboard untuk menanyakan apakah pengguna ingin mengubah harga."""
  keyboard = [[
      # Gunakan indeks, bukan kode paket yang panjang
      InlineKeyboardButton(
        "✅ Ya", callback_data=f'overwrite_yes_{package_index}'),
      InlineKeyboardButton(
        "❌ Tidak", callback_data=f'overwrite_no_{package_index}')
  ]]
  return InlineKeyboardMarkup(keyboard)


def payment_method_keyboard(price: int):
  """Keyboard untuk memilih metode pembayaran. TIDAK lagi butuh indeks."""
  keyboard = [
      # Callback data hanya berisi metode dan harga
      [InlineKeyboardButton(
        f"💳 Pulsa (Rp {price})", callback_data=f'pay_pulsa_{price}')],
      [
          InlineKeyboardButton(
            "E-Wallet", callback_data=f'pay_ewallet_{price}'),
          InlineKeyboardButton("QRIS", callback_data=f'pay_qris_{price}')
      ],
      [InlineKeyboardButton("⬅️ Batal", callback_data='cancel_purchase')]
  ]
  return InlineKeyboardMarkup(keyboard)


def pagination_keyboard(current_page: int, total_pages: int, flow_prefix: str):
  """
  Membuat keyboard untuk navigasi halaman.
  Kini lebih fleksibel dengan flow_prefix.
  """
  buttons = []
  row = []

  if current_page > 0:
    # Gunakan flow_prefix untuk membuat callback_data yang dinamis
    row.append(InlineKeyboardButton("⬅️ Sebelumnya",
               callback_data=f'{flow_prefix}_page_{current_page - 1}'))

  row.append(InlineKeyboardButton(
    f"📄 {current_page + 1}/{total_pages}", callback_data='noop'))

  if current_page < total_pages - 1:
    # Gunakan flow_prefix di sini juga
    row.append(InlineKeyboardButton("Berikutnya ➡️",
               callback_data=f'{flow_prefix}_page_{current_page + 1}'))

  buttons.append(row)
  # Dan di sini untuk tombol batal
  buttons.append([InlineKeyboardButton(
    "❌ Batalkan", callback_data=f'{flow_prefix}_cancel')])

  return InlineKeyboardMarkup(buttons)


def ewallet_choice_keyboard():
  """Menampilkan pilihan E-Wallet."""
  keyboard = [
      [
          InlineKeyboardButton("Dana", callback_data='ewallet_select_DANA'),
          InlineKeyboardButton("GoPay", callback_data='ewallet_select_GOPAY')
      ],
      [
          InlineKeyboardButton("OVO", callback_data='ewallet_select_OVO'),
          InlineKeyboardButton(
            "ShopeePay", callback_data='ewallet_select_SHOPEEPAY')
      ],
      [InlineKeyboardButton("⬅️ Kembali ke Metode Pembayaran",
                            callback_data='ewallet_cancel')]
  ]
  return InlineKeyboardMarkup(keyboard)
