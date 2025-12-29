# Production Deployment Guide

This guide covers deploying the refactored Hydroponic Controller to production.

## Pre-Deployment Checklist

### ✅ Prerequisites Verified
- [x] All dependencies installed (`pip install -r requirements.txt`)
- [x] Configuration file created and validated
- [x] Device credentials configured
- [x] Network connectivity verified
- [x] Tests passing (core functionality verified)
- [x] Documentation complete

### Configuration Verification

1. **Verify configuration file exists:**
   ```bash
   ls -la config/config.json
   ```

2. **Validate configuration:**
   ```bash
   python3 -c "from src.core.config_validator import load_and_validate_config; load_and_validate_config('config/config.json'); print('✅ Configuration valid')"
   ```

3. **Test device connection:**
   ```bash
   python3 -m src.discover_device --scan --email YOUR_EMAIL --password YOUR_PASSWORD
   ```

## Deployment Steps

### Step 1: Install Dependencies

```bash
# Activate virtual environment
source venv/bin/activate

# Install/upgrade all dependencies
pip install -r requirements.txt --upgrade

# Verify installation
python3 -c "import pydantic, fastapi, plugp100; print('✅ All dependencies installed')"
```

### Step 2: Configure Application

1. **Copy example configuration:**
   ```bash
   cp config/config.json.example config/config.json
   ```

2. **Edit configuration:**
   ```bash
   # Edit with your preferred editor
   nano config/config.json
   # or
   vim config/config.json
   ```

3. **Required configuration:**
   - Device IP address, email, and password
   - Primary device ID matching device configuration
   - Schedule type and parameters
   - Logging configuration

4. **Validate configuration:**
   ```bash
   python3 -c "from src.core.config_validator import load_and_validate_config; load_and_validate_config('config/config.json'); print('✅ Configuration valid')"
   ```

### Step 3: Test Run

Before deploying as a service, test the application:

```bash
# Activate virtual environment
source venv/bin/activate

# Run application (will run until Ctrl+C)
python3 -m src.main

# Or with custom config
python3 -m src.main --config /path/to/config.json
```

**Verify:**
- Application starts without errors
- Device connects successfully
- Scheduler starts and runs
- Web UI accessible (if enabled)
- Logs are being written

### Step 4: Deploy as Daemon (macOS)

#### Option A: Using Provided Script (Recommended)

```bash
# Install as launchd daemon
./scripts/install_daemon.sh
```

This will:
- Create launchd plist file
- Install as user daemon
- Start the service automatically
- Configure auto-restart on crash
- Set up logging

#### Option B: Manual Installation

1. **Create plist file** at `~/Library/LaunchAgents/com.hydro.controller.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.hydro.controller</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/YOUR_USERNAME/Projects/active/experimental/hydro_automation/venv/bin/python3</string>
        <string>-m</string>
        <string>src.main</string>
        <string>--config</string>
        <string>/Users/YOUR_USERNAME/Projects/active/experimental/hydro_automation/config/config.json</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/YOUR_USERNAME/Projects/active/experimental/hydro_automation</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/YOUR_USERNAME/Projects/active/experimental/hydro_automation/logs/daemon.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/YOUR_USERNAME/Projects/active/experimental/hydro_automation/logs/daemon.stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
```

2. **Load and start:**
   ```bash
   launchctl load ~/Library/LaunchAgents/com.hydro.controller.plist
   launchctl start com.hydro.controller
   ```

### Step 5: Verify Deployment

1. **Check service status:**
   ```bash
   launchctl list | grep com.hydro.controller
   ```

2. **Check logs:**
   ```bash
   # Application logs
   tail -f logs/hydro_controller.log
   
   # Daemon stdout
   tail -f logs/daemon.stdout.log
   
   # Daemon stderr
   tail -f logs/daemon.stderr.log
   ```

3. **Verify scheduler is running:**
   - Check logs for "Scheduler started" message
   - Verify device state changes in logs
   - Check web UI (if enabled) at http://localhost:8000

4. **Test device control:**
   - Use web UI to manually turn device on/off
   - Verify device responds correctly

## Production Configuration Recommendations

### Logging

```json
{
  "logging": {
    "log_file": "logs/hydro_controller.log",
    "log_level": "INFO"
  }
}
```

**Recommendations:**
- Use `INFO` level for production (less verbose than DEBUG)
- Monitor log file size (automatic rotation configured)
- Review logs regularly for errors

### Web UI

```json
{
  "web": {
    "enabled": true,
    "host": "0.0.0.0",
    "port": 8000
  }
}
```

**Security Considerations:**
- Web UI is accessible on local network only
- No authentication (assumes secure local network)
- For remote access, use VPN or SSH tunnel
- Consider firewall rules if needed

### Schedule Configuration

