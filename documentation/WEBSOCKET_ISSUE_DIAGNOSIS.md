# Odoo WebSocket Issue - Diagnosis & Fix Proposal

**Date:** 2025-11-19
**Environment:** Odoo 17.0 (odoo-dev-web container)
**Status:** ⚠️ Configuration Mismatch - Affecting Real-time Features

---

## 1. ISSUE SUMMARY

### Symptoms
Repeating RuntimeError in Odoo logs every ~30 seconds:

```
RuntimeError: Couldn't bind the websocket.
Is the connection opened on the evented port (8078)?

INFO testing werkzeug: GET /websocket?version=17.0-3 HTTP/1.1" 500
```

### Impact
- ⚠️ **WebSocket connections failing** (real-time features broken)
- ⚠️ **Live updates not working** (chat, notifications, dashboard updates)
- ✅ **Basic Odoo functionality works** (CRUD operations, reports, etc.)
- ⚠️ **User experience degraded** (no instant notifications)

---

## 2. ROOT CAUSE ANALYSIS

### The Configuration Mismatch

**Odoo Configuration (`/etc/odoo/odoo.conf`):**
```ini
longpolling_port = 8078
```

**Docker Port Mapping (odoo-dev-web container):**
```
8069/tcp → 0.0.0.0:8019  ✅ Main HTTP (working)
8072/tcp → 0.0.0.0:8020  ✅ Mapped but wrong port
8078/tcp → NOT MAPPED    ❌ Missing!
```

**The Problem:**
- Odoo **expects** websocket on port **8078** (per config)
- Docker **maps** only port **8072** → **8020**
- Port **8078** is **not exposed** to host
- Client tries to connect → **fails** → RuntimeError

### Standard Odoo 17 Configuration

**Default Gevent Port:** `8072` (standard for Odoo 16+)

**Deprecated vs Current:**
```ini
# ❌ DEPRECATED (shows warning):
longpolling_port = 8078

# ✅ CURRENT (Odoo 17):
gevent_port = 8072
```

---

## 3. WHY IT'S HAPPENING

### Configuration Inconsistency

1. **Odoo Config File** uses deprecated parameter:
   - `longpolling_port = 8078` (old syntax)
   - Should use: `gevent_port = 8072` (new syntax)

2. **Docker Compose/Run** expects standard port:
   - Maps `8072:8020` (standard Odoo setup)
   - Doesn't know about custom `8078` port

3. **Mismatch Result:**
   - Odoo binds websocket to `8078` inside container
   - Docker doesn't forward `8078` to host
   - External clients can't connect
   - Internal routing also broken

### The Deprecation Warning

You're also seeing this warning:
```
DeprecationWarning: The longpolling-port is a deprecated alias
to the gevent-port option, please use the latter.
```

**Why?**
- `longpolling_port` → Odoo 15 and earlier
- `gevent_port` → Odoo 16+
- Parameter renamed for clarity (WebSocket vs long-polling)

---

## 4. TECHNICAL DETAILS

### How Odoo WebSocket Works

**Normal Flow:**
```
1. User opens Odoo web interface
2. Browser connects to HTTP port (8069)
3. Browser requests WebSocket upgrade: GET /websocket
4. Odoo redirects to gevent port (8072 or 8078)
5. Persistent WebSocket connection established
6. Real-time notifications flow
```

**Current (Broken) Flow:**
```
1. User opens Odoo web interface ✅
2. Browser connects to HTTP port (8069) ✅
3. Browser requests: GET /websocket ✅
4. Odoo tries to connect to port 8078 ❌ (not mapped)
5. Connection fails → RuntimeError ❌
6. No real-time updates ❌
```

### What Features Are Affected

**Broken (Real-time features):**
- ❌ Live chat/messaging
- ❌ Instant notifications
- ❌ Dashboard real-time updates
- ❌ Multi-user collaboration indicators
- ❌ Live cursor tracking (in some views)

