import os
import asyncio
import logging
from datetime import datetime
import pytz
import yfinance as yf
import pandas as pd
import numpy as np
from telegram import Bot
from telegram.constants import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── CONFIG ───────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
CHAT_ID        = os.environ.get("CHAT_ID", "")
WIB            = pytz.timezone("Asia/Jakarta")
SEND_HOUR      = int(os.environ.get("SEND_HOUR", "7"))
SEND_MINUTE    = int(os.environ.get("SEND_MINUTE", "0"))

# Watchlist saham IDX (tambah/kurangi sesuai selera)
WATCHLIST = {
    "BRPT":  "BRPT.JK",
    "CDIA":  "CDIA.JK",
    "BBRI":  "BBRI.JK",
    "TLKM":  "TLKM.JK",
    "ISAT":  "ISAT.JK",
    "PTRO":  "PTRO.JK",
    "RATU":  "RATU.JK",
    "ASII":  "ASII.JK",
    "BMRI":  "BMRI.JK",
    "GOTO":  "GOTO.JK",
}

# ─── TECHNICAL INDICATORS ─────────────────────────────────────────────────────

def compute_rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs  = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return round(float(rsi.iloc[-1]), 1)

def compute_sma(series: pd.Series, window: int) -> float:
    if len(series) < window:
        return None
    return round(float(series.rolling(window).mean().iloc[-1]), 0)

def get_signal(price, sma10, sma50, sma200, rsi) -> str:
    score = 0
    if sma10  and price > sma10:  score += 1
    if sma50  and price > sma50:  score += 1
    if sma200 and price > sma200: score += 1
    if rsi < 40:  score += 2   # oversold = potensi beli
    if rsi > 70:  score -= 2   # overbought
    if score >= 3:  return "🟢 BUY"
    if score >= 1:  return "🟡 HOLD"
    return "🔴 SELL"

def fmt(val, prefix="Rp ") -> str:
    if val is None: return "N/A"
    return f"{prefix}{int(val):,}".replace(",", ".")

# ─── FETCH & ANALYZE ──────────────────────────────────────────────────────────

def analyze_stock(ticker_id: str, ticker_yf: str) -> dict | None:
    try:
        df = yf.download(ticker_yf, period="1y", interval="1d", progress=False, auto_adjust=True)
        if df.empty or len(df) < 20:
            return None

        close  = df["Close"].squeeze()
        volume = df["Volume"].squeeze()

        price   = round(float(close.iloc[-1]), 0)
        prev    = round(float(close.iloc[-2]), 0)
        chg_pct = round((price - prev) / prev * 100, 2)

        sma10  = compute_sma(close, 10)
        sma50  = compute_sma(close, 50)
        sma200 = compute_sma(close, 200)
        rsi    = compute_rsi(close)

        vol_today = int(volume.iloc[-1])
        vol_avg   = int(volume.rolling(20).mean().iloc[-1])
        vol_ratio = round(vol_today / vol_avg, 1) if vol_avg else 1.0

        # Support / Resistance sederhana (20-day low/high)
        support    = round(float(close.rolling(20).min().iloc[-1]), 0)
        resistance = round(float(close.rolling(20).max().iloc[-1]), 0)

        signal = get_signal(price, sma10, sma50, sma200, rsi)

        # RSI label
        if rsi < 30:   rsi_label = "🔥 Oversold"
        elif rsi > 70: rsi_label = "⚠️ Overbought"
        else:          rsi_label = "➡️ Netral"

        return {
            "ticker":     ticker_id,
            "price":      price,
            "chg_pct":    chg_pct,
            "sma10":      sma10,
            "sma50":      sma50,
            "sma200":     sma200,
            "rsi":        rsi,
            "rsi_label":  rsi_label,
            "vol_ratio":  vol_ratio,
            "support":    support,
            "resistance": resistance,
            "signal":     signal,
        }
    except Exception as e:
        logger.warning(f"Gagal analisis {ticker_id}: {e}")
        return None

# ─── FORMAT MESSAGE ───────────────────────────────────────────────────────────

