import os
import smtplib
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from email.message import EmailMessage


# Config
THRESHOLD_USD = 200_000_000
DUBAI_TZ = ZoneInfo("Asia/Dubai")
FINNHUB_URL = "https://finnhub.io/api/v1/calendar/ipo"


# Helpers
def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

def dubai_today_iso() -> str:
    return datetime.now(DUBAI_TZ).date().isoformat()

def parse_price_range(price_raw):
    if price_raw is None:
        return 0.0, 0.0

    s = str(price_raw).strip().replace("$", "")
    if not s or s == "-":
        return 0.0, 0.0

    try:
        if "-" in s:
            parts = [p.strip() for p in s.split("-") if p.strip()]
            if len(parts) >= 2:
                low = float(parts[0])
                high = float(parts[1])
                return low, high
            v = float(parts[-1])
            return v, v
        v = float(s)
        return v, v
    except ValueError:
        return 0.0, 0.0

def compute_offer(price_raw, shares):
    try:
        shares_f = float(shares) if shares is not None else 0.0
    except (TypeError, ValueError):
        shares_f = 0.0

    low, high = parse_price_range(price_raw)
    offer_low = low * shares_f
    offer_high = high * shares_f
    return offer_low, offer_high

def fetch_ipos(from_date: str, to_date: str, token: str) -> list[dict]:
    params = {"from": from_date, "to": to_date, "token": token}
    resp = requests.get(FINNHUB_URL, params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    return data.get("ipoCalendar") or []

def send_email(subject: str, body: str, email_user: str, email_pass: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = email_user
    msg["To"] = email_user
    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as smtp:
        smtp.login(email_user, email_pass)
        smtp.send_message(msg)


def run():
    finnhub_key = require_env("FINNHUB_KEY")
    email_user = require_env("EMAIL_USER")
    email_pass = require_env("EMAIL_PASS")

    today = dubai_today_iso()
    print(f"[INFO] Dubai date: {today}")
    print("[INFO] Fetching same-day IPOs from Finnhub...")

    try:
        ipos = fetch_ipos(today, today, finnhub_key)

        matches = []
        for ipo in ipos:
            ipo_date = ipo.get("date", "N/A")
            symbol = ipo.get("symbol")
            name = ipo.get("name", "N/A")
            exchange = ipo.get("exchange", "N/A")
            status = (ipo.get("status", "N/A") or "").lower()
            price_raw = ipo.get("price")
            shares = ipo.get("numberOfShares")

            if ipo_date != today:
                continue
            if status not in {"expected", "priced"}:
                continue
            if not exchange or ("NASDAQ" not in str(exchange) and "NYSE" not in str(exchange)):
                continue
            if not symbol or price_raw in (None, "", "-") or shares in (None, ""):
                continue

            _, offer = compute_offer(price_raw, shares)

            # Debug
            print(
                f"[DEBUG] {symbol} | {status} | {exchange} | price={price_raw} | shares={shares} "
                f"| offer_high(price×shares)=${offer:,.0f} | finnhub_total={ipo.get('totalSharesValue')}"
            )

            if offer > THRESHOLD_USD:
                finnhub_total = ipo.get("totalSharesValue")
                shares_int = int(float(shares))

                matches.append(
                    f"{symbol} ({name})\n"
                    f"  Exchange: {exchange}\n"
                    f"  Status: {status}\n"
                    f"  Price: {price_raw} | Shares: {shares_int:,}\n"
                    f"  Est. Offer: ${offer:,.0f}\n"
                    f"  Finnhub totalSharesValue: {f'${float(finnhub_total):,.0f}' if finnhub_total else 'N/A'}"
                )

        # Always email
        if matches:
            subject = f"IPO Report [{today}]: {len(matches)} tickers > $200M"
            body = (
                "Same-day US IPOs exceeding $200M:\n\n"
                + "\n---------------------------------------\n".join(matches)
            )
        else:
            subject = f"IPO Report [{today}]: No tickers > $200M"
            body = "Automation ran successfully. No same-day US IPOs exceeded $200M (price × shares)."

        send_email(subject, body, email_user, email_pass)
        print("[INFO] Email sent.")

    except Exception as e:
        # Send error email + re-raise so GH Actions shows failure clearly
        err_subject = f"IPO Monitor ERROR [{today}]"
        err_body = f"Automation failed:\n\n{repr(e)}"
        try:
            send_email(err_subject, err_body, email_user, email_pass)
            print("[WARN] Error email sent.")
        except:
            pass
        raise


if __name__ == "__main__":
    run()
