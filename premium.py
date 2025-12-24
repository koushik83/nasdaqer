import requests
import time
import os
from datetime import datetime, timedelta
import pytz
from twilio.rest import Client
from dotenv import load_dotenv

# Load .env file for local development
# small change
load_dotenv()

# --- TWILIO CONFIG (from environment variables) ---
TWILIO_SID = os.environ.get('TWILIO_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NO = os.environ.get('TWILIO_PHONE_NO')
FROM_WHATSAPP = os.environ.get('FROM_WHATSAPP')
TO_PHONE = os.environ.get('TO_PHONE')
TARGET_PREMIUM_LIMIT = 2.0

# Debug: Print all env vars at startup
print("=== ENV VAR CHECK ===")
print(f"TWILIO_SID: {'SET' if TWILIO_SID else 'MISSING'}")
print(f"TWILIO_AUTH_TOKEN: {'SET' if TWILIO_AUTH_TOKEN else 'MISSING'}")
print(f"TWILIO_PHONE_NO: {TWILIO_PHONE_NO or 'MISSING'}")
print(f"FROM_WHATSAPP: {FROM_WHATSAPP or 'MISSING'}")
print(f"TO_PHONE: {TO_PHONE or 'MISSING'}")
print("=" * 50)

IST = pytz.timezone('Asia/Kolkata')

def get_official_nav():
    """Fetches the latest official Closing NAV from AMFI Portal (live data)"""
    try:
        r = requests.get('https://portal.amfiindia.com/spages/NAVAll.txt', timeout=10)
        for line in r.text.splitlines():
            if '114984' in line:  # MON100 ETF scheme code
                return float(line.split(';')[4])
    except:
        pass
    return 223.52  # Fallback to recent known NAV if API fails

def get_live_market_data():
    """Gets Live ETF Price and Live USDINR from Yahoo Finance (v8 API)"""
    headers = {'User-Agent': 'Mozilla/5.0'}

    # Get ETF price
    url_etf = "https://query1.finance.yahoo.com/v8/finance/chart/MON100.NS"
    r_etf = requests.get(url_etf, headers=headers, timeout=10).json()
    etf_price = r_etf['chart']['result'][0]['meta']['regularMarketPrice']

    # Get USDINR
    url_fx = "https://query1.finance.yahoo.com/v8/finance/chart/USDINR=X"
    r_fx = requests.get(url_fx, headers=headers, timeout=10).json()
    live_usdinr = r_fx['chart']['result'][0]['meta']['regularMarketPrice']
    prev_usdinr = r_fx['chart']['result'][0]['meta']['previousClose']

    return etf_price, live_usdinr, prev_usdinr

def is_market_open():
    """Checks if current time is within NSE market hours (9:15 - 15:30 IST)"""
    now = datetime.now(IST)
    if now.weekday() > 4:
        return False
    start_time = now.replace(hour=9, minute=15, second=0, microsecond=0)
    end_time = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return start_time <= now <= end_time

def seconds_until_market_open():
    """Calculate seconds until next market open (9:10 AM IST, 5 mins early buffer)"""
    now = datetime.now(IST)

    # Target: 9:10 AM (5 min before market opens)
    next_open = now.replace(hour=9, minute=10, second=0, microsecond=0)

    # If it's already past 9:10 AM today, target tomorrow
    if now >= next_open:
        next_open += timedelta(days=1)

    # Skip weekends
    while next_open.weekday() > 4:  # 5=Saturday, 6=Sunday
        next_open += timedelta(days=1)

    sleep_seconds = (next_open - now).total_seconds()
    return int(sleep_seconds), next_open

def trigger_alert(premium, m_price, current_inav):
    """Send WhatsApp message and voice call via Twilio"""
    client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)

    msg_text = f"🚨 NASDAQ PREMIUM ALERT!\n\nPremium: {premium:.2f}%\nMarket Price: ₹{m_price:.2f}\nEst. iNAV: ₹{current_inav:.2f}\n\nSnipe it now bro! 🎯"

    # 1. Send WhatsApp
    try:
        client.messages.create(body=msg_text, from_=FROM_WHATSAPP, to=f'whatsapp:{TO_PHONE}')
        print("WhatsApp sent!")
    except Exception as e:
        print(f"WhatsApp Error: {e}")

    # 2. Voice Call
    try:
        client.calls.create(
            twiml=f'<Response><Say voice="alice" loop="2">Alert! NASDAQ premium is now {premium:.1f} percent. Time to snipe!</Say></Response>',
            to=TO_PHONE,
            from_=TWILIO_PHONE_NO
        )
        print("Call initiated!")
    except Exception as e:
        print(f"Call Error: {e}")

# --- MAIN ENGINE ---
print("=" * 50)
print("NASDAQ Speed Bot v2.0 - Started")
print("=" * 50)

official_nav = get_official_nav()
print(f"Official Closing NAV (AMFI): Rs {official_nav}")
print(f"Target Premium: <= {TARGET_PREMIUM_LIMIT}%")
print(f"Alerts will be sent to: {TO_PHONE}")
print("=" * 50)

alert_sent_today = False

while True:
    now = datetime.now(IST)

    # Reset alert flag at start of new day
    if now.hour == 9 and now.minute == 15:
        alert_sent_today = False
        official_nav = get_official_nav()  # Refresh NAV at market open
        print(f"New day! Refreshed NAV: Rs {official_nav}")

    if is_market_open():
        try:
            m_price, live_fx, closed_fx = get_live_market_data()

            # Calculate live fair value (iNAV estimate)
            current_inav = official_nav * (live_fx / closed_fx)
            premium = ((m_price - current_inav) / current_inav) * 100

            fx_change = ((live_fx - closed_fx) / closed_fx) * 100
            print(f"[{now.strftime('%H:%M:%S')}] Price: Rs {m_price:.2f} | NAV: Rs {official_nav:.2f} | FX: {closed_fx:.2f} -> {live_fx:.2f} ({fx_change:+.2f}%) | Adj iNAV: Rs {current_inav:.2f} | Premium: {premium:.2f}%")

            if premium <= TARGET_PREMIUM_LIMIT and not alert_sent_today:
                print(">>> TARGET HIT! Triggering alerts...")
                trigger_alert(premium, m_price, current_inav)
                alert_sent_today = True
                time.sleep(3600)  # Wait 1 hour before checking again

        except Exception as e:
            print(f"Error: {e}")

        time.sleep(600)  # Check every 10 minutes during market hours
    else:
        sleep_secs, next_open = seconds_until_market_open()
        hours = sleep_secs // 3600
        mins = (sleep_secs % 3600) // 60
        print(f"[{now.strftime('%H:%M')}] Market closed. Next open: {next_open.strftime('%A %d-%b %H:%M')} IST ({hours}h {mins}m)")

        # Sleep in 30-min chunks to keep container alive on Railway
        while sleep_secs > 0:
            chunk = min(1800, sleep_secs)  # 30 min max
            time.sleep(chunk)
            sleep_secs -= chunk
            if sleep_secs > 0:
                print(f"[{datetime.now(IST).strftime('%H:%M')}] Still waiting... {sleep_secs // 3600}h {(sleep_secs % 3600) // 60}m to go")
