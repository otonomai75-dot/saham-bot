"""
saham-bot — Telegram bot pengirim laporan saham IDX harian.

Refactor full (v2.1):
- Async-safe: yfinance dijalankan di thread executor
- Robust error handling: bot tidak crash kalau 1 saham/Telegram gagal
- HTML parse mode (lebih aman dari Markdown untuk karakter spesial)
- Retry mechanism untuk yfinance (network kadang flaky)
- Logging detail untuk debug deployment
- Validasi env var lebih jelas
- Mode RUN_ONCE: kirim laporan 1x lalu exit (untuk GitHub Actions / cron eksternal)
- Mode default (long-running): scheduler internal harian (untuk Railway/Render/local)
"""

import os
import asyncio
import logging
import html
from datetime import datetime
from typing import Optional

import pytz
import yfinance as yf
import pandas as pd
import numpy as np
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ─── LOGGING ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("saham-bot")
# Reduce noise dari library lain
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("yfinance").setLevel(logging.ERROR)

# ─── CONFIG ───────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
CHAT_ID = os.environ.get("CHAT_ID", "").strip()
WIB = pytz.timezone("Asia/Jakarta")
SEND_HOUR = int(os.environ.get("SEND_HOUR", "7"))
SEND_MINUTE = int(os.environ.get("SEND_MINUTE", "0"))
SEND_ON_START = os.environ.get("SEND_ON_START", "true").lower() == "true"
# RUN_ONCE=true → kirim laporan 1x lalu exit (mode untuk GitHub Actions / cron eksternal).
# Default false agar pemakaian lokal/Railway tetap pakai scheduler internal.
RUN_ONCE = os.environ.get("RUN_ONCE", "false").lower() == "true"

# Watchlist saham IDX (tambah/kurangi sesuai selera)
WATCHLIST = {
    "BRPT": "BRPT.JK",
    "CDIA": "CDIA.JK",
    "BBRI": "BBRI.JK",
    "TLKM": "TLKM.JK",
    "ISAT": "ISAT.JK",
    "PTRO": "PTRO.JK",
    "RATU": "RATU.JK",
    "ASII": "ASII.JK",
    "BMRI": "BMRI.JK",
    "GOTO": "GOTO.JK",
}

# Telegram message hard limit
TELEGRAM_MAX_LEN = 4000  # safety margin dari 4096


# ─── TECHNICAL INDICATORS ─────────────────────────────────────────────────────

def compute_rsi(series: pd.Series, period: int = 14) -> Optional[float]:
    """Hitung RSI dengan rolling mean (versi sederhana)."""
    if len(series) < period + 1:
        return None
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    if pd.isna(val):
        return None
    return round(float(val), 1)


def compute_sma(series: pd.Series, window: int) -> Optional[float]:
    if len(series) < window:
        return None
    val = series.rolling(window).mean().iloc[-1]
    if pd.isna(val):
        return None
    return round(float(val), 0)


def get_signal(price, sma10, sma50, sma200, rsi) -> str:
    """Sinyal sederhana: skor multi-faktor."""
    score = 0
    if sma10 and price > sma10:
        score += 1
    if sma50 and price > sma50:
        score += 1
    if sma200 and price > sma200:
        score += 1
    if rsi is not None:
        if rsi < 40:
            score += 2  # oversold = potensi beli
        if rsi > 70:
            score -= 2  # overbought
    if score >= 3:
        return "🟢 BUY"
    if score >= 1:
        return "🟡 HOLD"
    return "🔴 SELL"


def fmt(val, prefix: str = "Rp ") -> str:
    if val is None:
        return "N/A"
    try:
        return f"{prefix}{int(val):,}".replace(",", ".")
    except (ValueError, TypeError):
        return "N/A"


# ─── FETCH & ANALYZE ──────────────────────────────────────────────────────────

