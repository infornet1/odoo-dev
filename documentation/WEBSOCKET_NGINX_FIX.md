# WebSocket and Nginx Configuration Fix for Odoo 17

**Status:** Production | **Fixed:** 2026-01-27

## Issue Description

Users experienced "connection lost" errors when editing email campaigns in Odoo 17's Email Marketing module. The issue manifested as:
- Unable to edit email campaign content
- Frequent disconnections in the email editor
- "Request body too large" errors when saving campaigns

## Root Causes

### 1. WebSocket Port Mismatch
- **Problem:** Odoo config had `longpolling_port = 8078` but Docker mapped host:8078 to container:8072
- **Result:** WebSocket connections failed with HTTP 502 errors

### 2. Missing Origin Header in Nginx
- **Problem:** Odoo 17 WebSocket requires the `Origin` header for security validation
- **Result:** Connections rejected with HTTP 400 "Empty or missing header(s): origin"

### 3. Missing Upload Size Limit
- **Problem:** Default nginx `client_max_body_size` is 1MB
- **Result:** Email campaigns with images (1.6MB+) failed to save

## Fixes Applied

### 1. Odoo Configuration
**File:** `/home/vision/ueipab17/config/odoo.conf`

```ini
# Changed from:
longpolling_port = 8078

# To:
gevent_port = 8072
```

This aligns with Docker port mapping: host:8078 -> container:8072

### 2. Nginx Configuration
**File:** `/etc/nginx/sites-available/odoo.ueipab.edu.ve`

Added WebSocket map at the top:
```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    ''  close;
}
```

Added WebSocket location block (in both server blocks):
```nginx
location /websocket {
    proxy_pass http://odoo17chat;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    proxy_set_header Host $host;
    proxy_set_header Origin $http_origin;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_read_timeout 604800;
    proxy_send_timeout 604800;
}
```

Added upload size limit:
```nginx
client_max_body_size 50m;
```

### 3. Services Restarted
```bash
# Restart Odoo container
docker restart ueipab17

# Reload nginx
systemctl reload nginx
```

## Verification

Test WebSocket connection:
```bash
curl --http1.1 --max-time 5 -k \
  -H 'Connection: Upgrade' \
  -H 'Upgrade: websocket' \
  -H 'Sec-WebSocket-Version: 13' \
  -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' \
  -H 'Origin: https://odoo.ueipab.edu.ve' \
  'https://odoo.ueipab.edu.ve/websocket?version=17.0-1' \
  -o /dev/null -w 'HTTP Code: %{http_code}\n'
```

Expected output: `HTTP Code: 101` (Switching Protocols)

## Backup Files Created

- `/etc/nginx/sites-available/odoo.ueipab.edu.ve.bak.20260127_083923`
- `/home/vision/ueipab17/config/odoo.conf.bak.20260127_084222`

## Testing Environment

The testing environment (`dev.ueipab.edu.ve`) already has:
- Correct `gevent_port = 8072` in Odoo config
- WebSocket location configured in nginx

However, it may need:
- `Origin` header pass-through if WebSocket issues occur
- `client_max_body_size` increase if large file uploads fail

## Related Odoo 17 Information

- Odoo 17 uses `/websocket` endpoint (changed from `/longpolling` in earlier versions)
- WebSocket requires HTTP/1.1 (not HTTP/2) for upgrade handshake
- The gevent worker handles both `/websocket` and `/longpolling` endpoints
- Default gevent port is 8072
