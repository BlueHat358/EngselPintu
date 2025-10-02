# File ini mengadaptasi fungsi dari app/client/engsel.py untuk digunakan oleh bot
# Semua `print` dan `input` dihilangkan, dan fungsi mengembalikan data atau None/Exception

from app.client.encrypt import load_ax_fp, ax_device_id
import requests
import uuid
import time
import qrcode
import json
from io import BytesIO
from datetime import datetime, timezone, timedelta

# Impor konfigurasi
from config import BASE_CIAM_URL, BASIC_AUTH, UA, CRYPTO_API_KEY, MYXL_API_KEY
# Impor fungsi-fungsi asli
from app.client.encrypt import ax_api_signature, build_encrypted_field
from app.client.engsel import (
    get_new_token,
    send_api_request,
    get_package,
    send_payment_request,
    get_family
)
from app.client.purchase import (
    get_payment_methods,
    settlement_qris,
    get_qris_code,
    settlement_multipayment
)


# Inisialisasi beberapa variabel global dari kode asli
AX_DEVICE_ID = ax_device_id()
AX_FP = load_ax_fp()
GET_OTP_URL = f"{BASE_CIAM_URL}/realms/xl-ciam/auth/otp"
SUBMIT_OTP_URL = f"{BASE_CIAM_URL}/realms/xl-ciam/protocol/openid-connect/token"


def request_otp(contact: str) -> str | None:
  """Meminta OTP dan mengembalikan subscriber_id jika berhasil."""
  if not contact.startswith("628") or len(contact) > 14:
    return None

  querystring = {
      "contact": contact,
      "contactType": "SMS",
      "alternateContact": "false"
  }

  headers = {
      "Authorization": f"Basic {BASIC_AUTH}",
      "Ax-Device-Id": AX_DEVICE_ID,
      "Ax-Fingerprint": AX_FP,
      "Ax-Request-At": datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+07:00",
      "Ax-Request-Id": str(uuid.uuid4()),
      "User-Agent": UA,
  }

  try:
    response = requests.get(GET_OTP_URL, headers=headers,
                            params=querystring, timeout=30)
    response.raise_for_status()
    json_body = response.json()
    return json_body.get("subscriber_id")
  except requests.RequestException as e:
    print(f"Error requesting OTP: {e}")
    return None


def verify_otp(contact: str, code: str) -> dict | None:
  """Memverifikasi OTP dan mengembalikan token jika berhasil."""
  from app.client.encrypt import ts_gmt7_without_colon

  now_gmt7 = datetime.now(timezone(timedelta(hours=7)))
  ts_for_sign = ts_gmt7_without_colon(now_gmt7)

  # MENGGUNAKAN CRYPTO_API_KEY YANG BENAR
  signature = ax_api_signature(
    CRYPTO_API_KEY, ts_for_sign, contact, code, "SMS")

  payload = f"contactType=SMS&code={code}&grant_type=password&contact={contact}&scope=openid"

  headers = {
      "Authorization": f"Basic {BASIC_AUTH}",
      "Ax-Api-Signature": signature,
      "Ax-Device-Id": AX_DEVICE_ID,
      "Ax-Fingerprint": AX_FP,
      # PERBAIKAN: Mengubah timedelta dari 1 menit menjadi 5 menit agar sesuai dengan kode asli
      "Ax-Request-At": ts_gmt7_without_colon(now_gmt7 - timedelta(minutes=5)),
      "Ax-Request-Id": str(uuid.uuid4()),
      "Content-Type": "application/x-www-form-urlencoded",
      "User-Agent": UA,
  }

  try:
    response = requests.post(
      SUBMIT_OTP_URL, data=payload, headers=headers, timeout=30)
    response.raise_for_status()  # Akan memunculkan error untuk status 4xx atau 5xx
    json_body = response.json()
    if "error" in json_body:
      return None
    return json_body
  except requests.RequestException as e:
    # Menambahkan logging yang lebih detail untuk debugging
    print(f"[Error submit_otp]: {e}")
    if e.response is not None:
      print(f"[Server Response]: {e.response.text}")
    return None


