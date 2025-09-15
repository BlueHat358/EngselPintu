# app/service/user_manager.py
import json
import os
from threading import Lock

# Import fungsi lama yang masih relevan
from app.client.engsel import get_new_token, API_KEY


class UserManager:
  def __init__(self, filepath='users.json'):
    self.filepath = filepath
    self.lock = Lock()
    if not os.path.exists(self.filepath):
      self._write_data({"users": []})

  def _read_data(self):
    with self.lock:
      with open(self.filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

  def _write_data(self, data):
    with self.lock:
      with open(self.filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

  def get_user(self, user_id: int):
    """Mencari data pengguna berdasarkan Telegram User ID."""
    data = self._read_data()
    for user in data['users']:
      if user.get('user_id') == user_id:
        return user
    return None

  def create_user(self, user_id: int, username: str):
    """Membuat entri pengguna baru jika belum ada."""
    data = self._read_data()
    if self.get_user(user_id):
      return self.get_user(user_id)  # Pengguna sudah ada

    new_user = {
        "user_id": user_id,
        "username": username,
        "active_number": None,  # Nomor yang sedang aktif
        "tokens": []  # Daftar semua nomor yang dimiliki
    }
    data['users'].append(new_user)
    self._write_data(data)
    return new_user

  def add_token(self, user_id: int, number: int, refresh_token: str):
    """Menambahkan atau memperbarui token nomor untuk pengguna."""
    data = self._read_data()
    user_found = False
    for user in data['users']:
      if user['user_id'] == user_id:
        user_found = True
        token_found = False
        for token in user['tokens']:
          if token['number'] == number:
            token['refresh_token'] = refresh_token
            token_found = True
            break
        if not token_found:
          user['tokens'].append(
            {'number': number, 'refresh_token': refresh_token})
        # Jika ini adalah nomor pertama yang ditambahkan, jadikan aktif
        if not user['active_number']:
          user['active_number'] = number
        break

    if not user_found:
      return False

    self._write_data(data)
    return True

  def remove_token(self, user_id: int, number_to_remove: int):
    """Menghapus token nomor dari pengguna."""
    data = self._read_data()
    for user in data['users']:
      if user['user_id'] == user_id:
        user['tokens'] = [t for t in user['tokens']
                          if t['number'] != number_to_remove]
        # Jika nomor yang dihapus adalah yang aktif, set aktif ke nomor pertama atau None
        if user['active_number'] == number_to_remove:
          user['active_number'] = user['tokens'][0]['number'] if user['tokens'] else None
        self._write_data(data)
        return True
    return False

  def set_active_number(self, user_id: int, number_to_set: int):
    """Mengatur nomor mana yang aktif untuk pengguna."""
    data = self._read_data()
    for user in data['users']:
      if user['user_id'] == user_id:
        # Pastikan nomor itu milik pengguna
        if any(t['number'] == number_to_set for t in user['tokens']):
          user['active_number'] = number_to_set
          self._write_data(data)
          return True
    return False

  def get_active_session(self, user_id: int):
    """
    Mendapatkan sesi aktif (nomor dan token yang sudah di-refresh) untuk pengguna.
    Ini adalah fungsi terpenting yang akan dipanggil oleh bot.
    """
    user = self.get_user(user_id)
    if not user or not user['active_number']:
      return None  # Tidak ada pengguna atau nomor aktif

    active_number = user['active_number']
    refresh_token = None
    for token in user['tokens']:
      if token['number'] == active_number:
        refresh_token = token['refresh_token']
        break

    if not refresh_token:
      return None  # Nomor aktif tidak ditemukan di daftar token

    # Refresh token untuk mendapatkan access & id token baru
    new_tokens = get_new_token(refresh_token)
    if not new_tokens:
      # Mungkin token sudah expired
      return None

    # Simpan kembali refresh token yang mungkin baru
    self.add_token(user_id, active_number, new_tokens['refresh_token'])

    return {
        'number': active_number,
        'api_key': API_KEY,
        'tokens': new_tokens
    }

# Hapus atau arsipkan file app/service/auth.py karena sudah digantikan oleh ini.
