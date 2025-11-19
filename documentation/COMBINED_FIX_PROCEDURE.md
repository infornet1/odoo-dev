# Combined Fix Procedure: Empty Database + WebSocket Issues

**Date:** 2025-11-19
**Environment:** Odoo 17.0 (odoo-dev-web container)
**Issues:** 2 Known Problems
**Estimated Time:** 10 minutes
**Risk Level:** Very Low

---

## ISSUES SUMMARY

### Issue #1: Empty "ueipab" Database
**Symptom:** Repeating ERROR every ~60 seconds
```
ERROR ueipab odoo.sql_db: relation "ir_module_module" does not exist
```
**Impact:** Log pollution (~60 errors/hour)
**Fix:** Drop empty database

### Issue #2: WebSocket Port Mismatch
**Symptom:** Repeating RuntimeError every ~30 seconds
```
RuntimeError: Couldn't bind the websocket. Is the connection opened on the evented port (8078)?
```
**Impact:** Real-time features broken (chat, notifications)
**Fix:** Update config to use standard port 8072

---

## COMBINED FIX STRATEGY

**Why Fix Together:**
- Both require container restart
- One restart instead of two
- More efficient
- Cleaner result

**Fix Order:**
1. Drop empty database (PostgreSQL)
2. Update Odoo config (websocket)
3. Restart container (applies both)
4. Verify both fixes

---

## DETAILED FIX PROCEDURE

### STEP 1: BACKUP CURRENT STATE

```bash
# Backup Odoo configuration
docker exec odoo-dev-web cp /etc/odoo/odoo.conf /etc/odoo/odoo.conf.bak.20251119

# Verify backup
docker exec odoo-dev-web ls -lh /etc/odoo/*.bak*
```

---

### STEP 2: DROP EMPTY DATABASE

**Connect to PostgreSQL container:**
```bash
docker exec -it ueipab17_postgres_1 psql -U odoo
```

**Execute SQL commands:**
```sql
-- List databases (verify 'ueipab' exists)
\l

-- Terminate any connections to ueipab database
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'ueipab' AND pid <> pg_backend_pid();

-- Drop the database
DROP DATABASE ueipab;

-- Verify it's gone
\l

-- Exit
\q
```

**Expected Output:**
```
DROP DATABASE
```

**Alternative (One-line command):**
```bash
docker exec -i ueipab17_postgres_1 psql -U odoo << 'EOF'
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'ueipab' AND pid <> pg_backend_pid();

DROP DATABASE ueipab;

\l
EOF
```

---

### STEP 3: UPDATE ODOO CONFIGURATION

**Method A: Interactive Editing**
```bash
docker exec -it odoo-dev-web nano /etc/odoo/odoo.conf
```

**Changes to make:**
```ini
# FIND THIS LINE:
longpolling_port = 8078

# REPLACE WITH:
gevent_port = 8072

# ALSO VERIFY this line exists (add if missing):
workers = 2
```

Save (Ctrl+O, Enter) and Exit (Ctrl+X)

---

**Method B: Automated (Safer)**
```bash
docker exec odoo-dev-web bash << 'EOF'
CONFIG="/etc/odoo/odoo.conf"

# Replace longpolling_port with gevent_port
sed -i 's/longpolling_port = 8078/gevent_port = 8072/' "$CONFIG"

# Ensure workers are set
if ! grep -q "^workers = " "$CONFIG"; then
    echo "workers = 2" >> "$CONFIG"
fi

echo "===== Configuration Updated ====="
grep -E "gevent_port|workers" "$CONFIG"
EOF
```

**Expected Output:**
```
===== Configuration Updated =====
gevent_port = 8072
workers = 2
```

---

### STEP 4: VERIFY CONFIGURATION

```bash
docker exec odoo-dev-web cat /etc/odoo/odoo.conf | grep -E "gevent_port|workers|longpolling|dbfilter"
```

**Expected Output:**
```ini
dbfilter = ^(DB_UEIPAB|testing)$
gevent_port = 8072
workers = 2
```

**Should NOT see:**
```
longpolling_port = 8078  ← Should be gone
```

---

### STEP 5: RESTART ODOO CONTAINER

```bash
docker restart odoo-dev-web
```