def _fetch_stock_data(ticker_yf: str, retries: int = 2) -> Optional[pd.DataFrame]:
    """Fetch data dari yfinance dengan retry. Sync function."""
    for attempt in range(retries + 1):
        try:
            df = yf.download(
                ticker_yf,
                period="1y",
                interval="1d",
                progress=False,
                auto_adjust=True,
                threads=False,  # kurangi konflik di async env
            )
            if not df.empty and len(df) >= 20:
                return df
            logger.warning(f"  → {ticker_yf}: data kosong/kurang (attempt {attempt + 1})")
        except Exception as e:
            logger.warning(f"  → {ticker_yf}: error fetch (attempt {attempt + 1}) — {e}")
        if attempt < retries:
            # Sleep singkat sebelum retry (sync, OK karena dipanggil via to_thread)
            import time
            time.sleep(1.5)
    return None


def analyze_stock_sync(ticker_id: str, ticker_yf: str) -> Optional[dict]:
    """Analisa 1 saham. Sync — wajib dipanggil via asyncio.to_thread."""
    try:
        df = _fetch_stock_data(ticker_yf)
        if df is None:
            return None

        close = df["Close"].squeeze()
        volume = df["Volume"].squeeze()

        price = round(float(close.iloc[-1]), 0)
        prev = round(float(close.iloc[-2]), 0)
        chg_pct = round((price - prev) / prev * 100, 2) if prev else 0.0

        sma10 = compute_sma(close, 10)
        sma50 = compute_sma(close, 50)
        sma200 = compute_sma(close, 200)
        rsi = compute_rsi(close)

        try:
            vol_today = int(volume.iloc[-1])
            vol_avg = int(volume.rolling(20).mean().iloc[-1])
            vol_ratio = round(vol_today / vol_avg, 1) if vol_avg else 1.0
        except (ValueError, TypeError):
            vol_ratio = 1.0

        # Support / Resistance sederhana (20-day low/high)
        support = round(float(close.rolling(20).min().iloc[-1]), 0)
        resistance = round(float(close.rolling(20).max().iloc[-1]), 0)

        signal = get_signal(price, sma10, sma50, sma200, rsi)

        # RSI label
        if rsi is None:
            rsi_label = "N/A"
        elif rsi < 30:
            rsi_label = "🔥 Oversold"
        elif rsi > 70:
            rsi_label = "⚠️ Overbought"
        else:
            rsi_label = "➡️ Netral"

        return {
            "ticker": ticker_id,
            "price": price,
            "chg_pct": chg_pct,
            "sma10": sma10,
            "sma50": sma50,
            "sma200": sma200,
            "rsi": rsi if rsi is not None else 0,
            "rsi_label": rsi_label,
            "vol_ratio": vol_ratio,
            "support": support,
            "resistance": resistance,
            "signal": signal,
        }
    except Exception as e:
        logger.warning(f"Gagal analisis {ticker_id}: {e}")
        return None


async def analyze_stock(ticker_id: str, ticker_yf: str) -> Optional[dict]:
    """Async wrapper — jalankan analisa di thread executor agar tidak blocking."""
    return await asyncio.to_thread(analyze_stock_sync, ticker_id, ticker_yf)


# ─── FORMAT MESSAGE (HTML mode — lebih aman) ──────────────────────────────────

def esc(text) -> str:
    """Escape karakter HTML untuk Telegram."""
    return html.escape(str(text), quote=False)