def get_user_balance(id_token: str) -> dict | None:
  """
  Mengambil data saldo pengguna dengan logging error yang lebih baik.
  Fungsi ini sekarang mereplikasi logika dari `get_balance` di `engsel.py`
  untuk memberikan output debug yang lebih detail tanpa mengubah file asli.
  """
  print("Mencoba mengambil saldo...")

  path = "api/v8/packages/balance-and-credit"
  raw_payload = {
      "is_enterprise": False,
      "lang": "en"
  }

  # Memanggil send_api_request secara langsung untuk kontrol yang lebih baik
  res = send_api_request(MYXL_API_KEY, path, raw_payload, id_token, "POST")

  # Log respons mentah untuk debugging
  print(f"[DEBUG] Respons mentah dari server untuk saldo: {res}")

  # Logika penanganan error yang lebih kuat
  if res and isinstance(res, dict) and res.get("status") == "SUCCESS":
    if "data" in res and "balance" in res["data"]:
      return res["data"]["balance"]
    else:
      print("Error: Respons sukses tetapi tidak ada data saldo.")
      return None
  else:
    # Mencetak pesan error yang lebih informatif
    error_message = "Terjadi kesalahan yang tidak diketahui."
    if isinstance(res, dict):
      # Mencoba mengambil pesan error dari beberapa kunci yang mungkin
      error_message = res.get("message", res.get("error_description", res.get(
        "error", "Kunci error tidak ditemukan di respons.")))
    elif isinstance(res, str):
      # Tampilkan 200 karakter pertama
      error_message = f"Server mengembalikan respons non-JSON: {res[:200]}"

    print(f"Gagal mengambil saldo: {error_message}")
    return None


def get_my_packages(id_token: str) -> list | None:
  """Mengambil daftar paket aktif (kuota) milik pengguna."""
  print("Mencoba mengambil daftar paket saya...")

  path = "api/v8/packages/quota-details"
  raw_payload = {
      "is_enterprise": False,
      "lang": "en",
      "family_member_id": ""
  }

  res = send_api_request(MYXL_API_KEY, path, raw_payload, id_token, "POST")

  if res and isinstance(res, dict) and res.get("status") == "SUCCESS":
    if "data" in res and "quotas" in res["data"]:
      # Mengembalikan daftar kuota jika berhasil
      return res["data"]["quotas"]
    else:
      print("Error: Respons sukses tetapi tidak ada data kuota.")
      return []  # Kembalikan list kosong jika tidak ada kuota
  else:
    error_message = res.get(
      "message", "Terjadi kesalahan saat mengambil paket.")
    print(f"Gagal mengambil paket saya: {error_message}")
    return None


def get_package_details(id_token: str, package_option_code: str) -> dict | None:
  """Mengambil detail sebuah paket berdasarkan package_option_code."""
  print(f"Mengambil detail untuk paket: {package_option_code}")
  from app.client.engsel import get_package  # Impor fungsi spesifik

  # Fungsi get_package memerlukan seluruh dict 'tokens', jadi kita buat dummy
  # karena yang terpenting adalah 'id_token' untuk send_api_request
  dummy_tokens = {"id_token": id_token}

  # Memanggil fungsi get_package dari 'engsel'
  # Parameter pertama adalah MYXL_API_KEY
  package_data = get_package(MYXL_API_KEY, dummy_tokens, package_option_code)

  if package_data:
    return package_data
  else:
    print(f"Gagal mengambil detail untuk paket: {package_option_code}")
    return None


def get_hot_packages() -> list | None:
  """Mengambil daftar paket 'hot' dari URL JSON statis."""
  url = "https://me.mashu.lol/pg-hot.json"
  print("Mengambil daftar paket hot...")
  try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()  # Akan memunculkan error jika status bukan 2xx
    return response.json()
  except requests.RequestException as e:
    print(f"Gagal mengambil data hot package: {e}")
    return None
  except ValueError:  # Termasuk json.JSONDecodeError
    print("Gagal mem-parsing JSON dari hot package.")
    return None


