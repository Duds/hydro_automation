# Quick Production Deployment Guide

## ⚡ Fast Track to Production

### Step 1: Update Configuration (2 minutes)

Your current `config/config.json` uses the old format. Update it to the new format:

```bash
# Backup current config
cp config/config.json config/config.json.backup

# Copy example (new format)
cp config/config.json.example config/config.json

# Edit with your device details
nano config/config.json
# or
open -e config/config.json
```

**Required changes in config/config.json:**
1. Update `devices.devices[0]` with your device:
   - `device_id`: "pump1" (or your preferred ID)
   - `ip_address`: Your device IP
   - `email`: Your Tapo email
   - `password`: Your Tapo password

2. Ensure `growing_system.primary_device_id` matches your `device_id`

3. Configure your schedule (interval, time_based, or adaptive)

### Step 2: Validate Configuration (30 seconds)

```bash
source venv/bin/activate
python3 -c "from src.core.config_validator import load_and_validate_config; load_and_validate_config('config/config.json'); print('✅ Configuration valid')"
```

### Step 3: Test Run (2 minutes)

```bash
# Test the application
python3 -m src.main
```

**Verify:**
- ✅ Application starts without errors
- ✅ Device connects successfully
- ✅ Scheduler starts
- ✅ Web UI accessible (if enabled)

Press `Ctrl+C` to stop when satisfied.

### Step 4: Deploy as Daemon (1 minute)

```bash
# Install and start as background service
./scripts/install_daemon.sh
```

### Step 5: Verify Deployment (1 minute)

```bash
# Check service is running
launchctl list | grep com.hydro.controller

# Check logs
tail -f logs/hydro_controller.log
```

**Look for:**
- "Hydroponic Controller Starting"
- "Connected successfully"
- "Scheduler started"
- No errors

### Step 6: Monitor First Cycle (5-10 minutes)

Watch the logs to verify the first cycle executes:

```bash
tail -f logs/hydro_controller.log
```

**Expected:**
- Device turns ON at scheduled time
- Device turns OFF after flood duration
- Next cycle scheduled correctly

## ✅ Production Deployment Complete!

Your application is now running in production as a background daemon.

## Quick Reference Commands

```bash
# Check status
launchctl list | grep com.hydro.controller

# View logs
tail -f logs/hydro_controller.log

# Stop service
launchctl stop com.hydro.controller

# Start service
launchctl start com.hydro.controller

# Restart service
launchctl stop com.hydro.controller && launchctl start com.hydro.controller

# Uninstall daemon
./scripts/uninstall_daemon.sh
```

## Troubleshooting

**Service not starting?**
```bash
tail -f logs/daemon.stderr.log
```

**Configuration error?**
```bash
python3 -c "from src.core.config_validator import load_and_validate_config; load_and_validate_config('config/config.json')"
```

**Device connection issue?**
```bash
python3 -m src.discover_device --scan --email YOUR_EMAIL --password YOUR_PASSWORD
```

## Need Help?

- See `docs/PRODUCTION_DEPLOYMENT.md` for detailed guide
- See `PRODUCTION_CHECKLIST.md` for deployment checklist
- See `docs/MIGRATION.md` for configuration migration help

