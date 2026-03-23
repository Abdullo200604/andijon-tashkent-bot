# Andijon-Tashkent Taxi Bot 🚕

Professional Telegram bot for taxi services between Andijon and Tashkent.

## Features
- Role-based system (Client, Taxi, Admin)
- Subscription management via Click & Manual payments
- Real-time order distribution
- Multi-bot support (Andijon-Tashkent & Tashkent-Andijon)

## Technologies
- Python 3.x
- aiogram 3.x
- aiosqlite
- python-dotenv

## Setup (Local)
1. Clone the repo
2. Install requirements: `pip install -r requirements.txt`
3. Configure `.env` file (see `.env.example`)
4. Run: `python bot.py`

## VPS Deployment (Kamatera / Ubuntu)
1. Update system: `sudo apt update && sudo apt upgrade -y`
2. Install Python: `sudo apt install python3-pip python3-venv -y`
3. Clone repo: `git clone https://github.com/Abdullo200604/andijon-tashkent-bot.git`
4. Setup venv: `cd andijon-tashkent-bot && python3 -m venv venv && source venv/bin/activate`
5. Install: `pip install -r requirements.txt`
6. Create `.env`: `nano .env` (copy your environment variables)
7. Run with systemd (Service) to keep it alive 24/7.