def get_packages_by_family(id_token: str, family_code: str, is_enterprise: bool = False) -> list | None:
  """
  Mengambil daftar paket berdasarkan family code dan mengubahnya menjadi
  daftar (flat list) yang mudah diolah.
  """
  print(f"Mengambil paket untuk family code: {family_code}")
  # get_family memerlukan dict tokens, kita buat dummy-nya
  dummy_tokens = {"id_token": id_token}

  family_data = get_family(MYXL_API_KEY, dummy_tokens,
                           family_code, is_enterprise)

  if not family_data or "package_variants" not in family_data:
    return None

  # Ubah data dari API menjadi flat list yang sederhana
  package_list = []
  for variant in family_data.get("package_variants", []):
    for option in variant.get("package_options", []):
      package_list.append({
          "name": f"{variant.get('name', '')} {option.get('name', '')}".strip(),
          "price": option.get("price"),
          "package_option_code": option.get("package_option_code"),
          "validity": option.get("validity"),
          "order": option.get("order"),  # <-- TAMBAHKAN BARIS INI
          "family_name": family_data.get("package_family", {}).get("name", "N/A"),
      })
  return package_list


def purchase_package_with_balance(tokens: dict, package_option_code: str, price: int) -> dict | None:
  """Melakukan pembelian paket menggunakan pulsa (balance)."""
  print(f"Memulai pembelian paket {package_option_code} dengan harga {price}")

  # 1. Dapatkan detail paket terbaru untuk mendapatkan token konfirmasi
  package_details = get_package_details(
    tokens['id_token'], package_option_code)
  if not package_details:
    print("Gagal mendapatkan detail paket untuk pembelian.")
    return {"status": "FAILED", "message": "Gagal mendapatkan detail paket."}

  token_confirmation = package_details.get("token_confirmation")
  payment_target = package_details["package_option"]["package_option_code"]
  item_name = f"{package_details.get('package_detail_variant', {}).get('name', '')} {package_details['package_option'].get('name', '')}".strip(
  )
  payment_for = package_details["package_family"].get(
    "payment_for", "BUY_PACKAGE")

  # 2. Dapatkan token pembayaran dan timestamp
  from app.client.purchase import get_payment_methods
  payment_methods_data = get_payment_methods(
      api_key=MYXL_API_KEY,
      tokens=tokens,
      token_confirmation=token_confirmation,
      payment_target=payment_target
  )

  if not payment_methods_data:
    return {"status": "FAILED", "message": "Gagal memulai sesi pembayaran."}

  token_payment = payment_methods_data["token_payment"]
  ts_to_sign = payment_methods_data["timestamp"]

  # 3. Siapkan payload untuk settlement (pembayaran)
  settlement_payload = {
      "total_discount": 0, "is_enterprise": False, "payment_token": "",
      "token_payment": token_payment, "activated_autobuy_code": "",
      "cc_payment_type": "", "is_myxl_wallet": False, "pin": "",
      "ewallet_promo_id": "", "members": [], "total_fee": 0, "fingerprint": "",
      "autobuy_threshold_setting": {"label": "", "type": "", "value": 0},
      "is_use_point": False, "lang": "en", "payment_method": "BALANCE",
      "timestamp": int(time.time()), "points_gained": 0, "can_trigger_rating": False,
      "akrab_members": [], "akrab_parent_alias": "", "referral_unique_code": "",
      "coupon": "", "payment_for": payment_for, "with_upsell": False, "topup_number": "",
      "stage_token": "", "authentication_id": "",
      "encrypted_payment_token": build_encrypted_field(urlsafe_b64=True), "token": "",
      "token_confirmation": token_confirmation, "access_token": tokens["access_token"],
      "wallet_number": "", "encrypted_authentication_id": build_encrypted_field(urlsafe_b64=True),
      "additional_data": {
          "original_price": price, "is_spend_limit_temporary": False, "migration_type": "",
          "akrab_m2m_group_id": "false", "spend_limit_amount": 0, "is_spend_limit": False,
          "mission_id": "", "tax": 0, "benefit_type": "", "quota_bonus": 0, "cashtag": "",
          "is_family_plan": False, "combo_details": [], "is_switch_plan": False,
          "discount_recurring": 0, "is_akrab_m2m": False, "balance_type": "PREPAID_BALANCE",
          "has_bonus": False, "discount_promo": 0
      },
      "total_amount": price, "is_using_autobuy": False,
      "items": [{"item_code": payment_target, "product_type": "", "item_price": price, "item_name": item_name, "tax": 0}]
  }

  # 4. Kirim permintaan pembayaran
  print("Mengirim permintaan settlement...")
  purchase_result = send_payment_request(
      api_key=MYXL_API_KEY,
      payload_dict=settlement_payload,
      access_token=tokens["access_token"],
      id_token=tokens["id_token"],
      token_payment=token_payment,
      ts_to_sign=ts_to_sign,
      payment_for=payment_for
  )

  print(f"Hasil pembelian: {purchase_result}")
  return purchase_result


