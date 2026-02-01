# Daily IPO Monitor

Automation that runs every day at **09:00 Dubai time (05:00 UTC)** and:

- Fetches **same-day** U.S. IPOs from Finnhub (date = today)
- Filters to **NYSE / NASDAQ** and status **expected / priced**
- Computes offer amount as **IPO price × shares** (uses **high-end** if price is a range)
- Sends an email alert if any IPOs exceed **$200M**

## How it works

- Script: `main.py`
- Scheduler: GitHub Actions cron (`.github/workflows/daily.yml`)
- Email delivery: Gmail SMTP (App Password)

## Required GitHub Secrets

If you wish to run this workflow in your own GitHub account, please **fork** this repository. You will need to add the secrets listed below to your forked repository, as security credentials do not transfer automatically.

Set them in: **Repo → Settings → Secrets and variables → Actions → Repository secrets**

- `FINNHUB_KEY` — Finnhub API key
- `EMAIL_USER` — Gmail address (sender/recipient)
- `EMAIL_PASS` — Gmail App Password (16 characters)

## Manual test

The workflow is scheduled to run automatically, but can be triggered on demand:

1. Go to **Actions**
2. Select **Daily IPO Monitor**
3. Click **Run workflow**

## Local run (optional)

```bash
pip install requests python-dotenv
export FINNHUB_KEY="..."
export EMAIL_USER="..."
export EMAIL_PASS="..."
python main.py
