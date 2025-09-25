# from telegram import Update
# from telegram.ext import CallbackContext
# from datetime import datetime

# import services.user_service as user_service
# import services.myxl_service as myxl_service
# from keyboards import main_menu_keyboard, start_keyboard, rebuy_keyboard, ask_overwrite_keyboard, payment_method_keyboard


# async def start(update: Update, context: CallbackContext) -> None:
#   """Handler untuk perintah /start."""
#   user_id = update.effective_user.id
#   refresh_token = user_service.get_refresh_token(user_id)

#   if not refresh_token:
#     # Pengguna belum login
#     await update.message.reply_text(
#         "Selamat datang di MyXL Bot! Silakan login untuk melanjutkan.",
#         reply_markup=start_keyboard()
#     )
#   else:
#     # Pengguna sudah login, tampilkan menu utama
#     await show_main_menu(update, context)


# async def show_main_menu(update: Update, context: CallbackContext):
#   """Menampilkan informasi pengguna dan menu utama."""
#   user_id = update.effective_user.id
#   query = update.callback_query

#   # Menampilkan pesan "memuat"
#   if query:
#     await query.answer("Memuat data...")
#     message_target = query.message
#   else:
#     message_target = update.message

#   refresh_token = user_service.get_refresh_token(user_id)
#   if not refresh_token:
#     await message_target.reply_text("Sesi Anda telah berakhir. Silakan login kembali.", reply_markup=start_keyboard())
#     return

#   # Dapatkan token baru menggunakan refresh token
#   tokens = myxl_service.get_new_token(refresh_token)
#   if not tokens:
#     user_service.delete_refresh_token(user_id)  # Hapus token yang tidak valid
#     await message_target.reply_text("Gagal memperbarui sesi. Silakan login kembali.", reply_markup=start_keyboard())
#     return

#   # Perbarui refresh token jika ada yang baru
#   user_service.save_refresh_token(user_id, tokens['refresh_token'])

#   # Ambil saldo
#   balance_data = myxl_service.get_user_balance(tokens['id_token'])

#   if balance_data:
#     remaining_balance = balance_data.get("remaining", "N/A")
#     expired_at_ts = balance_data.get("expired_at")
#     expired_at_dt = datetime.fromtimestamp(expired_at_ts).strftime(
#       "%d %B %Y") if expired_at_ts else "N/A"

#     phone_number = context.user_data.get(
#       'phone_number', 'Nomor tidak tersimpan')

#     menu_text = (
#         f"👤 **Informasi Akun**\n"
#         f"Nomor: `{phone_number}`\n"
#         f"Sisa Pulsa: `Rp {remaining_balance}`\n"
#         f"Masa Aktif: `{expired_at_dt}`\n\n"
#         "Silakan pilih menu di bawah ini:"
#     )
#     await message_target.reply_text(menu_text, reply_markup=main_menu_keyboard(), parse_mode='Markdown')

#   else:
#     await message_target.reply_text("Gagal mengambil informasi akun. Coba lagi nanti.")


# async def logout(update: Update, context: CallbackContext) -> None:
#   """Handler untuk logout."""
#   query = update.callback_query
#   await query.answer()
#   user_id = update.effective_user.id

#   user_service.delete_refresh_token(user_id)

#   await query.edit_message_text(
#       "Anda telah berhasil logout. Sampai jumpa lagi!",
#       reply_markup=start_keyboard()
#   )


# async def placeholder_handler(update: Update, context: CallbackContext) -> None:
#   """Handler sementara untuk fitur yang belum diimplementasikan."""
#   query = update.callback_query
#   await query.answer("Fitur ini sedang dalam pengembangan!", show_alert=True)


# async def show_my_packages(update: Update, context: CallbackContext) -> None:
#   """Mengambil dan menampilkan daftar paket aktif pengguna."""
#   query = update.callback_query
#   await query.answer("Memuat paket Anda...")

#   user_id = update.effective_user.id
#   refresh_token = user_service.get_refresh_token(user_id)

#   if not refresh_token:
#     await query.edit_message_text("Sesi berakhir. Silakan /start dan login kembali.")
#     return

#   # Dapatkan token baru untuk memastikan sesi valid
#   tokens = myxl_service.get_new_token(refresh_token)
#   if not tokens:
#     user_service.delete_refresh_token(user_id)
#     await query.edit_message_text("Gagal memperbarui sesi. Silakan /start dan login kembali.")
#     return

#   # Perbarui refresh token
#   user_service.save_refresh_token(user_id, tokens['refresh_token'])

#   # Ambil daftar paket
#   packages = myxl_service.get_my_packages(tokens['id_token'])

#   if packages is None:
#     await query.edit_message_text("Maaf, terjadi kesalahan saat mengambil data paket Anda.")
#     return

#   if not packages:
#     await query.edit_message_text("Anda tidak memiliki paket aktif saat ini.")
#     return

#   # Hapus menu sebelumnya
#   context.user_data['my_packages'] = packages
#   await query.edit_message_text("Berikut adalah daftar paket aktif Anda:")

