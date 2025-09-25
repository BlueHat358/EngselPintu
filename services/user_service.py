import json
import os

USER_DATA_FILE = 'user_data.json'


def _load_data():
  """Memuat data pengguna dari file JSON."""
  if not os.path.exists(USER_DATA_FILE):
    return {}
  try:
    with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
      return json.load(f)
  except (json.JSONDecodeError, FileNotFoundError):
    return {}


def _save_data(data):
  """Menyimpan data pengguna ke file JSON."""
  with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=4)


def save_refresh_token(user_id: int, refresh_token: str, phone_number: int):
  """Menyimpan refresh token dan nomor telepon untuk pengguna tertentu."""
  data = _load_data()
  data[str(user_id)] = {
      'phone_number': phone_number,
      'refresh_token': refresh_token
  }
  _save_data(data)
  print(f"Token dan nomor telepon disimpan untuk user_id: {user_id}")


def get_refresh_token(user_id: int) -> str | None:
  """Mengambil refresh token untuk pengguna tertentu."""
  data = _load_data()
  user_info = data.get(str(user_id))
  return user_info.get('refresh_token') if user_info else None


def get_phone_number(user_id: int) -> str | None:
  """Mengambil nomor telepon untuk pengguna tertentu."""
  data = _load_data()
  user_info = data.get(str(user_id))
  return user_info.get('phone_number') if user_info else None


def delete_refresh_token(user_id: int):
  """Menghapus refresh token untuk pengguna tertentu (logout)."""
  data = _load_data()
  if str(user_id) in data:
    del data[str(user_id)]
    _save_data(data)
    print(f"Token dihapus untuk user_id: {user_id}")
