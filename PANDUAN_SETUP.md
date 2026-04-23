# 📊 Bot Laporan Saham IDX Harian via Telegram
## Panduan Setup Lengkap (Tanpa VPS, Gratis!)

---

## 🗺️ GAMBARAN SISTEM

```
Setiap pagi jam 07.00 WIB
        ↓
  Railway.app (gratis)
  menjalankan bot.py
        ↓
  Ambil data saham IDX
  dari Yahoo Finance
        ↓
  Hitung RSI, SMA, Signal
        ↓
  📱 Kirim ke Telegram kamu
```

---

## 📋 LANGKAH 1 — Buat Telegram Bot

1. Buka Telegram, cari **@BotFather**
2. Ketik `/newbot`
3. Ikuti instruksi:
   - Masukkan nama bot: misal `Laporan Saham Saya`
   - Masukkan username: misal `sahamku_bot`
4. BotFather akan memberikan **TOKEN** seperti ini:
   ```
   1234567890:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
   ⚠️ **Simpan token ini! Jangan bagikan ke siapapun.**

---

## 📋 LANGKAH 2 — Dapatkan Chat ID Kamu

1. Cari bot **@userinfobot** di Telegram
2. Ketik `/start`
3. Bot akan balas dengan info kamu, termasuk **Id:**
   ```
   Id: 987654321
   ```
4. Catat angka tersebut — itu adalah **CHAT_ID** kamu

> 💡 Alternatif: Bisa juga kirim pesan ke bot kamu dulu,
> lalu buka URL ini di browser (ganti TOKEN):
> `https://api.telegram.org/botTOKEN/getUpdates`
> Cari nilai `"id"` di dalam `"chat"`

---

## 📋 LANGKAH 3 — Upload ke GitHub

1. Daftar di **github.com** (gratis)
2. Buat repository baru, nama: `saham-bot`
3. Upload 3 file ini:
   - `bot.py`
   - `requirements.txt`
   - `Procfile`
   
   > ⚠️ JANGAN upload file `.env` — itu berisi token rahasia!

4. Cara upload:
   - Klik tombol **"Add file"** → **"Upload files"**
   - Drag & drop ketiga file tersebut
   - Klik **"Commit changes"**

---

## 📋 LANGKAH 4 — Deploy ke Railway.app (GRATIS)

1. Buka **railway.app** dan klik **"Login"**
2. Pilih **"Login with GitHub"**
3. Klik **"New Project"** → **"Deploy from GitHub repo"**
4. Pilih repository `saham-bot` yang baru kamu buat
5. Railway akan otomatis detect dan mulai deploy

### ⚙️ Set Environment Variables (PENTING!)

Setelah project terbuat:
1. Klik project kamu
2. Klik tab **"Variables"**
3. Tambahkan variable berikut satu per satu:

| Variable | Nilai |
|----------|-------|
| `TELEGRAM_TOKEN` | Token dari BotFather |
| `CHAT_ID` | ID kamu dari userinfobot |
| `SEND_HOUR` | `7` (jam 7 pagi) |
| `SEND_MINUTE` | `0` |

4. Klik **"Deploy"** — Railway akan restart bot dengan config baru

---

## 📋 LANGKAH 5 — Test Bot

1. Setelah deploy berhasil, bot akan **langsung kirim laporan pertama** ke Telegram kamu
2. Jika berhasil, kamu akan terima pesan seperti:

```
━━━━━━━━━━━━━━━━━━━━━━━━
📊 LAPORAN HARIAN SAHAM IDX
🗓 Rabu, 22 April 2026 — 07:00 WIB
━━━━━━━━━━━━━━━━━━━━━━━━

📈 BUY: 3  |  ⏸ HOLD: 5  |  📉 SELL: 2

━━━━━━━━━━━━━━━━━━━━━━━━
BRPT  🟢 BUY
💰 Harga: Rp 2.300  🔺 +7.48%
...
```

---

## 🔧 KUSTOMISASI

### Tambah/Kurangi Saham Watchlist
Edit bagian ini di `bot.py`:
```python
WATCHLIST = {
    "BRPT":  "BRPT.JK",
    "CDIA":  "CDIA.JK",
    # Tambah saham baru di sini:
    "BBCA":  "BBCA.JK",
    "ANTM":  "ANTM.JK",
}
```

### Ubah Jam Pengiriman
Di Railway Variables, ubah:
- `SEND_HOUR` = `6` (untuk jam 06.00 WIB)
- `SEND_MINUTE` = `30` (untuk jam 06.30 WIB)

### Kirim ke Grup WhatsApp/Telegram
- Buat grup Telegram
- Tambahkan bot ke grup
- Gunakan ID grup sebagai `CHAT_ID` (biasanya diawali `-100...`)

---

## ❓ TROUBLESHOOTING

| Masalah | Solusi |
|---------|--------|
| Bot tidak kirim pesan | Cek TOKEN dan CHAT_ID di Railway Variables |
| Error `Unauthorized` | Token salah — cek kembali dari BotFather |
| Data saham kosong | Yahoo Finance kadang delay — tunggu 30 menit |
| Railway minta bayar | Pilih plan Hobby (gratis $5 credit/bulan) |

---

## 💡 TIPS PENTING

- **Saham `.JK`** = format Yahoo Finance untuk IDX
  - Contoh: `BBRI` → `BBRI.JK`, `TLKM` → `TLKM.JK`
- Bot otomatis **jalan 24/7** di Railway tanpa laptop harus nyala
- **Gratis** selama penggunaan di bawah $5/bulan (cukup untuk bot ini)
- Laporan dikirim **setiap hari termasuk weekend** — cukup abaikan di hari libur bursa

---

## 📞 BUTUH BANTUAN?

Kalau ada error atau masalah setup, screenshot pesan error-nya
dan tanyakan ke Claude — akan dibantu langsung! 🚀