#   # Tampilkan setiap paket dalam pesan terpisah dengan tombol "Beli Lagi"
#   for index, package in enumerate(packages):
#     package_name = package.get("name", "Nama tidak diketahui")
#     remaining = package.get("remaining", "N/A")
#     expiry = package.get("expiry", "N/A")
#     # quota_code = package.get("quota_code")  # Ini adalah package_option_code

#     # Format pesan untuk setiap paket
#     text = (
#         f"**📦 {package_name}**\n"
#         f"Sisa Kuota: `{remaining}`\n"
#         f"Berlaku hingga: `{expiry}`"
#     )

#     if package.get("quota_code"):
#       await update.effective_chat.send_message(
#           text,
#           reply_markup=rebuy_keyboard(index),
#           parse_mode='Markdown'
#       )


# async def start_purchase_flow(update: Update, context: CallbackContext, package_option_code: str = None) -> None:
#   """
#   Memulai alur pembelian untuk sebuah paket.
#   Bisa dipanggil dari alur 'Beli Lagi' (rebuy) atau dari alur 'Family Code'.
#   """
#   query = update.callback_query
#   await query.answer("Memuat detail paket...")

#   # Jika package_option_code tidak diberikan, coba ambil dari alur 'rebuy'
#   if not package_option_code:
#     try:
#       package_index = int(query.data.split('_', 1)[1])
#       stored_packages = context.user_data.get('my_packages', [])
#       if not stored_packages or package_index >= len(stored_packages):
#         await query.edit_message_text("Data paket tidak ditemukan. Coba lagi dari menu utama.")
#         return
#       selected_package = stored_packages[package_index]
#       package_option_code = selected_package.get("quota_code")
#       if not package_option_code:
#         await query.edit_message_text("Paket ini tidak dapat dibeli kembali.")
#         return
#     except (ValueError, IndexError):
#       await query.edit_message_text("Terjadi kesalahan, callback tidak valid.")
#       return

#   user_id = update.effective_user.id
#   refresh_token = user_service.get_refresh_token(user_id)

#   if not refresh_token:
#     await query.edit_message_text("Sesi berakhir. Silakan /start dan login kembali.")
#     return

#   tokens = myxl_service.get_new_token(refresh_token)
#   if not tokens:
#     await query.edit_message_text("Gagal memperbarui sesi. Silakan /start dan login kembali.")
#     return

#   # Dapatkan detail lengkap paket
#   details = myxl_service.get_package_details(
#     tokens['id_token'], package_option_code)

#   if not details:
#     await query.edit_message_text("Gagal memuat detail paket. Mungkin paket ini sudah tidak tersedia.")
#     return

#   # Ambil informasi penting dari detail
#   package_option = details.get("package_option", {})
#   title = package_option.get("name", "N/A")
#   price = package_option.get("price", 0)
#   validity = package_option.get("validity", "N/A")

#   # Dapatkan package_index dari data callback jika ada (untuk alur rebuy)
#   # Jika tidak ada, kita tidak perlu keyboard overwrite (misal dari family_handler)
#   package_index_str = query.data.split('_')[-1]

#   # Tampilkan detail dan konfirmasi pembelian (untuk saat ini, fitur beli belum diimplementasikan)
#   text = (
#       f"**Konfirmasi Pembelian Ulang**\n\n"
#       f"Nama Paket: `{title}`\n"
#       f"Harga: `Rp {price}`\n"
#       f"Masa Aktif: `{validity}`\n\n"
#       f"Apakah Anda ingin menggunakan harga lain (overwrite)?"
#   )

#   # Hanya tampilkan keyboard overwrite jika kita berada dalam alur 'rebuy'
#   reply_markup = None
#   if query.data.startswith('rebuy_') and package_index_str.isdigit():
#     reply_markup = ask_overwrite_keyboard(int(package_index_str))

#   # Hapus tombol "Beli Lagi" dan tampilkan detailnya
#   await query.edit_message_text(
#       text, reply_markup=reply_markup, parse_mode='Markdown'
#   )


# async def handle_overwrite_choice(update: Update, context: CallbackContext) -> None:
#   """Langkah 2: Menangani jawaban Ya/Tidak untuk overwrite harga."""
#   query = update.callback_query
#   await query.answer()

#   try:
#     parts = query.data.split('_')
#     choice = parts[1]
#     package_index = int(parts[2])

#     stored_packages = context.user_data.get('my_packages', [])
#     if not stored_packages or package_index >= len(stored_packages):
#       await query.edit_message_text("Data paket tidak ditemukan. Coba lagi dari menu utama.")
#       return

#     selected_package = stored_packages[package_index]
#     package_option_code = selected_package.get("quota_code")

#   except (ValueError, IndexError):
#     await query.edit_message_text("Terjadi kesalahan, callback tidak valid.")
#     return

#   if choice == "yes":
#     # Simpan indeks paket yang sedang diproses
#     context.user_data['awaiting_price_for_index'] = package_index
#     await query.edit_message_text(
#         f"Silakan ketik harga baru yang ingin Anda gunakan.\n\n"
#         "**Peringatan:** Fitur ini dapat menyebabkan kegagalan transaksi jika harga tidak sesuai."
#     )
#   else:  # 'no'
#     user_id = update.effective_user.id
#     refresh_token = user_service.get_refresh_token(user_id)
#     tokens = myxl_service.get_new_token(refresh_token)
#     details = myxl_service.get_package_details(
#       tokens['id_token'], package_option_code)