**Still Working (Regular features):**
- ✅ All CRUD operations
- ✅ Reports (PDF/XLSX)
- ✅ Form submissions
- ✅ Searches and filters
- ✅ Batch operations
- ✅ (You just won't see live updates)

---

## 5. PROPOSED SOLUTIONS

### ✅ Option 1: UPDATE CONFIG TO USE STANDARD PORT (RECOMMENDED)

**Description:** Change Odoo config to use standard `gevent_port = 8072`

**Why This Is Best:**
- Matches Docker port mapping (already configured)
- Uses current (non-deprecated) parameter
- Follows Odoo 17 best practices
- No Docker changes needed

**Configuration Change:**
```ini
# /etc/odoo/odoo.conf

# ❌ REMOVE THIS LINE:
longpolling_port = 8078

# ✅ ADD THIS LINE:
gevent_port = 8072

# Also ensure workers are enabled (required for websocket):
workers = 2
```

**How to Apply:**
```bash
# Edit config file
docker exec -it odoo-dev-web nano /etc/odoo/odoo.conf

# Or use sed to replace
docker exec odoo-dev-web sed -i 's/longpolling_port = 8078/gevent_port = 8072/' /etc/odoo/odoo.conf

# Restart container
docker restart odoo-dev-web
```

**Verification:**
```bash
# Wait 1 minute after restart
docker logs --since 1m odoo-dev-web 2>&1 | grep "websocket"
# Expected: No errors

# Test websocket connection
curl -i http://localhost:8020/websocket
# Expected: 101 Switching Protocols (or Connection upgrade)
```

**Pros:**
- ✅ Simplest solution
- ✅ No Docker Compose changes
- ✅ Follows Odoo 17 standards
- ✅ Eliminates deprecation warning

**Cons:**
- None (this is the correct configuration)

---

### Option 2: ADD PORT 8078 TO DOCKER MAPPING

**Description:** Keep current config, add `8078` port to Docker

**Why Not Recommended:**
- Uses deprecated parameter
- Non-standard port (confusing)
- Requires Docker Compose changes
- Will keep showing deprecation warning

**Configuration Change:**
```yaml
# docker-compose.yml
ports:
  - "8019:8069"   # HTTP
  - "8020:8072"   # Gevent (standard)
  - "8021:8078"   # Custom longpolling (non-standard)
```

**Not Recommended:** Better to use standard configuration

---

### Option 3: DISABLE WEBSOCKET/LONGPOLLING

**Description:** Disable real-time features entirely

**Configuration Change:**
```ini
# /etc/odoo/odoo.conf
gevent_port = False
# or
# longpolling_port = False
```

**Pros:**
- ✅ Eliminates errors
- ✅ Simple config change

**Cons:**
- ❌ Loses real-time features
- ❌ Degraded user experience
- ❌ Not necessary (Option 1 is better)

**Not Recommended:** Unless you don't need real-time features

---

## 6. RECOMMENDED IMPLEMENTATION

### Step-by-Step Fix (Option 1)

**Step 1: Backup Current Config**
```bash
docker exec odoo-dev-web cp /etc/odoo/odoo.conf /etc/odoo/odoo.conf.bak
```

**Step 2: Update Configuration**
```bash
docker exec odoo-dev-web bash -c 'cat >> /tmp/fix_config.sh << "EOF"
#!/bin/bash
# Fix websocket configuration

CONFIG_FILE="/etc/odoo/odoo.conf"

# Replace deprecated longpolling_port with gevent_port
sed -i "s/longpolling_port = 8078/gevent_port = 8072/" "$CONFIG_FILE"

# Ensure workers are set (required for websocket)
if ! grep -q "^workers = " "$CONFIG_FILE"; then
    echo "workers = 2" >> "$CONFIG_FILE"
fi

echo "Configuration updated!"
cat "$CONFIG_FILE" | grep -E "gevent_port|workers"
EOF
chmod +x /tmp/fix_config.sh
/tmp/fix_config.sh'
```

**Step 3: Verify Configuration**
```bash
docker exec odoo-dev-web cat /etc/odoo/odoo.conf | grep -E "gevent_port|workers|longpolling"
# Expected:
#   gevent_port = 8072
#   workers = 2
#   (no longpolling_port line)
```

**Step 4: Restart Odoo**
```bash
docker restart odoo-dev-web
```

**Step 5: Wait for Startup (30 seconds)**
```bash
sleep 30
docker logs --since 1m odoo-dev-web 2>&1 | tail -20
```

**Step 6: Verify WebSocket Works**
```bash
# Check for websocket errors
docker logs --since 2m odoo-dev-web 2>&1 | grep -i "websocket.*error\|RuntimeError.*8078"
# Expected: (no output)

# Check if gevent port is listening
docker exec odoo-dev-web netstat -tlnp 2>/dev/null | grep 8072 || \
docker exec odoo-dev-web ss -tlnp 2>/dev/null | grep 8072
# Expected: tcp LISTEN 0.0.0.0:8072
```

**Step 7: Test from Browser**
1. Open Odoo web interface: http://dev.ueipab.edu.ve:8019
2. Open browser DevTools → Network tab
3. Filter: "websocket"
4. Refresh page
5. Should see: `websocket` connection with status `101 Switching Protocols`

---

## 7. VERIFICATION & TESTING

### Pre-Fix Verification
```bash
# Count websocket errors (before fix)
docker logs --since 1h odoo-dev-web 2>&1 | grep "RuntimeError.*websocket" | wc -l
# Expected: ~120 (one every ~30 seconds)

# Verify current config
docker exec odoo-dev-web grep "longpolling_port\|gevent_port" /etc/odoo/odoo.conf
# Expected: longpolling_port = 8078
```

### Post-Fix Verification
```bash
# Wait 3 minutes after restart
sleep 180

# Check for errors (should be none)
docker logs --since 3m odoo-dev-web 2>&1 | grep -i "websocket.*error\|RuntimeError"
# Expected: (no output)

# Verify gevent port is correct
docker exec odoo-dev-web grep "gevent_port" /etc/odoo/odoo.conf
# Expected: gevent_port = 8072

# Test websocket endpoint
curl -I http://localhost:8020/websocket
# Expected: HTTP 101 or appropriate WebSocket response
```

### Rollback (if needed)
```bash
# Restore backup
docker exec odoo-dev-web cp /etc/odoo/odoo.conf.bak /etc/odoo/odoo.conf

# Restart
docker restart odoo-dev-web
```

---

## 8. ADDITIONAL CONSIDERATIONS

### Worker Configuration

**Important:** WebSocket/gevent requires workers > 0

```ini
# /etc/odoo/odoo.conf
workers = 2  # or more
```

**Why?**
- Workers = 0 → Single-process mode (no gevent support)
- Workers > 0 → Multi-process mode (gevent enabled)

**Check Current Workers:**
```bash
docker exec odoo-dev-web grep "^workers" /etc/odoo/odoo.conf
```

If not set or = 0, add/change to 2.

### Proxy/Nginx Configuration

If you're using nginx/reverse proxy (likely for dev.ueipab.edu.ve):

**Current `/websocket` routing must be updated:**
```nginx
# nginx.conf
location /websocket {
    proxy_pass http://localhost:8020;  # ← Update to match Docker port
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
}

location / {
    proxy_pass http://localhost:8019;  # ← Main Odoo
}
```

**Note:** Ensure nginx routes `/websocket` to port `8020` (which maps to container port `8072`)

---

## 9. RELATED TO EMPTY DATABASE ISSUE

### Combined Fix Approach

Since we're restarting Odoo anyway, we can fix both issues together:

**Fix Order:**
1. Drop empty `ueipab` database (eliminates cron errors)
2. Update Odoo config (fixes websocket)
3. Restart container once (applies both fixes)

**Time Savings:** One restart instead of two

---

## 10. RISKS & MITIGATION

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Config syntax error** | Low | High | Backup config first; verify syntax |
| **Workers break something** | Very Low | Medium | Already have workers (check logs) |
| **WebSocket still broken** | Low | Medium | Check nginx config, Docker ports |
| **Odoo won't start** | Very Low | Critical | Restore from backup config |

---

## 11. DECISION REQUIRED

**Can I proceed with Option 1 (Update Config)?**

**The Fix:**
1. Change `longpolling_port = 8078` → `gevent_port = 8072`
2. Ensure `workers = 2` is set
3. Restart Odoo
4. Verify websocket works

**Combined with Database Fix:**
- Drop `ueipab` database (separate issue)
- Update config (this issue)
- Single restart (efficient)

**Time:** 10 minutes total
**Risk:** Very Low (config change + empty database removal)

---

## APPENDIX A: DIAGNOSTIC COMMANDS

```bash
# Check current websocket config
docker exec odoo-dev-web grep -E "gevent|longpolling|workers" /etc/odoo/odoo.conf

# Monitor websocket errors in real-time
docker logs -f odoo-dev-web 2>&1 | grep --line-buffered "websocket"

# Check what ports Odoo is listening on
docker exec odoo-dev-web ss -tlnp | grep python

# Test websocket from inside container
docker exec odoo-dev-web curl -I http://localhost:8072/websocket
docker exec odoo-dev-web curl -I http://localhost:8078/websocket

# Check Docker port mappings
docker port odoo-dev-web
```

---

## APPENDIX B: ODOO 17 WEBSOCKET BEST PRACTICES

**Recommended Configuration:**
```ini
# /etc/odoo/odoo.conf

# HTTP server
http_port = 8069

# WebSocket/Gevent server
gevent_port = 8072

# Workers (required for websocket)
workers = 2

# Database filter
dbfilter = ^(testing)$

# Other settings...
```

**Docker Port Mapping:**
```yaml
# docker-compose.yml
ports:
  - "8019:8069"  # HTTP → External 8019
  - "8020:8072"  # WebSocket → External 8020
```

**Nginx Configuration:**
```nginx
upstream odoo {
    server 127.0.0.1:8019;
}

upstream odoo_websocket {
    server 127.0.0.1:8020;
}

server {
    location /websocket {
        proxy_pass http://odoo_websocket;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location / {
        proxy_pass http://odoo;
    }
}
```

---

**Status:** 📋 Awaiting Decision - Ready to Implement Fix
**Recommendation:** Option 1 - Update Config to gevent_port = 8072
**Combined With:** Empty Database Fix (separate issue)
**Estimated Time:** 10 minutes total
**Risk Level:** Very Low