**Wait for startup (30 seconds):**
```bash
echo "Waiting for Odoo to start..."
sleep 30
```

---

### STEP 6: VERIFY FIX #1 (Empty Database)

**Check for ueipab errors:**
```bash
docker logs --since 2m odoo-dev-web 2>&1 | grep "ueipab odoo.sql_db"
```

**Expected:** (no output - errors stopped)

**If you see errors:** Database wasn't dropped or restart didn't work

---

### STEP 7: VERIFY FIX #2 (WebSocket)

**Check for websocket errors:**
```bash
docker logs --since 2m odoo-dev-web 2>&1 | grep "RuntimeError.*websocket"
```

**Expected:** (no output - errors stopped)

**Check for deprecation warning:**
```bash
docker logs --since 2m odoo-dev-web 2>&1 | grep "longpolling-port.*deprecated"
```

**Expected:** (no output - warning gone)

---

### STEP 8: FUNCTIONAL TESTING

**Test Database Access:**
```bash
docker exec -i odoo-dev-web odoo shell -d testing --no-http << 'EOF'
print("✅ Testing database works:", env.uid)
EOF
```

**Expected:** `✅ Testing database works: 1`

**Test WebSocket Port:**
```bash
curl -I http://localhost:8020/websocket 2>&1 | head -5
```

**Expected:** Should see HTTP response (not connection refused)

**Browser Test:**
1. Open: http://dev.ueipab.edu.ve:8019
2. Open DevTools → Network tab
3. Filter: "websocket" or "ws"
4. Refresh page
5. **Expected:** See websocket connection with status `101 Switching Protocols`

---

## VERIFICATION CHECKLIST

### Pre-Fix State (Document for comparison)
```bash
echo "=== PRE-FIX STATE ===" > /tmp/pre_fix_state.txt

# Count ueipab errors
echo "ueipab errors (last hour):" >> /tmp/pre_fix_state.txt
docker logs --since 1h odoo-dev-web 2>&1 | grep "ueipab odoo.sql_db" | wc -l >> /tmp/pre_fix_state.txt

# Count websocket errors
echo "websocket errors (last hour):" >> /tmp/pre_fix_state.txt
docker logs --since 1h odoo-dev-web 2>&1 | grep "RuntimeError.*websocket" | wc -l >> /tmp/pre_fix_state.txt

cat /tmp/pre_fix_state.txt
```

### Post-Fix Verification (After 5 minutes)
```bash
echo "=== POST-FIX STATE ===" > /tmp/post_fix_state.txt

# Wait 5 minutes
echo "Monitoring for 5 minutes..."
sleep 300

# Count ueipab errors
echo "ueipab errors (last 5 min):" >> /tmp/post_fix_state.txt
docker logs --since 5m odoo-dev-web 2>&1 | grep "ueipab odoo.sql_db" | wc -l >> /tmp/post_fix_state.txt

# Count websocket errors
echo "websocket errors (last 5 min):" >> /tmp/post_fix_state.txt
docker logs --since 5m odoo-dev-web 2>&1 | grep "RuntimeError.*websocket" | wc -l >> /tmp/post_fix_state.txt

cat /tmp/post_fix_state.txt
```

**Expected Results:**
```
=== POST-FIX STATE ===
ueipab errors (last 5 min):
0
websocket errors (last 5 min):
0
```

---

## ROLLBACK PROCEDURE (If Needed)

### If Something Goes Wrong

**Step 1: Restore Configuration**
```bash
docker exec odoo-dev-web cp /etc/odoo/odoo.conf.bak.20251119 /etc/odoo/odoo.conf
```

**Step 2: Recreate Database (if needed)**
```bash
docker exec -i ueipab17_postgres_1 psql -U odoo << 'EOF'
CREATE DATABASE ueipab;
EOF
```

**Step 3: Restart**
```bash
docker restart odoo-dev-web
```

---

## MONITORING POST-FIX

### Monitor Logs for 10 Minutes
```bash
# Real-time monitoring
docker logs -f odoo-dev-web 2>&1 | grep --line-buffered -E "ERROR|WARNING|ueipab|websocket"
```

Press Ctrl+C after 10 minutes.

**Expected:** No ueipab or websocket errors