def build_message(results: list) -> str:
    now = datetime.now(WIB).strftime("%A, %d %B %Y — %H:%M WIB")

    # Sortir: BUY dulu, lalu HOLD, lalu SELL
    order = {"🟢 BUY": 0, "🟡 HOLD": 1, "🔴 SELL": 2}
    results.sort(key=lambda x: order.get(x["signal"], 9))

    buy_count = sum(1 for r in results if r["signal"] == "🟢 BUY")
    sell_count = sum(1 for r in results if r["signal"] == "🔴 SELL")
    hold_count = sum(1 for r in results if r["signal"] == "🟡 HOLD")

    lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "📊 <b>LAPORAN HARIAN SAHAM IDX</b>",
        f"🗓 <i>{esc(now)}</i>",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"📈 BUY: <b>{buy_count}</b>  |  ⏸ HOLD: <b>{hold_count}</b>  |  📉 SELL: <b>{sell_count}</b>",
        "",
    ]

    for r in results:
        chg_icon = "🔺" if r["chg_pct"] >= 0 else "🔻"
        vol_icon = "🔥" if r["vol_ratio"] >= 1.5 else ("📊" if r["vol_ratio"] >= 1.0 else "💤")

        lines += [
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            f"<b>{esc(r['ticker'])}</b>  {r['signal']}",
            f"💰 Harga: <b>{esc(fmt(r['price']))}</b>  {chg_icon} {r['chg_pct']:+.2f}%",
            "",
            "📐 <b>Teknikal:</b>",
            f"  SMA10 : {esc(fmt(r['sma10']))}",
            f"  SMA50 : {esc(fmt(r['sma50']))}",
            f"  SMA200: {esc(fmt(r['sma200']))}",
            f"  RSI   : {r['rsi']} — {r['rsi_label']}",
            f"  Volume: {r['vol_ratio']}x rata-rata {vol_icon}",
            "",
            f"📍 Support : {esc(fmt(r['support']))}",
            f"📍 Resist  : {esc(fmt(r['resistance']))}",
            "",
        ]

    # Top picks
    buys = [r for r in results if r["signal"] == "🟢 BUY"]
    if buys:
        lines += [
            "━━━━━━━━━━━━━━━━━━━━━━━━",
            "🎯 <b>TOP PICK HARI INI:</b>",
        ]
        for r in buys[:2]:
            tp1 = int(r["resistance"])
            sl = int(r["support"])
            risk = r["price"] - sl
            rr = round((tp1 - r["price"]) / risk, 1) if risk > 0 else "N/A"
            lines += [
                f"  ✅ <b>{esc(r['ticker'])}</b> — Entry: {esc(fmt(r['price']))}",
                f"     TP1: {esc(fmt(tp1))}  |  SL: {esc(fmt(sl))}  |  R/R: 1:{rr}",
            ]
        lines.append("")

    lines += [
        "━━━━━━━━━━━━━━━━━━━━━━━━",
        "⚠️ <i>Disclaimer: Bukan saran investasi resmi.</i>",
        "<i>Selalu gunakan manajemen risiko.</i>",
        "━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    msg = "\n".join(lines)

    # Truncate kalau kepanjangan (safety)
    if len(msg) > TELEGRAM_MAX_LEN:
        msg = msg[:TELEGRAM_MAX_LEN - 50] + "\n\n... <i>(pesan dipotong)</i>"

    return msg


# ─── TELEGRAM SEND (dengan retry & error handling) ────────────────────────────

async def safe_send_message(bot: Bot, text: str, retries: int = 2) -> bool:
    """Kirim pesan dengan retry. Return True kalau sukses."""
    for attempt in range(retries + 1):
        try:
            await bot.send_message(
                chat_id=CHAT_ID,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            return True
        except TelegramError as e:
            logger.error(f"Telegram error (attempt {attempt + 1}): {e}")
            if attempt < retries:
                await asyncio.sleep(2)
        except Exception as e:
            logger.error(f"Unexpected error saat kirim (attempt {attempt + 1}): {e}")
            if attempt < retries:
                await asyncio.sleep(2)
    return False


# ─── MAIN JOB ─────────────────────────────────────────────────────────────────

async def send_daily_report(bot: Bot):
    """Job utama — fetch semua saham, build message, kirim."""
    logger.info("=" * 50)
    logger.info("Mulai mengambil data saham...")
    results = []

    # Fetch paralel (max 3 sekaligus biar ga di-rate-limit yfinance)
    semaphore = asyncio.Semaphore(3)

    async def fetch_with_limit(tid, tyf):
        async with semaphore:
            return await analyze_stock(tid, tyf)

    tasks = [fetch_with_limit(tid, tyf) for tid, tyf in WATCHLIST.items()]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    for item in raw_results:
        if isinstance(item, Exception):
            logger.warning(f"Task exception: {item}")
            continue
        if item:
            results.append(item)

    logger.info(f"Berhasil analisa {len(results)}/{len(WATCHLIST)} saham")

    if not results:
        logger.warning("Tidak ada data saham yang berhasil diambil. Kirim notifikasi error.")
        await safe_send_message(
            bot,
            "⚠️ <b>Bot Saham Alert</b>\n\nTidak bisa ambil data saham hari ini. "
            "Cek log server atau coba lagi nanti.",
        )
        return

    msg = build_message(results)
    success = await safe_send_message(bot, msg)
    if success:
        logger.info(f"✅ Laporan terkirim ke chat {CHAT_ID}")
    else:
        logger.error(f"❌ Gagal kirim laporan ke chat {CHAT_ID} setelah retry")


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

def validate_env():
    """Validasi environment variables di awal — gagal fast & jelas."""
    missing = []
    if not TELEGRAM_TOKEN:
        missing.append("TELEGRAM_TOKEN")
    if not CHAT_ID:
        missing.append("CHAT_ID")
    if missing:
        raise ValueError(
            f"❌ Environment variable wajib belum di-set: {', '.join(missing)}\n"
            f"   Set di GitHub Secrets / Railway / Render dashboard sebelum deploy."
        )
    logger.info("✅ Env vars OK")
    logger.info(f"   CHAT_ID: {CHAT_ID}")
    logger.info(f"   RUN_ONCE: {RUN_ONCE}")
    if not RUN_ONCE:
        logger.info(f"   Schedule: setiap hari {SEND_HOUR:02d}:{SEND_MINUTE:02d} WIB")
        logger.info(f"   SEND_ON_START: {SEND_ON_START}")


async def run_once_mode(bot: Bot):
    """Mode 1-shot: kirim laporan sekali lalu exit. Ideal untuk GitHub Actions cron."""
    logger.info("⚡ RUN_ONCE mode aktif → kirim laporan 1x lalu exit")
    await send_daily_report(bot)
    logger.info("✅ RUN_ONCE selesai. Exiting.")


async def run_long_mode(bot: Bot):
    """Mode long-running: scheduler internal + keep-alive loop. Untuk Railway/local."""
    # Kirim startup ping (ringan, bukan full report) supaya tahu bot hidup
    try:
        await safe_send_message(
            bot,
            f"🟢 <b>Saham-bot online!</b>\n\n"
            f"📅 Jadwal kirim: setiap hari <b>{SEND_HOUR:02d}:{SEND_MINUTE:02d} WIB</b>\n"
            f"📊 Watchlist: <b>{len(WATCHLIST)}</b> saham\n"
            f"⏰ Server time: {datetime.now(WIB).strftime('%H:%M WIB')}",
        )
    except Exception as e:
        logger.warning(f"Startup ping gagal (tidak fatal): {e}")

    # Setup scheduler dulu sebelum kirim report (biar scheduler aktif walau report awal lambat)
    scheduler = AsyncIOScheduler(timezone=WIB)
    scheduler.add_job(
        send_daily_report,
        trigger="cron",
        hour=SEND_HOUR,
        minute=SEND_MINUTE,
        args=[bot],
        misfire_grace_time=300,  # toleransi 5 menit kalau server sibuk
        coalesce=True,
    )
    scheduler.start()
    logger.info(f"⏰ Scheduler aktif — laporan harian {SEND_HOUR:02d}:{SEND_MINUTE:02d} WIB")

    # Kirim laporan langsung saat start (untuk test) — non-blocking via task
    if SEND_ON_START:
        logger.info("📤 SEND_ON_START=true → kirim laporan langsung (background task)...")
        asyncio.create_task(send_daily_report(bot))

    # Keep alive — loop forever
    logger.info("✅ Bot running. Ctrl+C untuk stop.")
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("🛑 Shutdown signal received...")
    finally:
        scheduler.shutdown(wait=False)
        logger.info("👋 Bot stopped.")


async def main():
    logger.info("🚀 Saham-bot starting...")
    validate_env()

    bot = Bot(token=TELEGRAM_TOKEN)

    # Test koneksi Telegram dulu
    try:
        me = await bot.get_me()
        logger.info(f"✅ Connected as bot: @{me.username}")
    except Exception as e:
        logger.error(f"❌ Gagal connect ke Telegram API: {e}")
        raise

    if RUN_ONCE:
        await run_once_mode(bot)
    else:
        await run_long_mode(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.exception(f"💥 Fatal error: {e}")
        raise