def purchase_multi_package_with_balance(tokens: dict, payment_items: list, total_price: int) -> dict | None:
  if not payment_items:
    return None

  # --- PERBAIKAN LOGIKA V2 ---
  # 1. Bangun string payment_targets
  payment_targets = ";".join([item['item_code'] for item in payment_items])

  first_item_code = payment_items[0]['item_code']
  details = get_package_details(tokens['id_token'], first_item_code)
  methods = get_payment_methods(MYXL_API_KEY, tokens, details.get(
    "token_confirmation"), first_item_code)

  payload = {
      "payment_for": "BUY_PACKAGE", "access_token": tokens["access_token"],
      "token_payment": methods["token_payment"], "payment_method": "BALANCE",
      "total_amount": total_price, "items": payment_items,
      "total_discount": 0, "is_enterprise": False, "lang": "en", "timestamp": int(time.time()),
  }

  # 2. Kirim payment_targets ke fungsi level rendah
  return send_payment_request(
      api_key=MYXL_API_KEY, payload_dict=payload, access_token=tokens["access_token"],
      id_token=tokens["id_token"], token_payment=methods["token_payment"],
      ts_to_sign=methods["timestamp"], payment_targets_override=payment_targets
  )


def generate_qris_payment(tokens: dict, package_option_code: str, price: int, item_name: str) -> BytesIO | None:
  """
  Mengurus seluruh alur pembayaran QRIS dan mengembalikan gambar QR dalam buffer memori.
  """
  print(f"Memulai pembuatan QRIS untuk paket {package_option_code}")

  # 1. Dapatkan token pembayaran dan timestamp
  package_details = get_package_details(
    tokens['id_token'], package_option_code)
  if not package_details:
    print("Gagal mendapatkan detail paket untuk pembayaran QRIS.")
    return None
  token_confirmation = package_details.get("token_confirmation")

  payment_methods_data = get_payment_methods(
      api_key=MYXL_API_KEY,
      tokens=tokens,
      token_confirmation=token_confirmation,
      payment_target=package_option_code,
  )
  if not payment_methods_data:
    print("Gagal mendapatkan metode pembayaran.")
    return None

  token_payment = payment_methods_data["token_payment"]
  ts_to_sign = payment_methods_data["timestamp"]

  # 2. Lakukan settlement untuk mendapatkan ID transaksi
  # transaction_id = settlement_qris(
  #     api_key=MYXL_API_KEY,
  #     tokens=tokens,
  #     token_payment=token_payment,
  #     ts_to_sign=ts_to_sign,
  #     payment_target=package_option_code,
  #     price=price,
  #     item_name=item_name
  # )

  settlement_result = settlement_qris(
      api_key=MYXL_API_KEY, tokens=tokens, token_payment=token_payment,
      ts_to_sign=ts_to_sign, payment_target=package_option_code, price=price, item_name=item_name
    )

  if not isinstance(settlement_result, dict):
    return (False, f"Menerima respons tidak terduga dari server:\n`{str(settlement_result)}`")

  if settlement_result.get("status") != "SUCCESS":
    message = settlement_result.get('message', 'Settlement Gagal')
    description = settlement_result.get('description', 'Tidak ada deskripsi.')
    error_details = f"Pesan: `{message}`\nDeskripsi: `{description}`"
    return (False, error_details)

  transaction_id = settlement_result["transaction_id"]

  print(f"Transaksi ID: {transaction_id}. Mengambil kode QRIS...")
  qris_result = get_qris_code(
      api_key=MYXL_API_KEY, tokens=tokens, transaction_id=transaction_id
  )

  if not transaction_id:
    print("Gagal melakukan settlement QRIS.")
    return None

  # 3. Dapatkan data string QRIS menggunakan ID transaksi
  print(f"Transaksi ID: {transaction_id}. Mengambil kode QRIS...")
  qris_data_string = get_qris_code(
      api_key=MYXL_API_KEY,
      tokens=tokens,
      transaction_id=transaction_id
  )

  if not isinstance(qris_result, dict):
    return (False, f"Menerima respons tidak terduga saat mengambil kode QR:\n`{str(qris_result)}`")

  if qris_result.get("status") != "SUCCESS":
    message = qris_result.get('message', 'Gagal Mendapatkan Kode QRIS')
    description = qris_result.get('description', 'Tidak ada deskripsi.')
    error_details = f"Pesan: `{message}`\nDeskripsi: `{description}`"
    return (False, error_details)

  qris_data_string = qris_result["qr_code"]

  # 4. Buat gambar QR code
  print("Membuat gambar QR code...")
  qr_image = qrcode.make(qris_data_string)
  buffer = BytesIO()
  qr_image.save(buffer, "PNG")
  buffer.seek(0)

  return (True, buffer)


