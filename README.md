# Traffic Guard

`Traffic Guard` is a small Python service that runs on each VPS, tracks consumed network traffic and sends Telegram alerts when configured thresholds are reached.

## What We Are Building

The practical MVP is:

1. One private Git project with the monitoring code.
2. The same service deployed on every VPS.
3. Each server stores its own counters locally.
4. Telegram messages identify the exact server and current usage.

This avoids a central database and works even when servers are independent.

## Plan

1. Create the repository structure and document the architecture.
2. Implement traffic accounting from Linux network interfaces.
3. Persist usage state across restarts and month boundaries.
4. Send Telegram alerts when thresholds are crossed.
5. Add deployment instructions for systemd on VPS.
6. Prepare the repo for the first private remote push.

## How It Works

The service reads `/proc/net/dev`, sums RX and TX bytes for selected interfaces and stores:

- current billing period
- last observed interface counters
- accumulated traffic for the period
- thresholds already notified

When the machine restarts and counters reset, the service detects it and continues from the new baseline without losing the accumulated monthly total.

## Current Scope

Included in this repository:

- one-shot check command
- daemon mode with interval polling
- JSON state file
- Telegram Bot API notifications
- systemd unit example

Not included yet:

- provider API integration
- central dashboard
- interactive Telegram commands

Those can be added later if you want a single control bot.

## Requirements On VPS

- Linux server with `/proc/net/dev`
- Python 3.11+
- outbound access to `api.telegram.org`

## Quick Start

Create and fill `.env`:

```bash
cp .env.example .env
```

Install locally on the server:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

Run one check:

```bash
set -a
source .env
set +a
traffic-guard check-once
```

Run as daemon:

```bash
set -a
source .env
set +a
traffic-guard daemon
```

## Install On A VPS

Clone the repository on the server:

```bash
git clone https://github.com/spacexerq/tg_bot_traffic.git /opt/traffic-guard-src
cd /opt/traffic-guard-src
git checkout codex/traffic-telegram-bot
```

Run the installer as root:

```bash
sudo bash scripts/install.sh
```

Edit the environment file:

```bash
sudo nano /etc/traffic-guard.env
```

Start and inspect the service:

```bash
sudo systemctl start traffic-guard
sudo systemctl status traffic-guard
sudo journalctl -u traffic-guard -f
```

## Environment Variables

- `TG_BOT_TOKEN`: Telegram bot token
- `TG_CHAT_ID`: target user, group or channel chat id
- `TG_SERVER_NAME`: server label in messages
- `TG_MONTHLY_LIMIT_GB`: monthly traffic cap in gigabytes
- `TG_ALERT_THRESHOLDS`: comma-separated percentage thresholds
- `TG_INTERFACE_INCLUDE`: optional comma-separated whitelist of interfaces
- `TG_INTERFACE_EXCLUDE`: comma-separated excluded interfaces
- `TG_STATE_FILE`: where the JSON state is stored
- `TG_CHECK_INTERVAL_SECONDS`: daemon polling interval

## Telegram Bot Setup

1. Create a bot through `@BotFather`.
2. Get the bot token.
3. Add the bot to the target chat or start a direct chat with it.
4. Obtain the chat id.

## Deployment With systemd

The example unit is in [deploy/systemd/traffic-guard.service](C:/Users/user.LAPTOP-M7DTCFMM/Documents/New%20project/deploy/systemd/traffic-guard.service).

Suggested layout on a server:

- app directory: `/opt/traffic-guard`
- env file: `/etc/traffic-guard.env`
- state file: `/var/lib/traffic-guard/state.json`

The installer creates:

- virtual environment in `/opt/traffic-guard/.venv`
- systemd unit in `/etc/systemd/system/traffic-guard.service`
- env template from [deploy/traffic-guard.env.example](C:/Users/user.LAPTOP-M7DTCFMM/Documents/New%20project/deploy/traffic-guard.env.example)

If you prefer a different layout, override these variables before running the installer:

```bash
sudo APP_DIR=/srv/traffic-guard ENV_TARGET=/etc/traffic-guard.env bash scripts/install.sh
```

## Operational Notes

- The service is intended for Linux VPS only.
- Threshold notifications are sent once per month per threshold.
- At the start of a new UTC month, the local counter resets automatically.
- If your provider counts traffic differently from interface counters, we can add provider API polling in the next step.