#     if not details:
#       await query.edit_message_text("Gagal memuat detail harga. Coba lagi.")
#       return

#     price = details["package_option"]["price"]
#     text = "Silakan pilih metode pembayaran:"
#     # PERUBAHAN DI SINI: Kirim package_index, bukan package_option_code
#     await query.edit_message_text(
#         text,
#         reply_markup=payment_method_keyboard(package_index, price)
#     )


# async def handle_price_input(update: Update, context: CallbackContext) -> None:
#   """Langkah 2.5: Menerima input harga baru dari pengguna."""
#   if 'awaiting_price_for_index' not in context.user_data:
#     return

#   package_index = context.user_data.pop('awaiting_price_for_index')

#   try:
#     new_price = int(update.message.text.strip())
#     if new_price <= 0:
#       raise ValueError("Harga harus positif")

#     text = f"Harga diatur ke `Rp {new_price}`. Sekarang, silakan pilih metode pembayaran:"
#     # PERUBAHAN DI SINI: Kirim package_index
#     await update.message.reply_text(
#         text,
#         reply_markup=payment_method_keyboard(package_index, new_price),
#         parse_mode='Markdown'
#     )
#   except (ValueError, TypeError):
#     await update.message.reply_text(
#         "Input tidak valid. Harap masukkan angka saja. Proses dibatalkan. Ulangi dari awal."
#     )

# async def handle_payment_choice(update: Update, context: CallbackContext) -> None:
#   """Langkah 3: Menangani pilihan metode pembayaran dan mengeksekusi pembelian."""
#   query = update.callback_query
#   await query.answer()

#   if query.data == 'cancel_purchase':
#     await query.edit_message_text("Pembelian dibatalkan.")
#     return

#   try:
#     parts = query.data.split('_')
#     method = parts[1]
#     package_index = int(parts[2])
#     price = int(parts[3])

#     # Ambil package_option_code dari data yang disimpan menggunakan indeks
#     stored_packages = context.user_data.get('my_packages', [])
#     if not stored_packages or package_index >= len(stored_packages):
#       await query.edit_message_text("Data paket tidak ditemukan. Coba lagi dari menu utama.")
#       return

#     selected_package = stored_packages[package_index]
#     package_option_code = selected_package.get("quota_code")

#   except (ValueError, IndexError):
#     await query.edit_message_text("Terjadi kesalahan, callback tidak valid.")
#     return

#   user_id = update.effective_user.id
#   refresh_token = user_service.get_refresh_token(user_id)
#   tokens = myxl_service.get_new_token(refresh_token)
#   if not tokens:
#     await query.edit_message_text("Sesi berakhir. Silakan login kembali.")
#     return

#   # Sisa logika pembelian (pulsa, ewallet, qris) tetap sama
#   if method == "pulsa":
#     await query.edit_message_text(f"Memproses pembelian dengan pulsa (Rp {price})...")
#     result = myxl_service.purchase_package_with_balance(
#       tokens, package_option_code, price)
#     if result and result.get("status") == "SUCCESS":
#       final_message = result.get("data", {}).get(
#         "message", "Pembelian berhasil!")
#       await query.edit_message_text(f"✅ **Berhasil!**\n\n{final_message}")
#     else:
#       error_message = result.get("message", "Terjadi kesalahan.")
#       await query.edit_message_text(f"❌ **Gagal!**\n\nPesan: `{error_message}`")

#   elif method == "ewallet":
#     await query.edit_message_text("Fitur pembayaran E-Wallet sedang dikembangkan.")

#   elif method == "qris":
#     await query.edit_message_text("Membuat kode QRIS...")
#     details = myxl_service.get_package_details(
#       tokens['id_token'], package_option_code)
#     item_name = details["package_option"].get(
#       "name", "Produk XL") if details else "Produk XL"
#     success, data = myxl_service.generate_qris_payment(
#         tokens=tokens,
#         package_option_code=package_option_code,
#         price=price,
#         item_name=item_name
#     )

#     if success:
#       # Jika sukses, data adalah gambar
#       qr_image_buffer = data
#       await query.delete_message()
#       await context.bot.send_photo(
#           chat_id=update.effective_chat.id,
#           photo=qr_image_buffer,
#           caption="Silakan pindai (scan) kode QR di atas untuk menyelesaikan pembayaran."
#       )
#     else:
#       # Jika gagal, data adalah string detail error
#       error_details = data
#       await query.edit_message_text(
#           f"❌ **Gagal membuat kode QRIS!**\n\n{error_details}",
#           parse_mode='Markdown'
#       )

# from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
# from telegram.ext import CallbackContext
# from datetime import datetime

# import services.user_service as user_service
# import services.myxl_service as myxl_service
# from keyboards import main_menu_keyboard, start_keyboard, rebuy_keyboard, ask_overwrite_keyboard, payment_method_keyboard


# # --- FUNGSI UTAMA (TIDAK BERUBAH BANYAK) ---


