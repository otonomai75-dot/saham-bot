# 📖 PETUNJUK PEMAKAIAN SAHAM-BOT

> **Untuk Eric** — Cara test bot di komputer sendiri sebelum upload ke GitHub.
> Cuma 3 langkah, hampir semua otomatis.

---

## 🎯 RINGKASAN: 3 LANGKAH

| Langkah | Aksi | Berapa Lama |
|---------|------|-------------|
| 1️⃣ | Double-click `SETUP.bat` | ~2 menit (auto) |
| 2️⃣ | Edit `START_BOT.bat` (isi token) | ~2 menit (manual) |
| 3️⃣ | Double-click `START_BOT.bat` | Instant |

---

## 📋 PERSIAPAN AWAL (Sekali Saja)

### A. Cek Python Sudah Terinstall

1. Tekan tombol **Windows** di keyboard
2. Ketik: `cmd` → tekan Enter
3. Di jendela hitam, ketik: `python --version` lalu Enter

**Hasil yang benar:**
```
Python 3.11.9
```

**Kalau muncul "command not found" atau error:**
- Download Python di: https://www.python.org/downloads/
- Saat install, **WAJIB CENTANG** ✅ "Add Python to PATH" (di bawah)
- Restart komputer

---

### B. Dapatkan Token Telegram & Chat ID

#### Cara Dapat **TELEGRAM_TOKEN**:
1. Buka Telegram, cari: `@BotFather`
2. Klik Start, ketik: `/newbot`
3. Kasih nama bot (bebas, misal: "Saham Bot Eric")
4. Kasih username bot (harus akhiran `bot`, misal: `eric_saham_bot`)
5. BotFather akan kasih **token** seperti ini:
   ```
   7891234567:AAEhBOhIqWzWJfzh3M-1qGm9XXXXXXXXXX
   ```
   ☝️ **COPY token ini, simpan di Notepad sementara**

#### Cara Dapat **CHAT_ID**:
1. Di Telegram, cari: `@userinfobot`
2. Klik Start
3. Bot akan kasih info Anda, lihat baris **Id**:
   ```
   Id: 123456789
   ```
   ☝️ **COPY angka ini juga**

#### ⚠️ PENTING — Aktifkan Bot Anda Dulu:
1. Cari bot Anda di Telegram (pakai username yang Anda buat tadi)
2. Klik **Start** atau kirim `/start`
3. Wajib! Kalau tidak, bot tidak bisa kirim pesan ke Anda.

---

## 🚀 LANGKAH 1: Install Otomatis (SETUP.bat)

1. Buka folder `C:\Users\Eric\Desktop\saham-bot`
2. **Double-click** file: `SETUP.bat`
3. Window hitam akan muncul, tunggu sampai keluar pesan:
   ```
   [4/4] Setup selesai!
   ```
4. Tekan tombol apa saja untuk tutup

> ⏱️ Lama: **1-3 menit** (download library)
> 
> ⚠️ Jangan tutup window di tengah jalan!

---

## ✏️ LANGKAH 2: Isi Token di START_BOT.bat

1. **Klik kanan** file `START_BOT.bat`
2. Pilih **Edit** (atau "Open with → Notepad")
3. Cari 2 baris ini di paling atas:
   ```bat
   set TELEGRAM_TOKEN=GANTI_DENGAN_TOKEN_ANDA
   set CHAT_ID=GANTI_DENGAN_CHAT_ID_ANDA
   ```
4. **Ganti** `GANTI_DENGAN_TOKEN_ANDA` dengan token Telegram Anda
5. **Ganti** `GANTI_DENGAN_CHAT_ID_ANDA` dengan chat id Anda

**Contoh setelah diisi:**
```bat
set TELEGRAM_TOKEN=7891234567:AAEhBOhIqWzWJfzh3M-1qGm9XXXXXXXXXX
set CHAT_ID=123456789
```

6. **Save** file (Ctrl+S), lalu tutup Notepad

> ⚠️ **JANGAN PAKAI TANDA KUTIP** ("...") di sekitar nilainya!

---

## ▶️ LANGKAH 3: Jalankan Bot (START_BOT.bat)

1. **Double-click** file: `START_BOT.bat`
2. Window hitam muncul, tunggu sampai ada log:
   ```
   ✅ Connected as bot: @eric_saham_bot
   ⏰ Scheduler aktif
   ✅ Bot running. Ctrl+C untuk stop.
   ```
3. **Buka Telegram** Anda → harus muncul 2 pesan:
   - 🟢 "Saham-bot online!" (instant)
   - 📊 "LAPORAN HARIAN SAHAM IDX..." (~30 detik kemudian)

### ✅ KALAU BERHASIL
- Pesan masuk Telegram ✓
- Window terus running (jangan ditutup)
- Bot akan kirim laporan otomatis tiap hari jam 7 pagi WIB (selama window terbuka)

### 🛑 Cara STOP Bot
- Klik window hitam tadi
- Tekan **Ctrl + C** (di keyboard)
- Atau langsung **tutup window** (klik X)

---

## 🐛 KALAU ADA ERROR — APA YANG HARUS DILAKUKAN?

### Error: "Python tidak ditemukan"
👉 Install Python (lihat **Persiapan A** di atas)

### Error: "ERROR: Anda belum isi TELEGRAM_TOKEN!"
👉 Anda lupa edit `START_BOT.bat` (lihat **Langkah 2**)

### Error: "Forbidden: bot can't initiate conversation"
👉 Anda lupa kirim `/start` ke bot di Telegram (lihat **Persiapan B — Aktifkan Bot**)

### Error: "Chat not found"
👉 CHAT_ID salah → cek lagi di @userinfobot

### Error: "Unauthorized"
👉 TELEGRAM_TOKEN salah → cek lagi di @BotFather, atau token sudah di-revoke

### Error lain / window langsung tutup
👉 **Screenshot error**-nya, kirim ke saya, akan saya bantu debug

---

## 📤 SETELAH TEST BERHASIL — Upload ke GitHub

Kalau test lokal sukses, langkah berikutnya untuk deploy 24/7:

1. Upload **semua file di folder `saham-bot/`** ke GitHub repo Anda
   - ⚠️ **JANGAN upload** `START_BOT.bat` (berisi token!) — sudah ada di `.gitignore`
   - ⚠️ **JANGAN upload** folder `venv/`
2. Deploy ke Railway/Render/Heroku
3. Set env vars di dashboard platform (TELEGRAM_TOKEN, CHAT_ID)
4. Selesai — bot jalan 24/7 di server

> 📘 Detail deploy ada di file `README.md`

---

## 📞 Butuh Bantuan?

Kalau buntu di langkah manapun, kirim ke saya:
- 📸 Screenshot window error
- 📋 Copy-paste teks error
- 🤔 Langkah mana yang bingung

Saya akan pandu langsung sampai berhasil. ✅
