import asyncio
import os
import logging
from datetime import datetime
import pytz
import yfinance as yf
import pandas as pd
import numpy as np
from telegram import Bot
from telegram.constants import ParseMode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
WIB = pytz.timezone("Asia/Jakarta")

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

def fmt(v):
    try:
        return "Rp {:,}".format(int(v)).replace(",", ".")
    except:
        return "N/A"

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return round(float((100 - 100 / (1 + rs)).iloc[-1]), 1)

def compute_sma(series, w):
    if len(series) < w:
        return None
    return round(float(series.rolling(w).mean().iloc[-1]), 0)

def get_signal(price, s10, s50, s200, rsi_val):
    score = 0
    if s10 and price > s10: score += 1
    if s50 and price > s50: score += 1
    if s200 and price > s200: score += 1
    if rsi_val < 40: score += 2
    if rsi_val > 70: score -= 2
    if score >= 3: return "BUY"
    if score >= 1: return "HOLD"
    return "SELL"

def analyze(tid, tyf):
    try:
        df = yf.download(tyf, period="1y", interval="1d", progress=False, auto_adjust=True)
        if df.empty or len(df) < 20:
            return None
        cl = df["Close"].squeeze()
        vo = df["Volume"].squeeze()
        price = round(float(cl.iloc[-1]), 0)
        prev = round(float(cl.iloc[-2]), 0)
        chg = round((price - prev) / prev * 100, 2)
        s10 = compute_sma(cl, 10)
        s50 = compute_sma(cl, 50)
        s200 = compute_sma(cl, 200)
        rsi_val = compute_rsi(cl)
        vol_avg = float(vo.rolling(20).mean().iloc[-1])
        vr = round(float(vo.iloc[-1]) / vol_avg, 1) if vol_avg else 1.0
        sup = round(float(cl.rolling(20).min().iloc[-1]), 0)
        res = round(float(cl.rolling(20).max().iloc[-1]), 0)
        sig = get_signal(price, s10, s50, s200, rsi_val)
        return dict(ticker=tid, price=price, chg=chg,
                    s10=s10, s50=s50, s200=s200,
                    rsi=rsi_val, vr=vr, sup=sup, res=res, sig=sig)
    except Exception as e:
        logger.warning("{}: {}".format(tid, e))
        return None

def build_message(results):
    now = datetime.now(WIB).strftime("%A, %d %B %Y - %H:%M WIB")
    order = {"BUY": 0, "HOLD": 1, "SELL": 2}
    results.sort(key=lambda x: order.get(x["sig"], 9))

    buy = sum(1 for r in results if r["sig"] == "BUY")
    hold = sum(1 for r in results if r["sig"] == "HOLD")
    sell = sum(1 for r in results if r["sig"] == "SELL")

    emoji = {"BUY": "BUY", "HOLD": "HOLD", "SELL": "SELL"}
    icon = {"BUY": "GREEN", "HOLD": "YELLOW", "SELL": "RED"}

    lines = [
        "================================",
        "LAPORAN HARIAN SAHAM IDX",
        now,
        "================================",
        "BUY: {}  |  HOLD: {}  |  SELL: {}".format(buy, hold, sell),
        "",
    ]

    for r in results:
        ci = "+" if r["chg"] >= 0 else ""
        vi = "VOL TINGGI" if r["vr"] >= 1.5 else ""
        sig_label = {"BUY": "[BUY]", "HOLD": "[HOLD]", "SELL": "[SELL]"}[r["sig"]]

        lines += [
            "--------------------------------",
            "{} {}".format(r["ticker"], sig_label),
            "Harga: {}  ({}{:.2f}%) {}".format(fmt(r["price"]), ci, r["chg"], vi),
            "SMA10:{} SMA50:{} SMA200:{}".format(fmt(r["s10"]), fmt(r["s50"]), fmt(r["s200"])),
            "RSI: {}  Volume: {}x".format(r["rsi"], r["vr"]),
            "Support:{} | Resist:{}".format(fmt(r["sup"]), fmt(r["res"])),
            "",
        ]

    buys = [r for r in results if r["sig"] == "BUY"]
    if buys:
        lines += ["================================", "TOP PICK HARI INI:"]
        for r in buys[:2]:
            rr = round((r["res"] - r["price"]) / (r["price"] - r["sup"]), 1) if r["price"] > r["sup"] else "N/A"
            lines += [
                "  {} - Entry: {}".format(r["ticker"], fmt(r["price"])),
                "  TP: {}  SL: {}  R/R: 1:{}".format(fmt(r["res"]), fmt(r["sup"]), rr),
            ]
        lines.append("")

    lines += [
        "================================",
        "Bukan saran investasi. Selalu pakai manajemen risiko.",
        "================================",
    ]
    return "\n".join(lines)

async def main():
    logger.info("Mengambil data saham...")
    results = []
    for tid, tyf in WATCHLIST.items():
        r = analyze(tid, tyf)
        if r:
            results.append(r)

    if not results:
        logger.error("Semua saham gagal diambil!")
        return

    msg = build_message(results)
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=CHAT_ID, text=msg)
    logger.info("Laporan terkirim!")

if __name__ == "__main__":
    asyncio.run(main())