### Set Up Alert (Optional)
```bash
# Create monitoring script
cat > /tmp/monitor_odoo.sh << 'EOF'
#!/bin/bash
while true; do
    UEIPAB_ERRORS=$(docker logs --since 1m odoo-dev-web 2>&1 | grep "ueipab odoo.sql_db" | wc -l)
    WS_ERRORS=$(docker logs --since 1m odoo-dev-web 2>&1 | grep "RuntimeError.*websocket" | wc -l)

    if [ $UEIPAB_ERRORS -gt 0 ] || [ $WS_ERRORS -gt 0 ]; then
        echo "⚠️  ALERT: Errors detected!"
        echo "   ueipab: $UEIPAB_ERRORS, websocket: $WS_ERRORS"
    else
        echo "✅ OK - No errors ($(date))"
    fi

    sleep 60
done
EOF

chmod +x /tmp/monitor_odoo.sh
# Run in background: /tmp/monitor_odoo.sh &
```

---

## SUCCESS CRITERIA

**Fix is successful if:**

✅ **Issue #1 (ueipab database):**
- [ ] No "ueipab odoo.sql_db" errors in logs
- [ ] Database 'ueipab' no longer exists
- [ ] Cron polling only 'testing' database
- [ ] Log file clean after 5 minutes

✅ **Issue #2 (websocket):**
- [ ] No "RuntimeError: Couldn't bind websocket" errors
- [ ] No "longpolling-port is deprecated" warnings
- [ ] Websocket connections successful (Browser DevTools)
- [ ] Real-time features working (if tested)

✅ **General:**
- [ ] Odoo starts successfully
- [ ] Testing database accessible
- [ ] All existing functionality works
- [ ] No new errors introduced

---

## DOCUMENTATION UPDATE

After successful fix, update:

**File:** `/opt/odoo-dev/CLAUDE.md`

Add to "Technical Learnings" section:
```markdown
### Fixed Issues (2025-11-19)

**Empty Database Cleanup:**
- Removed orphaned 'ueipab' database (empty, not initialized)
- Eliminated ~60 cron errors per hour

**WebSocket Configuration Fix:**
- Updated deprecated `longpolling_port = 8078` → `gevent_port = 8072`
- Fixed real-time features (chat, notifications)
- Aligned with Odoo 17 best practices
```

---

## ESTIMATED TIMELINE

| Step | Time | Cumulative |
|------|------|------------|
| Backup | 1 min | 1 min |
| Drop database | 1 min | 2 min |
| Update config | 2 min | 4 min |
| Restart | 1 min | 5 min |
| Wait for startup | 1 min | 6 min |
| Verify both fixes | 2 min | 8 min |
| Functional testing | 2 min | 10 min |
| **TOTAL** | **10 min** | |

---

## RISK ASSESSMENT

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Config syntax error | Very Low | Medium | Backup created, can restore |
| Odoo won't start | Very Low | High | Rollback procedure ready |
| WebSocket still broken | Low | Medium | Check nginx config separately |
| Database drop affects production | None | N/A | Production is DB_UEIPAB (different server) |
| Data loss | None | N/A | Database confirmed empty |

**Overall Risk:** ✅ Very Low

---

## CONTACT & SUPPORT

If issues occur:
1. Check logs: `docker logs odoo-dev-web 2>&1 | tail -50`
2. Verify config: `docker exec odoo-dev-web cat /etc/odoo/odoo.conf`
3. Rollback if needed (see Rollback section)
4. Document the issue for team review

---

## APPENDIX: QUICK REFERENCE COMMANDS

```bash
# Check if ueipab database exists
docker exec -i ueipab17_postgres_1 psql -U odoo -c "\l" | grep ueipab

# Check current websocket config
docker exec odoo-dev-web grep -E "gevent|longpolling" /etc/odoo/odoo.conf

# Count recent errors
docker logs --since 10m odoo-dev-web 2>&1 | grep -E "ueipab.*sql_db|RuntimeError.*websocket" | wc -l

# Test websocket endpoint
curl -I http://localhost:8020/websocket

# Monitor logs in real-time
docker logs -f odoo-dev-web
```

---

**Status:** 📋 Ready to Execute
**Approval Needed:** Yes
**Time Required:** 10 minutes
**Risk Level:** Very Low
**Rollback Available:** Yes