def generate_qris_payment_multi(tokens: dict, payment_items: list, total_price: int) -> tuple:
  if not payment_items:
    return (False, "Tidak ada item.")

  # --- PERBAIKAN LOGIKA V2 ---
  # 1. Bangun string payment_targets
  payment_targets = ";".join([item['item_code'] for item in payment_items])

  first_item_code = payment_items[0]['item_code']
  details = get_package_details(tokens['id_token'], first_item_code)
  methods = get_payment_methods(MYXL_API_KEY, tokens, details.get(
      "token_confirmation"), first_item_code)

  # 2. Kirim payment_targets ke fungsi level rendah
  settlement_result = settlement_qris(
      api_key=CRYPTO_API_KEY, tokens=tokens, token_payment=methods["token_payment"],
      ts_to_sign=methods["timestamp"], payment_target=first_item_code, price=total_price,
      item_name=f"Combo Pembelian ({len(payment_items)} item)",
      payment_items_override=payment_items, payment_targets_override=payment_targets
  )

  if not isinstance(settlement_result, dict):
    return (False, f"Menerima respons tidak terduga dari server:\n`{str(settlement_result)}`")

  if settlement_result.get("status") != "SUCCESS":
    message = settlement_result.get('message', 'Settlement Gagal')
    description = settlement_result.get('description', 'Tidak ada deskripsi.')
    error_details = f"Pesan: `{message}`\nDeskripsi: `{description}`"
    return (False, error_details)

  transaction_id = settlement_result["transaction_id"]

  print(f"Transaksi ID: {transaction_id}. Mengambil kode QRIS...")
  qris_result = get_qris_code(
      api_key=MYXL_API_KEY, tokens=tokens, transaction_id=transaction_id
  )

  if not transaction_id:
    print("Gagal melakukan settlement QRIS.")
    return None

  # 3. Dapatkan data string QRIS menggunakan ID transaksi
  print(f"Transaksi ID: {transaction_id}. Mengambil kode QRIS...")
  qris_data_string = get_qris_code(
      api_key=MYXL_API_KEY,
      tokens=tokens,
      transaction_id=transaction_id
  )

  if not isinstance(qris_result, dict):
    return (False, f"Menerima respons tidak terduga saat mengambil kode QR:\n`{str(qris_result)}`")

  if qris_result.get("status") != "SUCCESS":
    message = qris_result.get('message', 'Gagal Mendapatkan Kode QRIS')
    description = qris_result.get('description', 'Tidak ada deskripsi.')
    error_details = f"Pesan: `{message}`\nDeskripsi: `{description}`"
    return (False, error_details)

  qris_data_string = qris_result["qr_code"]

  # 4. Buat gambar QR code
  print("Membuat gambar QR code...")
  qr_image = qrcode.make(qris_data_string)
  buffer = BytesIO()
  qr_image.save(buffer, "PNG")
  buffer.seek(0)

  return (True, buffer)


def initiate_ewallet_payment(
    tokens: dict, package_option_code: str, price: int, item_name: str,
    payment_method: str, wallet_number: str = ""
) -> dict | None:
  """Memulai dan menyelesaikan pembayaran E-Wallet."""
  print(f"Memulai pembayaran {payment_method} untuk {package_option_code}")

  # 1. Dapatkan token pembayaran dan timestamp
  package_details = get_package_details(
    tokens['id_token'], package_option_code)
  if not package_details:
    return {"status": "FAILED", "message": "Gagal mendapatkan detail paket."}
  token_confirmation = package_details.get("token_confirmation")

  payment_methods_data = get_payment_methods(
      api_key=MYXL_API_KEY, tokens=tokens, token_confirmation=token_confirmation,
      payment_target=package_option_code
  )
  if not payment_methods_data:
    return {"status": "FAILED", "message": "Gagal memulai sesi pembayaran."}

  token_payment = payment_methods_data["token_payment"]
  ts_to_sign = payment_methods_data["timestamp"]

  # 2. Panggil settlement multipayment
  # Gunakan CRYPTO_API_KEY karena fungsi ini melakukan enkripsi
  result = settlement_multipayment(
      api_key=CRYPTO_API_KEY,
      tokens=tokens,
      token_payment=token_payment,
      ts_to_sign=ts_to_sign,
      payment_target=package_option_code,
      price=price,
      amount_int=price,
      wallet_number=wallet_number,
      item_name=item_name,
      payment_method=payment_method
  )

  return result


