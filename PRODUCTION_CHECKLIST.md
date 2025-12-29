# Production Deployment Checklist

Use this checklist to ensure a smooth production deployment.

## Pre-Deployment

- [ ] **Dependencies Installed**
  ```bash
  source venv/bin/activate
  pip install -r requirements.txt
  ```

- [ ] **Configuration File Created**
  ```bash
  cp config/config.json.example config/config.json
  # Edit config/config.json with your settings
  ```

- [ ] **Configuration Validated**
  ```bash
  python3 -c "from src.core.config_validator import load_and_validate_config; load_and_validate_config('config/config.json'); print('✅ Valid')"
  ```

- [ ] **Device Connection Tested**
  ```bash
  python3 -m src.discover_device --scan --email YOUR_EMAIL --password YOUR_PASSWORD
  ```

- [ ] **Test Run Successful**
  ```bash
  python3 -m src.main
  # Verify: starts without errors, device connects, scheduler runs
  # Press Ctrl+C to stop
  ```

## Deployment

- [ ] **Install as Daemon**
  ```bash
  ./scripts/install_daemon.sh
  ```

- [ ] **Verify Service Started**
  ```bash
  launchctl list | grep com.hydro.controller
  # Should show service running
  ```

- [ ] **Check Initial Logs**
  ```bash
  tail -f logs/hydro_controller.log
  # Look for: "Hydroponic Controller Starting", "Connected successfully", "Scheduler started"
  ```

- [ ] **Verify Web UI (if enabled)**
  - Open http://localhost:8000 in browser
  - Check status page shows correct information
  - Test manual device control (ON/OFF)

- [ ] **Verify First Cycle**
  - Monitor logs for first cycle execution
  - Verify device turns on/off as expected
  - Check timing matches configuration

## Post-Deployment Verification

- [ ] **Service Running**
  - `launchctl list | grep com.hydro.controller` shows service
  - No errors in `logs/daemon.stderr.log`

- [ ] **Device Connected**
  - Logs show successful connection
  - Web UI shows device as connected
  - Device responds to commands

- [ ] **Scheduler Active**
  - Logs show scheduler started
  - Cycles executing according to schedule
  - Next event time displayed correctly

- [ ] **Logging Working**
  - Logs being written to `logs/hydro_controller.log`
  - Log rotation working (check for .log.1, .log.2 files after time)

- [ ] **Web UI Functional (if enabled)**
  - Accessible at http://localhost:8000
  - Status updates correctly
  - Manual controls work
  - Configuration can be viewed

## Monitoring (First 24 Hours)

- [ ] **Hour 1**: Verify service stability, check for immediate errors
- [ ] **Hour 6**: Verify cycles executing, check device state changes
- [ ] **Hour 12**: Review logs for any warnings, verify schedule adherence
- [ ] **Hour 24**: Full day cycle verification, check for any issues

## Troubleshooting Quick Reference

### Service Not Running
```bash
launchctl start com.hydro.controller
tail -f logs/daemon.stderr.log
```

### Device Connection Failed
```bash
# Test connection
python3 -m src.discover_device --ip DEVICE_IP --email EMAIL --password PASSWORD

# Check network
ping DEVICE_IP
```

### Configuration Error
```bash
# Validate config
python3 -c "from src.core.config_validator import load_and_validate_config; load_and_validate_config('config/config.json')"
```

### View Logs
```bash
# Application logs
tail -f logs/hydro_controller.log

# Daemon output
tail -f logs/daemon.stdout.log

# Daemon errors
tail -f logs/daemon.stderr.log
```

## Success Indicators

✅ **Deployment Successful When:**
- Service runs continuously
- Device connects reliably
- Scheduler executes cycles correctly
- Logs show normal operation
- Web UI functional (if enabled)
- No errors in daemon logs

## Next Steps After Deployment

1. **Monitor for 24-48 hours** to ensure stability
2. **Review logs** for any warnings or issues
3. **Adjust schedule** if needed based on plant/system needs
4. **Document** any custom configuration or adjustments
5. **Set up regular monitoring** (weekly log reviews)

## Emergency Procedures

### Stop Service Immediately
```bash
launchctl stop com.hydro.controller
```

### Manual Device Control
- Use Tapo app to control device directly
- Or use web UI if accessible
- Or use: `python3 -m src.test_on_off` (if script exists)

### Restart Service
```bash
launchctl stop com.hydro.controller
launchctl start com.hydro.controller
```

### Uninstall Service
```bash
./scripts/uninstall_daemon.sh
```

