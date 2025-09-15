import os
import sys
import requests

# Load API key from text file named api.key


def load_api_key() -> str:
  if os.path.exists("api.key"):
    with open("api.key", "r", encoding="utf8") as f:
      api_key = f.read().strip()
    if api_key:
      print("API key loaded successfully.")
      return api_key
    else:
      print("API key file is empty.")
      return ""
  else:
    print("API key file not found.")
    return ""


def save_api_key(api_key: str):
  with open("api.key", "w", encoding="utf8") as f:
    f.write(api_key)
  print("API key saved successfully.")


def delete_api_key():
  if os.path.exists("api.key"):
    os.remove("api.key")
    print("API key file deleted.")
  else:
    print("API key file does not exist.")


def verify_api_key(api_key: str, *, timeout: float = 10.0) -> bool:
  """
  Returns True iff the verification endpoint responds with HTTP 200.
  Any network error or non-200 is treated as invalid.
  """
  try:
    url = f"https://crypto.mashu.lol/api/verify?key={api_key}"
    resp = requests.get(url, timeout=timeout)
    if resp.status_code == 200:
      json_resp = resp.json()
      print(
        f"API key is valid.\nId: {json_resp.get('user_id')}\nOwner: @{json_resp.get('username')}")
      return True
    else:
      print(
        f"API key is invalid. Server responded with status code {resp.status_code}.")
      return False
  except requests.RequestException as e:
    print(f"Failed to verify API key: {e}")
    return False


def ensure_api_key() -> str:
  """
  Load api.key if present; otherwise prompt the user.
  Always verifies the key. Saves only if valid.
  Exits the program if invalid or empty.
  """
  # Try to load an existing key
  current = load_api_key()
  if current:
    if verify_api_key(current):
      return current
    else:
      print("Existing API key is invalid. Please enter a new one.")

  # Prompt user if missing or invalid
  api_key = input("Masukkan API key: ").strip()
  if not api_key:
    print("API key tidak boleh kosong. Menutup aplikasi.")
    sys.exit(1)

  if not verify_api_key(api_key):
    print("API key tidak valid. Menutup aplikasi.")
    delete_api_key()
    sys.exit(1)

  save_api_key(api_key)
#   save_user_data(id, username)  # Save user data after verifying API key
  return api_key


def load_user_data() -> dict:
  if os.path.exists("users.json"):
    import json
    with open("users.json", "r", encoding="utf8") as f:
      try:
        data = json.load(f)
        if isinstance(data, dict):
          return data
        else:
          print("User data file is corrupted. Expected a JSON object.")
          return {}
      except json.JSONDecodeError:
        print("Failed to parse user data file. It may be corrupted.")
        return {}
  else:
    print("User data file not found.")
    return {}


def save_user_data(id: str, username: str):
  import json
  data = load_user_data()
  if "users" not in data:
    data["users"] = []
  # Check if user already exists; if so, update tokens
  for user in data["users"]:
    if user.get("user_id") == id:
      break
  else:
    # User not found; add new entry
    data["users"].append({
        "user_id": id,
        "username": username
    })
  with open("users.json", "w", encoding="utf8") as f:
    json.dump(data, f, indent=2)
  print("User data saved successfully.")


def verify_id_username(user_id: str, username: str) -> bool:
  data = load_user_data()
  for user in data.get("users", []):
    if user.get("user_id") == user_id and user.get("username") == username:
      return True
  return False