def initiate_ewallet_payment_multi(tokens: dict, payment_items: list, total_price: int, payment_method: str, wallet_number: str = "") -> dict:
    # --- PERBAIKAN LOGIKA V2 ---
    # 1. Bangun string payment_targets
  payment_targets = ";".join([item['item_code'] for item in payment_items])

  first_item_code = payment_items[0]['item_code']
  details = get_package_details(tokens['id_token'], first_item_code)
  methods = get_payment_methods(MYXL_API_KEY, tokens, details.get(
    "token_confirmation"), first_item_code)

  # 2. Kirim payment_targets ke fungsi level rendah
  return settlement_multipayment(
      api_key=CRYPTO_API_KEY, tokens=tokens, token_payment=methods["token_payment"],
      ts_to_sign=methods["timestamp"], payment_target=first_item_code,
      price=total_price, amount_int=total_price, wallet_number=wallet_number,
      item_name=f"Combo Pembelian ({len(payment_items)} item)", payment_method=payment_method,
      payment_items_override=payment_items, payment_targets_override=payment_targets
  )


# Cache untuk Hot 2
hot_packages_2_cache = {
    "data": None,
    "timestamp": 0
}


def get_hot_packages_2() -> list | None:
  """Mengambil daftar paket 'hot 2' dari URL JSON statis."""

  # Cek cache dulu (berlaku 10 menit)
  if hot_packages_2_cache["data"] and (time.time() - hot_packages_2_cache["timestamp"] < 600):
    print("Mengambil paket hot 2 dari cache...")
    return hot_packages_2_cache["data"]

  # PENTING: Ganti URL ini jika sumber datanya berbeda
  url = "https://me.mashu.lol/pg-hot2.json"
  print("Mengambil daftar paket hot 2 dari internet...")

  try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()

    json_data = response.json()

    # --- TAMBAHKAN BARIS INI UNTUK LOGGING ---
    # print("--- MULAI RAW JSON HOT 2 ---")
    # print(json.dumps(json_data, indent=2))
    # print("--- AKHIR RAW JSON HOT 2 ---")
    # ----------------------------------------

    hot_packages_2_cache["data"] = json_data
    hot_packages_2_cache["timestamp"] = time.time()

    return hot_packages_2_cache["data"]
  except Exception as e:
    print(f"Gagal mengambil data hot package 2: {e}")
    return None


def get_package_details_from_hot_list(id_token: str, hot_package_item: dict) -> dict | None:
  """
  Mencari detail lengkap sebuah paket (termasuk package_option_code)
  menggunakan info dari JSON hot list (family_code, is_enterprise, order).
  """
  family_code = hot_package_item.get("family_code")
  is_enterprise = hot_package_item.get("is_enterprise", False)
  target_order = hot_package_item.get("order")

  # Ambil semua paket dalam satu family
  all_packages_in_family = get_packages_by_family(
    id_token, family_code, is_enterprise)
  if not all_packages_in_family:
    return None

  # Cari paket yang cocok berdasarkan 'order'
  for pkg in all_packages_in_family:
    # Kita perlu memodifikasi get_packages_by_family untuk menyertakan 'order'
    # Untuk sekarang, kita asumsikan 'order' ada di dalam data yang dikembalikan.
    # Jika tidak, kita perlu memodifikasi get_packages_by_family.
    # Mari kita asumsikan 'order' ada untuk saat ini.
    if pkg.get("order") == target_order:
      # Jika cocok, ambil detail lengkapnya menggunakan package_option_code
      return get_package_details(id_token, pkg.get("package_option_code"))

  return None  # Tidak ditemukan
