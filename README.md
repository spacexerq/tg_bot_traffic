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
- doctor command for first launch validation
- interface diagnostics
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
- Python 3.10+
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

Run diagnostics:

```bash
traffic-guard show-interfaces
traffic-guard doctor
traffic-guard doctor --send-test-message
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
sudo /opt/traffic-guard/.venv/bin/traffic-guard --env-file /etc/traffic-guard.env doctor
sudo /opt/traffic-guard/.venv/bin/traffic-guard --env-file /etc/traffic-guard.env doctor --send-test-message
sudo systemctl start traffic-guard
sudo systemctl status traffic-guard
sudo journalctl -u traffic-guard -f
```

If the selected interfaces look wrong, inspect them first:

```bash
sudo /opt/traffic-guard/.venv/bin/traffic-guard --env-file /etc/traffic-guard.env show-interfaces
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

1. Open Telegram and start a chat with `@BotFather`.
2. Run `/newbot`.
3. Give the bot a display name.
4. Give the bot a unique username ending with `bot`.
5. Copy the bot token and put it into `TG_BOT_TOKEN`.
6. Decide where alerts should arrive:
7. For private alerts: open a direct chat with your bot and press `Start`.
8. For group alerts: create a group, add the bot, and allow it to post messages.
9. Send at least one message in that chat so the bot has a dialog context.
10. Obtain the numeric chat id.

Private chat id is usually your user id or a positive chat id.
Group chat id is usually negative.

One practical way to get the chat id:

```bash
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates"
```

Then find `chat.id` in the JSON response and copy it into `TG_CHAT_ID`.

After filling `/etc/traffic-guard.env`, run:

```bash
sudo /opt/traffic-guard/.venv/bin/traffic-guard --env-file /etc/traffic-guard.env doctor --send-test-message
```

If the message arrives in Telegram, the bot side is configured correctly.

## Deployment With systemd

The example unit is in [deploy/systemd/traffic-guard.service](C:/Users/user.LAPTOP-M7DTCFMM/Documents/New%20project/deploy/systemd/traffic-guard.service).

Suggested layout on a server:

- app directory: `/opt/traffic-guard`
- env file: `/etc/traffic-guard.env`
- state file: `/var/lib/traffic-guard/state.json`

The installer creates:

- virtual environment in `/opt/traffic-guard/.venv`
- systemd unit in `/etc/systemd/system/traffic-guard.service`
- profile template unit in [deploy/systemd/traffic-guard@.service](C:/Users/user.LAPTOP-M7DTCFMM/Documents/New%20project/deploy/systemd/traffic-guard@.service)
- env template from [deploy/traffic-guard.env.example](C:/Users/user.LAPTOP-M7DTCFMM/Documents/New%20project/deploy/traffic-guard.env.example)

If you prefer a different layout, override these variables before running the installer:

```bash
sudo APP_DIR=/srv/traffic-guard ENV_TARGET=/etc/traffic-guard.env bash scripts/install.sh
```

## Multiple Profiles On One Host

If one host needs more than one independent profile, first run the base installer, then create a profile:

```bash
sudo bash scripts/install-profile.sh backup-node
sudo nano /etc/traffic-guard/backup-node.env
sudo systemctl start traffic-guard@backup-node
```

This creates:

- profile env: `/etc/traffic-guard/backup-node.env`
- profile state: `/var/lib/traffic-guard/backup-node/state.json`
- service name: `traffic-guard@backup-node`

This is useful if one host should notify to different chats, use different thresholds, or track different interfaces.

## First Launch Checklist

1. Install the project with `scripts/install.sh`.
2. Fill `/etc/traffic-guard.env`.
3. Run `doctor` without Telegram sending.
4. Run `doctor --send-test-message`.
5. Confirm the message arrived in Telegram.
6. Start `traffic-guard` via `systemctl`.
7. Watch logs with `journalctl -u traffic-guard -f`.

## Operational Notes

- The service is intended for Linux VPS only.
- Threshold notifications are sent once per month per threshold.
- At the start of a new UTC month, the local counter resets automatically.
- If your provider counts traffic differently from interface counters, we can add provider API polling in the next step.