# async def start(update: Update, context: CallbackContext) -> None:
#   user_id = update.effective_user.id
#   if not user_service.get_refresh_token(user_id):
#     await update.message.reply_text(
#         "Selamat datang di MyXL Bot! Silakan login untuk melanjutkan.",
#         reply_markup=start_keyboard()
#     )
#   else:
#     await show_main_menu(update, context)


# async def show_main_menu(update: Update, context: CallbackContext):
#   """Menampilkan informasi pengguna dan menu utama."""
#   user_id = update.effective_user.id
#   query = update.callback_query

#   # Menampilkan pesan "memuat"
#   if query:
#     await query.answer("Memuat data...")
#     message_target = query.message
#   else:
#     message_target = update.message

#   refresh_token = user_service.get_refresh_token(user_id)
#   if not refresh_token:
#     await message_target.reply_text("Sesi Anda telah berakhir. Silakan login kembali.", reply_markup=start_keyboard())
#     return

#   # Dapatkan token baru menggunakan refresh token
#   tokens = myxl_service.get_new_token(refresh_token)
#   if not tokens:
#     user_service.delete_refresh_token(user_id)  # Hapus token yang tidak valid
#     await message_target.reply_text("Gagal memperbarui sesi. Silakan login kembali.", reply_markup=start_keyboard())
#     return

#   # Perbarui refresh token jika ada yang baru
#   user_service.save_refresh_token(user_id, tokens['refresh_token'])

#   # Ambil saldo
#   balance_data = myxl_service.get_user_balance(tokens['id_token'])

#   if balance_data:
#     remaining_balance = balance_data.get("remaining", "N/A")
#     expired_at_ts = balance_data.get("expired_at")
#     expired_at_dt = datetime.fromtimestamp(expired_at_ts).strftime(
#       "%d %B %Y") if expired_at_ts else "N/A"

#     phone_number = context.user_data.get(
#       'phone_number', 'Nomor tidak tersimpan')

#     menu_text = (
#         f"👤 **Informasi Akun**\n"
#         f"Nomor: `{phone_number}`\n"
#         f"Sisa Pulsa: `Rp {remaining_balance}`\n"
#         f"Masa Aktif: `{expired_at_dt}`\n\n"
#         "Silakan pilih menu di bawah ini:"
#     )
#     await message_target.reply_text(menu_text, reply_markup=main_menu_keyboard(), parse_mode='Markdown')

#   else:
#     await message_target.reply_text("Gagal mengambil informasi akun. Coba lagi nanti.")


# async def logout(update: Update, context: CallbackContext) -> None:
#   """Handler untuk logout."""
#   query = update.callback_query
#   await query.answer()
#   user_id = update.effective_user.id

#   user_service.delete_refresh_token(user_id)

#   await query.edit_message_text(
#       "Anda telah berhasil logout. Sampai jumpa lagi!",
#       reply_markup=start_keyboard()
#   )


# async def placeholder_handler(update: Update, context: CallbackContext) -> None:
#   query = update.callback_query
#   await query.answer("Fitur ini sedang dalam pengembangan!", show_alert=True)

# # --- ALUR "PAKET SAYA" (DISEDERHANAKAN) ---


# async def show_my_packages(update: Update, context: CallbackContext) -> None:
#   """HANYA MENAMPILKAN DAFTAR PAKET SAYA."""
#   query = update.callback_query
#   await query.answer("Memuat paket Anda...")
#   user_id = update.effective_user.id
#   refresh_token = user_service.get_refresh_token(user_id)
#   tokens = myxl_service.get_new_token(refresh_token)
#   if not tokens:
#     await query.edit_message_text("Sesi berakhir. Silakan /start.")
#     return
#   user_service.save_refresh_token(user_id, tokens['refresh_token'])
#   packages = myxl_service.get_my_packages(tokens['id_token'])
#   if packages is None:
#     await query.edit_message_text("Maaf, terjadi kesalahan saat mengambil data.")
#     return
#   if not packages:
#     await query.edit_message_text("Anda tidak memiliki paket aktif.")
#     return

#   context.user_data['my_packages'] = packages
#   await query.edit_message_text("Berikut adalah daftar paket aktif Anda:")
#   for index, package in enumerate(packages):
#     text = f"**📦 {package.get('name', 'N/A')}**\nSisa: `{package.get('remaining', 'N/A')}`\nHabis: `{package.get('expiry', 'N/A')}`"
#     if package.get("quota_code"):
#       await update.effective_chat.send_message(text, reply_markup=rebuy_keyboard(index), parse_mode='Markdown')


# async def start_rebuy_flow(update: Update, context: CallbackContext) -> None:
#   """HANDLER UNTUK TOMBOL 'BELI LAGI'. TUGASNYA HANYA MENCARI KODE & MEMANGGIL PUSAT PEMBELIAN."""
#   query = update.callback_query
#   await query.answer()
#   package_index = int(query.data.split('_')[1])
#   package = context.user_data.get('my_packages', [])[package_index]
#   package_option_code = package.get("quota_code")
#   # Panggil Pusat Pembelian
#   await start_purchase_flow(update, context, package_option_code)

# # --- "PUSAT PEMBELIAN" & LANGKAH-LANGKAHNYA ---


