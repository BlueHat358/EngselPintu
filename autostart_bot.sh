#!/system/bin/sh
# Tunggu 30 detik setelah boot agar sistem dan koneksi internet stabil
sleep 30

# Jalankan perintah di dalam Termux
# Ganti 'nama-folder-proyek' dengan direktori Anda
am startservice --user 0 -n com.termux/com.termux.app.TermuxService && \
su -c "cd /data/data/com.termux/files/home/EngselPintu && termux-wake-lock && python bot.py"