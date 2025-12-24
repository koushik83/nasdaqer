import requests
import time
import os
from datetime import datetime
import pytz
from twilio.rest import Client
from dotenv import load_dotenv

# Load .env file for local development
load_dotenv()

# --- TWILIO CONFIG (from environment variables) ---
TWILIO_SID = os.environ.get('TWILIO_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NO = os.environ.get('TWILIO_PHONE_NO')
FROM_WHATSAPP = os.environ.get('FROM_WHATSAPP')
TO_PHONE = os.environ.get('TO_PHONE')
TARGET_PREMIUM_LIMIT = 2.0

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
print(f"Official Closing NAV (AMFI): ₹{official_nav}")
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
        print(f"New day! Refreshed NAV: ₹{official_nav}")

    if is_market_open():
        try:
            m_price, live_fx, closed_fx = get_live_market_data()

            # Calculate live fair value (iNAV estimate)
            current_inav = official_nav * (live_fx / closed_fx)
            premium = ((m_price - current_inav) / current_inav) * 100

            print(f"[{now.strftime('%H:%M:%S')}] Price: ₹{m_price:.2f} | iNAV: ₹{current_inav:.2f} | FX: {live_fx:.2f} | Premium: {premium:.2f}%")

            if premium <= TARGET_PREMIUM_LIMIT and not alert_sent_today:
                print("🎯 TARGET HIT! Triggering alerts...")
                trigger_alert(premium, m_price, current_inav)
                alert_sent_today = True
                time.sleep(3600)  # Wait 1 hour before checking again

        except Exception as e:
            print(f"Error: {e}")

        time.sleep(120)  # Check every 2 minutes during market hours
    else:
        print(f"[{now.strftime('%H:%M')}] Market closed. Sleeping...")
        time.sleep(600)  # Sleep 10 mins when market is closed