# async def start_purchase_flow(update: Update, context: CallbackContext, package_option_code: str):
#   """LANGKAH 1: PUSAT PEMBELIAN. Menampilkan detail & tombol overwrite."""
#   query = update.callback_query
#   await query.edit_message_text("Memuat detail paket...")

#   user_id = update.effective_user.id
#   refresh_token = user_service.get_refresh_token(user_id)
#   tokens = myxl_service.get_new_token(refresh_token)
#   details = myxl_service.get_package_details(
#     tokens['id_token'], package_option_code)
#   if not details:
#     await query.edit_message_text("Gagal memuat detail paket.")
#     return

#   # SOLUSI FINAL 'button_data_invalid': Simpan kode di memori sebelum menampilkan tombol
#   context.user_data['purchase_pending_code'] = package_option_code

#   price = details["package_option"]["price"]
#   text = (
#       f"**Detail Paket**\n"
#       f"Nama: `{details['package_option']['name']}`\n"
#       f"Harga: `Rp {price}`\n"
#       f"Masa Aktif: `{details['package_option']['validity']}`\n\n"
#       f"Apakah Anda ingin menggunakan harga lain (overwrite)?"
#   )

#   keyboard = [[
#       InlineKeyboardButton("✅ Ya", callback_data='overwrite_yes'),
#       InlineKeyboardButton("❌ Tidak", callback_data='overwrite_no')
#   ]]
#   await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


# async def handle_overwrite_choice(update: Update, context: CallbackContext) -> None:
#   """LANGKAH 2: Menangani pilihan overwrite."""
#   query = update.callback_query
#   await query.answer()

#   choice = query.data.split('_')[1]
#   package_option_code = context.user_data.get(
#     'purchase_pending_code')  # Ambil kode dari memori

#   if not package_option_code:
#     await query.edit_message_text("Sesi pembelian tidak valid. Silakan mulai lagi.")
#     return

#   if choice == "yes":
#     context.user_data['awaiting_price_for_code'] = package_option_code
#     del context.user_data['purchase_pending_code']  # Hapus data lama
#     await query.edit_message_text("Silakan ketik harga baru yang ingin Anda gunakan.")
#   else:  # 'no'
#     user_id = update.effective_user.id
#     refresh_token = user_service.get_refresh_token(user_id)
#     tokens = myxl_service.get_new_token(refresh_token)
#     details = myxl_service.get_package_details(
#       tokens['id_token'], package_option_code)

#     if not details:
#       await query.edit_message_text("Gagal memuat detail harga. Coba lagi.")
#       return

#     price = details["package_option"]["price"]

#     # Kita tidak lagi butuh indeks, jadi kita simpan saja kodenya untuk langkah selanjutnya
#     context.user_data['final_purchase_code'] = package_option_code
#     del context.user_data['purchase_pending_code']

#     await query.edit_message_text("Silakan pilih metode pembayaran:", reply_markup=payment_method_keyboard(price))


# async def handle_price_input(update: Update, context: CallbackContext) -> None:
#   """LANGKAH 2.5: Menerima input harga baru."""
#   package_option_code = context.user_data.pop('awaiting_price_for_code', None)
#   if not package_option_code:
#     return

#   try:
#     new_price = int(update.message.text.strip())
#     if new_price <= 0:
#       raise ValueError("Harga harus positif")

#     context.user_data['final_purchase_code'] = package_option_code
#     await update.message.reply_text(
#         f"Harga diatur ke `Rp {new_price}`. Silakan pilih metode pembayaran:",
#         reply_markup=payment_method_keyboard(new_price), parse_mode='Markdown'
#     )
#   except (ValueError, TypeError):
#     await update.message.reply_text("Input tidak valid. Proses dibatalkan.")


# async def handle_payment_choice(update: Update, context: CallbackContext) -> None:
#   """Langkah 3: Menangani pilihan metode pembayaran dan mengeksekusi pembelian."""
#   query = update.callback_query
#   await query.answer()

#   if query.data == 'cancel_purchase':
#     await query.edit_message_text("Pembelian dibatalkan.")
#     return

#   try:
#     parts = query.data.split('_')
#     method = parts[1]
#     package_index = int(parts[2])
#     price = int(parts[3])

#     # Ambil package_option_code dari data yang disimpan menggunakan indeks
#     stored_packages = context.user_data.get('my_packages', [])
#     if not stored_packages or package_index >= len(stored_packages):
#       await query.edit_message_text("Data paket tidak ditemukan. Coba lagi dari menu utama.")
#       return

#     selected_package = stored_packages[package_index]
#     package_option_code = selected_package.get("quota_code")

#   except (ValueError, IndexError):
#     await query.edit_message_text("Terjadi kesalahan, callback tidak valid.")
#     return

#   user_id = update.effective_user.id
#   refresh_token = user_service.get_refresh_token(user_id)
#   tokens = myxl_service.get_new_token(refresh_token)
#   if not tokens:
#     await query.edit_message_text("Sesi berakhir. Silakan login kembali.")
#     return

