# Deployment

This folder contains deployment helpers for the room monitor prototype.

## Firebase deployment

The Raspberry Pi writes to Firebase Realtime Database, and GitHub Pages reads
the public dashboard data.

### Firebase setup

1. Create a Firebase project.
2. Create a Realtime Database.
3. Enable Authentication with the Email/Password provider.
4. Add one device user, for example `room-device@example.com`.
5. Copy that user's UID.
6. In `firebase/database.rules.json`, replace
   `REPLACE_WITH_FIREBASE_DEVICE_UID` with the device UID.
7. Publish those rules in Firebase Realtime Database rules.
8. Create a Firebase Web App and copy its config into `web/firebase-config.js`.

The web config is not a server secret. Firebase access is controlled by
Realtime Database security rules. The device email/password is secret and should
only live on the Raspberry Pi in `/etc/room-monitor/firebase_collector.env`.

### Raspberry Pi service

On the Raspberry Pi:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv

sudo mkdir -p /opt
sudo git clone YOUR_REPO_URL /opt/stm32_raspberrypi_practice
cd /opt/stm32_raspberrypi_practice

sudo bash deploy/install_firebase_collector_service.sh
sudo nano /etc/room-monitor/firebase_collector.env
sudo systemctl restart room-monitor-firebase-collector.service
```

If the repo is under your home directory, such as
`/home/bill/Desktop/stm32_raspberrypi_practice`, pass that path with `REPO_DIR`.
The systemd service is allowed to read that path so Desktop-based checkouts work.
Keep the checkout owned by your normal user so `git pull` can update it. Only
`raspberry_pi/data` needs to be writable by the service user.

If you want to use Miniforge/conda instead of a project `.venv`, create or
activate the conda environment first, install with `PYTHON_BIN`, and keep using
the absolute Python path in systemd:

```bash
conda create -n room-monitor python=3.11 -y
conda activate room-monitor
which python

sudo REPO_DIR=/home/bill/Desktop/stm32_raspberrypi_practice \
  SERVICE_USER=bill \
  SERVICE_GROUP=bill \
  PYTHON_BIN=/home/bill/miniforge3/envs/room-monitor/bin/python \
  bash deploy/install_firebase_collector_service.sh
```

Use the path printed by `which python` for `PYTHON_BIN`.

Set these values:

```text
FIREBASE_DATABASE_URL=https://YOUR_PROJECT_ID-default-rtdb.firebaseio.com
FIREBASE_API_KEY=your-firebase-web-api-key
FIREBASE_DEVICE_EMAIL=room-device@example.com
FIREBASE_DEVICE_PASSWORD=your-device-password
FIREBASE_UPLOAD_EVERY_SECONDS=60
FIREBASE_RETENTION_DAYS=30
FIREBASE_PRUNE_EVERY_SECONDS=86400
FIREBASE_PRUNE_BATCH_SIZE=200
```

Firebase retention deletes old `/readings` rows from Realtime Database. `latest`
is kept so the dashboard always has the newest reading. At one upload per
minute, 30 days is about 43,200 history rows.

Check logs:

```bash
journalctl -u room-monitor-firebase-collector.service -f
```

### GitHub Pages

In GitHub repository settings, set Pages source to GitHub Actions. The included
`.github/workflows/deploy-pages.yml` workflow publishes the `web/` folder. Then
open the Pages URL on your phone. The dashboard reads:

```text
/latest
/readings
```

from Firebase Realtime Database.