**For Production Use:**
- Start with conservative timing (longer intervals)
- Monitor system behavior for first few days
- Adjust based on plant needs and system performance
- Use adaptive scheduling for automatic optimization

### Device Configuration

```json
{
  "devices": {
    "devices": [{
      "device_id": "pump1",
      "name": "Main Pump",
      "brand": "tapo",
      "type": "power_controller",
      "ip_address": "192.168.1.XXX",
      "email": "your_email@example.com",
      "password": "your_password",
      "auto_discovery": true
    }]
  }
}
```

**Recommendations:**
- Enable `auto_discovery` for resilience to IP changes
- Consider static IP assignment on router for reliability
- Keep credentials secure (never commit to git)

## Monitoring and Maintenance

### Daily Checks

1. **Check service status:**
   ```bash
   launchctl list | grep com.hydro.controller
   ```

2. **Review recent logs:**
   ```bash
   tail -50 logs/hydro_controller.log
   ```

3. **Verify device connectivity:**
   - Check web UI device status
   - Verify recent cycle events in logs

### Weekly Maintenance

1. **Review log files:**
   - Check for errors or warnings
   - Verify schedule execution
   - Review device connection stability

2. **Check disk space:**
   ```bash
   du -sh logs/
   ```

3. **Verify configuration:**
   - Ensure configuration is still valid
   - Check for any needed adjustments

### Troubleshooting

#### Service Not Running

```bash
# Check status
launchctl list | grep com.hydro.controller

# Check logs
tail -f logs/daemon.stderr.log

# Restart service
launchctl stop com.hydro.controller
launchctl start com.hydro.controller
```

#### Device Connection Issues

1. **Verify device is online:**
   - Check Tapo app
   - Ping device IP address

2. **Test connection:**
   ```bash
   python3 -m src.discover_device --ip DEVICE_IP --email EMAIL --password PASSWORD
   ```

3. **Check network:**
   - Ensure device and Mac on same network
   - Check router/firewall settings

#### Configuration Errors

1. **Validate configuration:**
   ```bash
   python3 -c "from src.core.config_validator import load_and_validate_config; load_and_validate_config('config/config.json')"
   ```

2. **Check for common issues:**
   - JSON syntax errors
   - Missing required fields
   - Invalid device IDs
   - Invalid time formats

#### Scheduler Not Running

1. **Check logs for errors:**
   ```bash
   grep -i error logs/hydro_controller.log | tail -20
   ```

2. **Verify scheduler configuration:**
   - Check schedule type is valid
   - Verify cycle definitions
   - Check adaptation settings (if using adaptive)

## Rollback Procedure

If issues occur, you can rollback:

1. **Stop service:**
   ```bash
   launchctl stop com.hydro.controller
   ```

2. **Unload daemon:**
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.hydro.controller.plist
   ```

3. **Restore previous version:**
   ```bash
   git checkout PREVIOUS_COMMIT
   ```

4. **Reinstall:**
   ```bash
   pip install -r requirements.txt
   ./scripts/install_daemon.sh
   ```

## Post-Deployment Verification

After deployment, verify:

- [ ] Service is running (`launchctl list | grep com.hydro.controller`)
- [ ] No errors in logs (`tail logs/hydro_controller.log`)
- [ ] Device connects successfully (check logs)
- [ ] Scheduler starts and runs (check logs for cycle events)
- [ ] Web UI accessible (if enabled) at http://localhost:8000
- [ ] Device responds to manual control (web UI)
- [ ] First cycle executes correctly (monitor logs)
- [ ] Log rotation working (check for rotated log files)

## Production Best Practices

1. **Backup Configuration:**
   - Keep backup of working `config.json`
   - Version control configuration (without credentials)
   - Document any custom settings

2. **Monitor Regularly:**
   - Check logs daily
   - Monitor device state
   - Verify cycle execution

3. **Keep Updated:**
   - Monitor for dependency updates
   - Review security advisories
   - Test updates in development first

4. **Document Changes:**
   - Keep notes on configuration changes
   - Document any issues and resolutions
   - Track schedule adjustments

5. **Safety:**
   - Always verify device state before leaving unattended
   - Test emergency stop functionality
   - Have manual override capability (web UI or Tapo app)

## Support and Troubleshooting

For issues:
1. Check logs first (`logs/hydro_controller.log`)
2. Review this deployment guide
3. Check `docs/` directory for detailed documentation
4. Review `REFACTOR_STATUS.md` for current status

## Success Criteria

Production deployment is successful when:
- ✅ Service runs continuously without crashes
- ✅ Device connects reliably
- ✅ Scheduler executes cycles as configured
- ✅ Web UI accessible and functional
- ✅ Logs show normal operation
- ✅ No errors in daemon logs