#   # Sisa logika pembelian (pulsa, ewallet, qris) tetap sama
#   if method == "pulsa":
#     await query.edit_message_text(f"Memproses pembelian dengan pulsa (Rp {price})...")
#     result = myxl_service.purchase_package_with_balance(
#       tokens, package_option_code, price)
#     if result and result.get("status") == "SUCCESS":
#       final_message = result.get("data", {}).get(
#         "message", "Pembelian berhasil!")
#       await query.edit_message_text(f"✅ **Berhasil!**\n\n{final_message}")
#     else:
#       error_message = result.get("message", "Terjadi kesalahan.")
#       await query.edit_message_text(f"❌ **Gagal!**\n\nPesan: `{error_message}`")

#   elif method == "ewallet":
#     await query.edit_message_text("Fitur pembayaran E-Wallet sedang dikembangkan.")

#   elif method == "qris":
#     await query.edit_message_text("Membuat kode QRIS...")
#     details = myxl_service.get_package_details(
#       tokens['id_token'], package_option_code)
#     item_name = details["package_option"].get(
#       "name", "Produk XL") if details else "Produk XL"
#     success, data = myxl_service.generate_qris_payment(
#         tokens=tokens,
#         package_option_code=package_option_code,
#         price=price,
#         item_name=item_name
#     )

#     if success:
#       # Jika sukses, data adalah gambar
#       qr_image_buffer = data
#       await query.delete_message()
#       await context.bot.send_photo(
#           chat_id=update.effective_chat.id,
#           photo=qr_image_buffer,
#           caption="Silakan pindai (scan) kode QR di atas untuk menyelesaikan pembayaran."
#       )
#     else:
#       # Jika gagal, data adalah string detail error
#       error_details = data
#       await query.edit_message_text(
#           f"❌ **Gagal membuat kode QRIS!**\n\n{error_details}",
#           parse_mode='Markdown'
#       )
#   pass

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from datetime import datetime

import services.user_service as user_service
import services.myxl_service as myxl_service
from keyboards import (
  main_menu_keyboard,
  start_keyboard,
  rebuy_keyboard,
  ask_overwrite_keyboard,
  payment_method_keyboard,
  ewallet_choice_keyboard
)

# --- FUNGSI UTAMA ---


async def start(update: Update, context: CallbackContext) -> None:
  user_id = update.effective_user.id
  if not user_service.get_refresh_token(user_id):
    await update.message.reply_text("Selamat datang! Silakan login.", reply_markup=start_keyboard())
  else:
    await show_main_menu(update, context)


async def show_main_menu(update: Update, context: CallbackContext):
  user_id = update.effective_user.id
  msg_target = update.callback_query.message if update.callback_query else update.message
  if update.callback_query:
    await update.callback_query.answer("Memuat data...")

  refresh_token = user_service.get_refresh_token(user_id)
  tokens = myxl_service.get_new_token(refresh_token) if refresh_token else None
  if not tokens:
    if refresh_token:
      user_service.delete_refresh_token(user_id)
    await msg_target.reply_text("Sesi berakhir. Silakan login.", reply_markup=start_keyboard())
    return

  # Ambil nomor telepon yang ada SEBELUM menyimpan token baru agar tidak hilang
  phone_number = user_service.get_phone_number(user_id)
  # Simpan token baru BERSAMA nomor telepon yang sudah ada
  user_service.save_refresh_token(
      user_id, tokens['refresh_token'], phone_number)

  balance_data = myxl_service.get_user_balance(tokens['id_token'])
  if balance_data:
    expired_at = datetime.fromtimestamp(
      balance_data.get("expired_at", 0)).strftime("%d %B %Y")
    display_number = phone_number or 'Nomor tidak tersimpan'
    menu_text = (
        f"👤 **Akun**\nNomor: `{display_number}`\nPulsa: `Rp {balance_data.get('remaining', 0):,}`\nAktif s/d: `{expired_at}`\n\n"
        "Silakan pilih menu:"
    )
    await msg_target.reply_text(menu_text, reply_markup=main_menu_keyboard(), parse_mode='Markdown')
  else:
    await msg_target.reply_text("Gagal mengambil info akun.")


async def logout(update: Update, context: CallbackContext) -> None:
  await update.callback_query.answer()
  user_service.delete_refresh_token(update.effective_user.id)
  await update.callback_query.edit_message_text("Anda telah logout.", reply_markup=start_keyboard())


async def placeholder_handler(update: Update, context: CallbackContext) -> None:
  await update.callback_query.answer("Fitur ini sedang dikembangkan!", show_alert=True)

# --- ALUR "PAKET SAYA" ---


async def show_my_packages(update: Update, context: CallbackContext) -> None:
  query = update.callback_query
  await query.answer("Memuat paket...")
  user_id = update.effective_user.id
  tokens = myxl_service.get_new_token(user_service.get_refresh_token(user_id))
  packages = myxl_service.get_my_packages(
    tokens['id_token']) if tokens else None
  if packages is None:
    await query.edit_message_text("Gagal mengambil data paket.")
    return
  if not packages:
    await query.edit_message_text("Anda tidak punya paket aktif.")
    return
  context.user_data['my_packages'] = packages
  await query.edit_message_text("Paket aktif Anda:")
  for index, package in enumerate(packages):
    text = f"**📦 {package.get('name', 'N/A')}**\nSisa: `{package.get('remaining', 'N/A')}`"
    if package.get("quota_code"):
      await update.effective_chat.send_message(text, reply_markup=rebuy_keyboard(index), parse_mode='Markdown')


