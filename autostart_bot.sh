# simpan file ini di ~/.termux/boot/start_bot.sh


#!/data/data/com.termux/files/usr/bin/sh

# Beri jeda 20 detik untuk memastikan koneksi internet siap setelah boot
sleep 20

# Pindah ke direktori proyek Anda
cd ~/EngselPintu

# Aktifkan wake lock agar Termux tidak 'tertidur'
termux-wake-lock

# Jalankan bot Anda (log akan diurus oleh Python)
python bot.py