# NASDAQ ETF Premium Monitor Bot

A bot that monitors the premium on **MON100.NS** (Motilal Oswal NASDAQ 100 ETF) and alerts you via WhatsApp + Voice Call when the premium drops to your target level.

## Status: LIVE on Railway.com

The bot is deployed and running on Railway.com

## How It Works

1. **Fetches Official NAV** from AMFI Portal (portal.amfiindia.com)
2. **Gets Live ETF Price** from Yahoo Finance
3. **Gets USD/INR Rate** (live vs previous close) from Yahoo Finance
4. **Calculates Adjusted iNAV**: `NAV × (live_fx / closed_fx)`
5. **Calculates Premium**: `((market_price - adj_inav) / adj_inav) × 100`
6. **Alerts** when premium <= 2% via Twilio (WhatsApp + Voice Call)

## Schedule

- **Market Hours (9:15 AM - 3:30 PM IST)**: Checks every 10 minutes
- **After Hours**: Sleeps until next market open (9:10 AM IST)
- **Weekends**: Sleeps until Monday 9:10 AM IST

## Environment Variables (set in Railway)

```
TWILIO_SID          = your_twilio_sid
TWILIO_AUTH_TOKEN   = your_twilio_auth_token
TWILIO_PHONE_NO     = +1xxxxxxxxxx  (Twilio calling number)
FROM_WHATSAPP       = whatsapp:+14155238886  (Twilio sandbox)
TO_PHONE            = +91xxxxxxxxxx  (Your phone number)
```

## PENDING: Keep WhatsApp Sandbox Active

Since we're using **Twilio WhatsApp Sandbox** (not a production WhatsApp Business account), you need to:

1. **Join the sandbox** by sending a message to the Twilio WhatsApp number
2. **Keep it active** - The sandbox expires after 72 hours of inactivity

### To keep it active:
- Send any message to the Twilio WhatsApp sandbox number (`+14155238886`) at least once every 3 days
- Or upgrade to a Twilio WhatsApp Business account (paid)

### Sandbox Join Command:
Send this message to `+14155238886` on WhatsApp:
```
join <your-sandbox-keyword>
```
(Check your Twilio Console for the exact join phrase)

## Local Development

1. Clone the repo
2. Create `.env` file with the environment variables above
3. Run: `pip install -r requirements.txt`
4. Run: `python premium.py`

## Built With

- Python
- Twilio (WhatsApp + Voice)
- Yahoo Finance API
- AMFI India Portal