async def start_rebuy_flow(update: Update, context: CallbackContext) -> None:
  """Handler tombol 'Beli Lagi'. Mengambil kode paket lalu memanggil Pusat Pembelian."""
  query = update.callback_query
  await query.answer()
  package_index = int(query.data.split('_')[1])
  package = context.user_data.get('my_packages', [])[package_index]
  package_option_code = package.get("quota_code")
  await start_purchase_flow(update, context, package_option_code)

# --- "PUSAT PEMBELIAN" & LANGKAH-LANGKAHNYA ---


async def start_purchase_flow(update: Update, context: CallbackContext, package_option_code: str):
  """LANGKAH 1: PUSAT PEMBELIAN. Menampilkan detail & tombol overwrite."""
  query = update.callback_query
  await query.edit_message_text("Memuat detail paket...")

  user_id = update.effective_user.id
  tokens = myxl_service.get_new_token(user_service.get_refresh_token(user_id))
  details = myxl_service.get_package_details(
    tokens['id_token'], package_option_code)
  if not details:
    await query.edit_message_text("Gagal memuat detail paket.")
    return

  context.user_data['purchase_pending_code'] = package_option_code
  price = details["package_option"]["price"]
  text = (
      f"**Detail Paket**\nNama: `{details['package_option']['name']}`\nHarga: `Rp {price:,}`\nAktif: `{details['package_option']['validity']}`\n\n"
      f"Gunakan harga lain (overwrite)?"
  )
  keyboard = [[InlineKeyboardButton("✅ Ya", callback_data='overwrite_yes'), InlineKeyboardButton(
    "❌ Tidak", callback_data='overwrite_no')]]
  await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


async def handle_overwrite_choice(update: Update, context: CallbackContext) -> None:
  """LANGKAH 2: Menangani pilihan overwrite."""
  query = update.callback_query
  await query.answer()
  choice = query.data.split('_')[1]
  package_option_code = context.user_data.get('purchase_pending_code')
  if not package_option_code:
    await query.edit_message_text("Sesi pembelian tidak valid. Silakan mulai lagi.")
    return

  if choice == "yes":
    context.user_data['awaiting_price_for_code'] = package_option_code
    del context.user_data['purchase_pending_code']
    await query.edit_message_text("Silakan ketik harga baru yang ingin Anda gunakan.")
  else:  # 'no'
    tokens = myxl_service.get_new_token(
      user_service.get_refresh_token(update.effective_user.id))
    details = myxl_service.get_package_details(
      tokens['id_token'], package_option_code)
    price = details["package_option"]["price"]
    context.user_data['final_purchase_code'] = package_option_code
    del context.user_data['purchase_pending_code']
    await query.edit_message_text("Silakan pilih metode pembayaran:", reply_markup=payment_method_keyboard(price))


async def handle_price_input(update: Update, context: CallbackContext) -> None:
  """LANGKAH 2.5: Menerima input harga baru."""
  package_option_code = context.user_data.pop('awaiting_price_for_code', None)
  if not package_option_code:
    return
  try:
    new_price = int(update.message.text.strip())
    if new_price <= 0:
      raise ValueError("Harga harus positif")
    context.user_data['final_purchase_code'] = package_option_code
    await update.message.reply_text(
        f"Harga diatur ke `Rp {new_price:,}`. Pilih metode pembayaran:",
        reply_markup=payment_method_keyboard(new_price), parse_mode='Markdown'
    )
  except (ValueError, TypeError):
    await update.message.reply_text("Input tidak valid. Proses dibatalkan.")


async def handle_payment_choice(update: Update, context: CallbackContext) -> None:
  """LANGKAH 3: Mengeksekusi pembelian."""
  query = update.callback_query
  await query.answer()

  if query.data == 'cancel_purchase':
    await query.edit_message_text("Pembelian dibatalkan.")
    return

  package_option_code = context.user_data.pop('final_purchase_code', None)
  if not package_option_code:
    await query.edit_message_text("Sesi pembelian tidak valid. Mulai lagi.")
    return

  parts = query.data.split('_')
  method, price = parts[1], int(parts[2])
  tokens = myxl_service.get_new_token(
    user_service.get_refresh_token(update.effective_user.id))

  if method == "pulsa":
    await query.edit_message_text(f"Memproses pembelian pulsa (Rp {price:,})...")
    result = myxl_service.purchase_package_with_balance(
      tokens, package_option_code, price)
    message = result.get(
      'message', 'Terjadi kesalahan.') if result else 'Gagal terhubung.'
    status_icon = "✅ Berhasil!" if result and result.get(
      "status") == "SUCCESS" else "❌ Gagal!"
    await query.edit_message_text(f"**{status_icon}**\n\nPesan: `{message}`", parse_mode='Markdown')

  elif method == "ewallet":
    # Tampilkan pilihan e-wallet, jangan langsung bilang 'dalam pengembangan'
    await query.edit_message_text(
        "Silakan pilih E-Wallet yang ingin Anda gunakan:",
        reply_markup=ewallet_choice_keyboard()
    )
    return  # Hentikan eksekusi di sini, tunggu pilihan e-wallet

  elif method == "qris":
    await query.edit_message_text("Membuat kode QRIS...")
    details = myxl_service.get_package_details(
      tokens['id_token'], package_option_code)
    item_name = details["package_option"].get("name", "Produk XL")
    success, data = myxl_service.generate_qris_payment(
      tokens, package_option_code, price, item_name)
    if success:
      await query.delete_message()
      await context.bot.send_photo(update.effective_chat.id, photo=data, caption="Pindai QRIS di atas untuk membayar.")
    else:
      await query.edit_message_text(f"**❌ Gagal membuat QRIS!**\n\n{data}", parse_mode='Markdown')


