# 📊 Saham-Bot

Bot Telegram pengirim **laporan harian saham IDX** dengan analisa teknikal otomatis (SMA, RSI, Volume, Support/Resistance) + sinyal **BUY/HOLD/SELL**.

> Versi: **2.0** (refactor full — async-safe, error handling robust, retry mechanism)

---

## ✨ Fitur

- 📈 Analisa teknikal otomatis: SMA 10/50/200, RSI 14, Volume ratio
- 🎯 Sinyal trading: 🟢 BUY / 🟡 HOLD / 🔴 SELL berbasis skor multi-faktor
- 🏆 Top Pick harian dengan Entry/TP/SL/Risk-Reward
- ⏰ Jadwal otomatis tiap hari (default 07:00 WIB)
- 🛡️ Error handling: 1 saham gagal tidak crash bot
- 🔁 Retry mechanism untuk yfinance & Telegram API
- 📝 Logging detail untuk debug deployment

---

## 🚀 Cara Deploy

### 🏆 Opsi 1: GitHub Actions (100% GRATIS Selamanya — RECOMMENDED)

> Cocok untuk bot yang cuma kirim 1x sehari. Pakai GitHub free tier (2,000 menit/bulan, bot ini cuma butuh ~60 menit/bulan).

**Setup sekali doang:**

1. **Buat repo GitHub** (private atau public, terserah)
   - Daftar di [github.com](https://github.com) kalau belum punya
   - Klik **New repository** → kasih nama (misal `saham-bot`) → **Create**

2. **Push code ke repo:**
   ```bash
   cd saham-bot
   git init
   git add .
   git commit -m "initial deploy"
   git branch -M main
   git remote add origin https://github.com/<USERNAME>/saham-bot.git
   git push -u origin main
   ```

3. **Set GitHub Secrets** (TOKEN tidak akan muncul di code):
   - Buka repo di GitHub → **Settings** → **Secrets and variables** → **Actions**
   - Klik **New repository secret**, tambah dua secret berikut:
     - Name: `TELEGRAM_TOKEN` → Value: token dari @BotFather
     - Name: `CHAT_ID` → Value: chat id Anda (dari @userinfobot)

4. **Test workflow manual:**
   - Buka tab **Actions** di repo
   - Pilih workflow **"Daily Stock Report"**
   - Klik **Run workflow** → **Run workflow** (hijau)
   - Tunggu ~2 menit → cek Telegram, laporan harus masuk!

5. **Done!** Setelah ini bot otomatis jalan setiap hari **jam 07:00 WIB** (00:00 UTC).

> 💡 Cek hasil run: tab **Actions** → klik run terakhir → lihat log lengkap
> 💡 Mau ubah jam? Edit `.github/workflows/daily-report.yml` baris `cron: '0 0 * * *'`

---

### Opsi 2: Railway (⚠️ HANYA $5 trial one-time, habis ~20 hari)

1. Fork repo ini ke GitHub Anda
2. Login ke [Railway.app](https://railway.app)
3. **New Project** → **Deploy from GitHub repo** → pilih `saham-bot`
4. **Variables** → tambahkan:
   ```
   TELEGRAM_TOKEN = <token dari @BotFather>
   CHAT_ID        = <chat id Anda>
   SEND_HOUR      = 7        (opsional, default 7)
   SEND_MINUTE    = 0        (opsional, default 0)
   SEND_ON_START  = true     (opsional, kirim test saat deploy)
   ```
5. Deploy! Cek log untuk pastikan bot online.

### Opsi 3: Render

1. New **Background Worker** di [Render.com](https://render.com)
2. Connect GitHub repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `python bot.py`
5. Set env vars sama seperti Railway di atas

### Opsi 4: Heroku

1. `heroku create saham-bot`
2. `heroku config:set TELEGRAM_TOKEN=xxx CHAT_ID=xxx`
3. `git push heroku main`
4. `heroku ps:scale worker=1` ⚠️ **WAJIB** (default web=1, kita butuh worker)

---

## 🔑 Setup Telegram Bot

### Dapat Token Bot
1. Chat [@BotFather](https://t.me/BotFather)
2. `/newbot` → ikuti instruksi
3. Copy **token** (format: `123456:ABC-DEF...`)

### Dapat CHAT_ID
1. Chat [@userinfobot](https://t.me/userinfobot)
2. Copy **ID** (angka, contoh: `987654321`)

> 💡 Untuk **grup**: tambahkan bot ke grup, lalu pakai chat id grup (negatif, contoh: `-1001234567890`)

---

## 🧪 Test Lokal

```bash
# Clone repo
git clone https://github.com/<username>/saham-bot.git
cd saham-bot

# Install deps
pip install -r requirements.txt

# Set env vars (Windows PowerShell)
$env:TELEGRAM_TOKEN="123456:ABC..."
$env:CHAT_ID="987654321"

# Run
python bot.py
```

Atau pakai `.env` file (rename `.env.example` → `.env`, isi nilai, lalu `pip install python-dotenv` & tambahkan `from dotenv import load_dotenv; load_dotenv()` di `bot.py`).

---

## ⚙️ Customize Watchlist

Edit `WATCHLIST` di `bot.py`:

```python
WATCHLIST = {
    "BBCA": "BBCA.JK",
    "BBRI": "BBRI.JK",
    "TLKM": "TLKM.JK",
    # tambah saham lain di sini
    # format: "TICKER_DISPLAY": "TICKER.JK"
}
```

> Untuk saham US: gunakan ticker tanpa `.JK` (contoh: `"NVDA": "NVDA"`)

---

## 🐛 Troubleshooting

| Gejala | Penyebab | Solusi |
|--------|----------|--------|
| Bot tidak kirim apa-apa | Env var `TELEGRAM_TOKEN`/`CHAT_ID` belum di-set | Cek dashboard platform → Variables |
| Build gagal | Python version mismatch | Pastikan `runtime.txt` = `python-3.11.9` |
| "Chat not found" | CHAT_ID salah / bot belum di-add ke grup | Re-cek dengan @userinfobot, atau start chat dgn bot dulu |
| Worker exit setelah start | Heroku default `web` dyno | Run `heroku ps:scale worker=1 web=0` |
| yfinance return empty | Rate limit Yahoo | Sudah ada retry — kurangi watchlist jika persisten |

### Cek Log
- **Railway**: Project → Deployments → klik deployment → Logs
- **Render**: Service → Logs tab
- **Heroku**: `heroku logs --tail`

---

## 📋 Sinyal Logic

Skor dihitung dari:
- ✅ +1 jika Price > SMA10
- ✅ +1 jika Price > SMA50
- ✅ +1 jika Price > SMA200
- ✅ +2 jika RSI < 40 (oversold = potensi beli)
- ❌ -2 jika RSI > 70 (overbought)

Hasil:
- **🟢 BUY**: skor ≥ 3
- **🟡 HOLD**: skor 1-2
- **🔴 SELL**: skor ≤ 0

---

## ⚠️ Disclaimer

Bot ini **bukan saran investasi resmi**. Sinyal berbasis indikator teknikal sederhana — tidak mempertimbangkan fundamental, berita, atau kondisi makro. **Selalu lakukan riset sendiri (DYOR) dan gunakan manajemen risiko.**

---

## 📄 License

MIT — bebas digunakan & dimodifikasi.
