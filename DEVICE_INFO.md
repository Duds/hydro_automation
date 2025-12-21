# Tapo P100 Device Information

## Device Details

- **Model**: Tapo P100
- **MAC Address**: `CC-BA-BD-DB-49-D4`
- **Current IP**: `192.168.0.126` (may change if not set as static)
- **Firmware**: 1.2.5 Build 240411
- **Hardware Version**: 2.0
- **Device ID**: 80220074916899E92FA1D5869F754C0824B1FB44
- **Nickname**: hydroponic flood and drain table

## Setting Static IP Reservation

To prevent IP address changes, configure your router to reserve a static IP for this device:

1. Log into your router admin panel (usually `http://192.168.0.1`)
2. Navigate to DHCP/Network Settings
3. Find "DHCP Reservation" or "Static IP" option
4. Add reservation:
   - **MAC Address**: `CC-BA-BD-DB-49-D4` ⚠️ **Use this - it's the identifier you need**
   - **IP Address**: `192.168.0.126` (or your preferred IP)
   - **Hostname/Description**: `Tapo-P100` or `hydroponic flood and drain table` (optional, for reference only)
   - **Device Name**: Tapo P100 - Hydroponic Controller (optional description)

**Note**: Most routers require the MAC address for static IP reservations. The hostname is usually just for identification in the router's device list.

## Auto-Discovery

If static IP is not configured, the controller will automatically discover the device on the network if the IP address changes. This is enabled by default in `config.json`.

## Current Configuration

Your device is configured in `config/config.json` with:
- IP: 192.168.0.126
- Auto-discovery: Enabled

