\"\"\"saham-bot FIXED - no event loop error\"\"\"

import asyncio
import os
import logging
from datetime import datetime

import pytz
import yfinance as yf
import pandas as pd
from telegram.ext import Application, CommandHandler
from telegram.constants import ParseMode

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(\"saham-bot\")

TELEGRAM_TOKEN = os.environ[\"TELEGRAM_TOKEN\"]
CHAT_ID = os.environ[\"CHAT_ID\"]
WIB = pytz.timezone(\"Asia/Jakarta\")

WATCHLIST = {
    \"BRPT\": \"BRPT.JK\",
    \"CDIA\": \"CDIA.JK\",
    \"BBRI\": \"BBRI.JK\",
    \"TLKM\": \"TLKM.JK\",
    \"ISAT\": \"ISAT.JK\",
    \"PTRO\": \"PTRO.JK\",
    \"RATU\": \"RATU.JK\",
    \"ASII\": \"ASII.JK\",
    \"BMRI\": \"BMRI.JK\",
    \"GOTO\": \"GOTO.JK\",
}

def fmt(val):
    return f\"Rp {int(val):,}\".replace(\",\", \".\") if val else \"N/A\"

async def get_report():
    semaphore = asyncio.Semaphore(3)
    
    async def fetch_stock(tid, tyf):
        async with semaphore:
            try:
                df = yf.download(tyf, period=\"1y\", progress=False)
                close = df[\"Close\"][-20:]
                
                price = float(close.iloc[-1])
                support = float(close.min())
                resistance = float(close.max())
                
                rsi_period = 14
                delta = close.diff()
                gain = delta.clip(lower=0).rolling(rsi_period).mean()
                loss = -delta.clip(upper=0).rolling(rsi_period).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                rsi_val = rsi.iloc[-1]
                
                sma10 = close.rolling(10).mean().iloc[-1]
                sma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else None
                
                score = 0
                if price > sma10:
                    score += 1
                if sma50 and price > sma50:
                    score += 1
                if rsi_val < 40:
                    score += 2
                if rsi_val > 70:
                    score -= 2
                
                signal = \"🟢 BUY\" if score >= 3 else \"🟡 HOLD\" if score >= 1 else \"🔴 SELL\"
                
                return {
                    \"ticker\": tid,
                    \"price\": price,
                    \"support\": support,
                    \"resistance\": resistance,
                    \"signal\": signal,
                }
            except Exception as e:
                logger.warning(f\"{tid}: {e}\")
                return None
    
    tasks = [fetch_stock(tid, tyf) for tid, tyf in WATCHLIST.items()]
    results = [r for r in await asyncio.gather(*tasks) if r]
    
    if not results:
        return \"❌ No data\"
    
    now = datetime.now(WIB).strftime(\"%d %B %Y %H:%M WIB\")
    lines = [
        \"📊 <b>LAPORAN SAHAM</b>\",
        f\"🗓 {now}\",
        \"━━━━━━━━━━━━━━━━\",
    ]
    
    for r in results:
        tp1 = r[\"resistance\"]
        sl = r[\"support\"]
        risk = r[\"price\"] - sl
        rr = round((tp1 - r[\"price\"]) / risk, 1) if risk > 0 else \"N/A\"
        lines += [
            f\"<b>{r['ticker']}</b> {r['signal']}\",
            f\"💰 {fmt(r['price'])}\",
            f\"📈 TP1: {fmt(tp1)}\",
            f\"🛑 SL: {fmt(sl)}\",
            f\"⚖️ R/R 1:{rr}\",
            \"\",
        ]
    
    lines += [\"⚠️ Estimasi teknikal. DYOR!\"]
    return \"\\n\".join(lines)

async def start(update, context):
    await update.message.reply_text(
        \"🟢 Saham Bot OK!\n\n/update - Report + harga jual\n/start - Help\",
        parse_mode=ParseMode.HTML
    )

async def update_cmd(update, context):
    await update.message.reply_text(\"⏳ Loading...\")
    report = await get_report()
    await update.message.reply_text(report, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

async def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler(\"start\", start))
    app.add_handler(CommandHandler(\"update\", update_cmd))
    logger.info(\"Bot running. Chat /update!\")
    await app.run_polling()

if __name__ == \"__main__\": 
    asyncio.run(main())