async def handle_ewallet_selection(update: Update, context: CallbackContext) -> None:
  """Menangani setelah pengguna memilih salah satu E-Wallet."""
  query = update.callback_query
  await query.answer()

  # Ambil kode paket yang disimpan dari langkah sebelumnya
  package_option_code = context.user_data.get('final_purchase_code')
  if not package_option_code:
    await query.edit_message_text("Sesi pembelian tidak valid. Silakan mulai lagi.")
    return

  # Ambil harga dari callback tombol pembayaran awal
  # Kita perlu sedikit trik untuk mendapatkannya kembali
  # Untuk sementara, kita ambil ulang dari detail paket
  user_id = update.effective_user.id
  tokens = myxl_service.get_new_token(user_service.get_refresh_token(user_id))
  details = myxl_service.get_package_details(
    tokens['id_token'], package_option_code)
  price = details['package_option']['price']
  item_name = details['package_option']['name']

  payment_method = query.data.split('_')[-1]  # e.g., 'DANA', 'GOPAY'

  # Jika DANA atau OVO, minta nomor telepon
  if payment_method in ["DANA", "OVO"]:
    context.user_data['ewallet_purchase_info'] = {
        'code': package_option_code,
        'price': price,
        'item_name': item_name,
        'method': payment_method
    }
    await query.edit_message_text(f"Silakan masukkan nomor **{payment_method}** Anda (contoh: 0812...):", parse_mode='Markdown')
  else:  # Untuk GoPay dan ShopeePay, langsung proses
    await query.edit_message_text(f"Memproses pembayaran via **{payment_method}**...")
    result = myxl_service.initiate_ewallet_payment(
      tokens, package_option_code, price, item_name, payment_method)

    if result and result.get("status") == "SUCCESS":
      deeplink = result.get("data", {}).get("deeplink")
      message = f"✅ **Berhasil!**\n\nSilakan buka [link ini]({deeplink}) untuk menyelesaikan pembayaran."
      await query.edit_message_text(message, parse_mode='Markdown', disable_web_page_preview=True)
    else:
      error = result.get('message', 'Terjadi kesalahan.')
      await query.edit_message_text(f"❌ **Gagal!**\n\nPesan: `{error}`", parse_mode='Markdown')

    # Hapus data sesi setelah selesai
    context.user_data.pop('final_purchase_code', None)


async def handle_ewallet_number_input(update: Update, context: CallbackContext) -> None:
  """Menangani input nomor telepon untuk DANA/OVO."""
  purchase_info = context.user_data.pop('ewallet_purchase_info', None)
  if not purchase_info:
    return  # Bukan dalam alur input nomor, abaikan

  wallet_number = update.message.text.strip()

  # Validasi nomor sederhana
  if not (wallet_number.startswith("08") and wallet_number.isdigit() and 10 <= len(wallet_number) <= 14):
    await update.message.reply_text("Format nomor salah. Coba lagi atau /cancel.")
    # Kembalikan state agar bisa input lagi
    context.user_data['ewallet_purchase_info'] = purchase_info
    return

  # Ambil data yang tersimpan
  code = purchase_info['code']
  price = purchase_info['price']
  item_name = purchase_info['item_name']
  method = purchase_info['method']

  await update.message.reply_text(f"Memproses pembayaran via **{method}** ke nomor `{wallet_number}`...", parse_mode='Markdown')

  user_id = update.effective_user.id
  tokens = myxl_service.get_new_token(user_service.get_refresh_token(user_id))
  result = myxl_service.initiate_ewallet_payment(
    tokens, code, price, item_name, method, wallet_number)

  if result and result.get("status") == "SUCCESS":
    message = f"✅ **Berhasil!**\n\nSilakan cek aplikasi **{method}** Anda untuk menyelesaikan pembayaran."
    if result.get("data", {}).get("deeplink"):
      deeplink = result["data"]["deeplink"]
      message = f"✅ **Berhasil!**\n\nSilakan buka [link ini]({deeplink}) untuk menyelesaikan pembayaran."

    await update.message.reply_text(message, parse_mode='Markdown', disable_web_page_preview=True)
  else:
    error = result.get('message', 'Terjadi kesalahan.')
    await update.message.reply_text(f"❌ **Gagal!**\n\nPesan: `{error}`", parse_mode='Markdown')