def build_message(results: list[dict]) -> str:
    now = datetime.now(WIB).strftime("%A, %d %B %Y — %H:%M WIB")

    # Sortir: BUY dulu, lalu HOLD, lalu SELL
    order = {"🟢 BUY": 0, "🟡 HOLD": 1, "🔴 SELL": 2}
    results.sort(key=lambda x: order.get(x["signal"], 9))

    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "📊 *LAPORAN HARIAN SAHAM IDX*",
        f"🗓 _{now}_",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    buy_count  = sum(1 for r in results if r["signal"] == "🟢 BUY")
    sell_count = sum(1 for r in results if r["signal"] == "🔴 SELL")
    hold_count = sum(1 for r in results if r["signal"] == "🟡 HOLD")

    lines += [
        f"📈 BUY: *{buy_count}*  |  ⏸ HOLD: *{hold_count}*  |  📉 SELL: *{sell_count}*",
        "",
    ]

    for r in results:
        chg_icon = "🔺" if r["chg_pct"] >= 0 else "🔻"
        vol_icon = "🔥" if r["vol_ratio"] >= 1.5 else ("📊" if r["vol_ratio"] >= 1.0 else "💤")

        lines += [
            f"━━━━━━━━━━━━━━━━━━━━━━━━",
            f"*{r['ticker']}*  {r['signal']}",
            f"💰 Harga: *{fmt(r['price'])}*  {chg_icon} {r['chg_pct']:+.2f}%",
            "",
            f"📐 *Teknikal:*",
            f"  SMA10 : {fmt(r['sma10'])}",
            f"  SMA50 : {fmt(r['sma50'])}",
            f"  SMA200: {fmt(r['sma200'])}",
            f"  RSI   : {r['rsi']} — {r['rsi_label']}",
            f"  Volume: {r['vol_ratio']}x rata-rata {vol_icon}",
            "",
            f"📍 Support : {fmt(r['support'])}",
            f"📍 Resist  : {fmt(r['resistance'])}",
            "",
        ]

    # Top picks
    buys = [r for r in results if r["signal"] == "🟢 BUY"]
    if buys:
        lines += [
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            "🎯 *TOP PICK HARI INI:*",
        ]
        for r in buys[:2]:
            tp1 = int(r["resistance"])
            sl  = int(r["support"])
            rr  = round((tp1 - r["price"]) / (r["price"] - sl), 1) if (r["price"] - sl) > 0 else "N/A"
            lines += [
                f"  ✅ *{r['ticker']}* — Entry: {fmt(r['price'])}",
                f"     TP1: {fmt(tp1)}  |  SL: {fmt(sl)}  |  R/R: 1:{rr}",
            ]
        lines.append("")

    lines += [
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "⚠️ _Disclaimer: Bukan saran investasi resmi._",
        "_Selalu gunakan manajemen risiko._",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    return "\n".join(lines)

# ─── MAIN JOB ─────────────────────────────────────────────────────────────────

async def send_daily_report(bot: Bot):
    logger.info("Mengambil data saham...")
    results = []
    for ticker_id, ticker_yf in WATCHLIST.items():
        data = analyze_stock(ticker_id, ticker_yf)
        if data:
            results.append(data)

    if not results:
        logger.warning("Tidak ada data saham yang berhasil diambil.")
        return

    msg = build_message(results)
    await bot.send_message(
        chat_id=CHAT_ID,
        text=msg,
        parse_mode=ParseMode.MARKDOWN,
    )
    logger.info(f"Laporan terkirim ke {CHAT_ID}")

# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

async def main():
    if not TELEGRAM_TOKEN or not CHAT_ID:
        raise ValueError("Set TELEGRAM_TOKEN dan CHAT_ID di environment variables!")

    bot = Bot(token=TELEGRAM_TOKEN)

    # Kirim sekali langsung saat start (untuk test)
    await send_daily_report(bot)

    # Jadwalkan pengiriman harian
    scheduler = AsyncIOScheduler(timezone=WIB)
    scheduler.add_job(
        send_daily_report,
        trigger="cron",
        hour=SEND_HOUR,
        minute=SEND_MINUTE,
        args=[bot],
    )
    scheduler.start()
    logger.info(f"Bot aktif — laporan dikirim setiap hari jam {SEND_HOUR:02d}:{SEND_MINUTE:02d} WIB")

    # Keep alive
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
