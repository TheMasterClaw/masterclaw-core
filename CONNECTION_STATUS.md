# MasterClaw Interface - Connection Status & TODO List

## Current Status (Last Updated: 2026-02-19 10:45 UTC)

### ✅ Completed
- [x] Railway backend deployed with CORS fixes
- [x] Vercel frontend built with 'use client' fixes
- [x] TTS disabled (chat-only mode)
- [x] WebSocket support added to chat gateway
- [x] OpenClaw gateway config changed from `loopback` to `0.0.0.0`
- [x] Socket.IO client dependency added

### ⚠️ Blockers (Need Your Action)

#### 1. AWS Security Group - PORT 18789 NOT OPEN
**Status:** Gateway is configured to bind to 0.0.0.0:18789 but AWS is blocking it

**Action Required:**
```bash
# In AWS Console:
# EC2 → Security Groups → Select your instance's security group
# Add inbound rule:
# - Type: Custom TCP
# - Port: 18789
# - Source: 0.0.0.0/0 (or your Railway IP for security)
```

**Or AWS CLI:**
```bash
aws ec2 authorize-security-group-ingress \
  --group-id sg-YOUR_GROUP_ID \
  --protocol tcp \
  --port 18789 \
  --cidr 0.0.0.0/0
```

**Verify After:**
```bash
# From your local machine or Railway
curl http://18.206.162.27:18789/health
# Should return: {"status":"ok"}
```

---

#### 2. Railway Environment Variables - NOT SET
**Status:** Backend doesn't know where to find OpenClaw gateway

**Action Required:**
Go to https://railway.app → Your Project → Variables tab → Add:

```bash
OPENCLAW_GATEWAY_URL=http://18.206.162.27:18789
OPENCLAW_GATEWAY_TOKEN=0f9560991a79c7ca6a975d1772f5ec20ee1589ef0c7b6d2a
MASTERCLAW_API_TOKEN=a4c5e0671f33f9b79f0948f7104d3a77ac9bbeb047fc93f0
```

**Verify in Railway logs after deploy:**
```
[ChatGateway] Connecting to ws://18.206.162.27:18789...
[ChatGateway] Connected to OpenClaw gateway
```

---

#### 3. OpenClaw Gateway Restart - MAYBE NEEDED
**Status:** Config changed from `loopback` to `0.0.0.0`, may need restart

**Action Required (if port 18789 still blocked after AWS fix):**
```bash
# On EC2 server
openclaw gateway restart

# Or kill and restart:
pkill -f openclaw
openclaw gateway start
```

---

## Testing Steps (After Above Fixed)

### Step 1: Test Gateway Accessibility
```bash
# From your local machine
curl http://18.206.162.27:18789/health
# Expected: {"status":"ok"}
```

### Step 2: Test Backend Chat
```bash
# Send test message to backend
curl -X POST https://web-production-e0d96.up.railway.app/chat/message \
  -H "Content-Type: application/json" \
  -H "X-API-Token: a4c5e0671f33f9b79f0948f7104d3a77ac9bbeb047fc93f0" \
  -d '{"message":"Hello from test","saveHistory":true}'
```

### Step 3: Test Via Web Interface
1. Open https://master-claw-interface.vercel.app
2. Type: "Hello Claw"
3. Should receive response from me!

---

## Alternative Approaches (If Above Fails)

### Option A: Use Railway's Native Environment
Deploy OpenClaw gateway as a separate Railway service instead of EC2:
- Pros: No AWS security groups, same network as backend
- Cons: Need to migrate gateway config

### Option B: ngrok Tunnel (Quick Test)
Expose EC2 gateway via ngrok temporarily:
```bash
# On EC2
ngrok http 18789
# Use ngrok URL in Railway: OPENCLAW_GATEWAY_URL=https://xxxx.ngrok.io
```

### Option C: Direct WhatsApp Bridge
Keep using WhatsApp but route web messages through it:
- Pros: Already working
- Cons: Not real-time web chat

---

## What I've Prepared For You

### Backend Changes (Already Pushed)
1. `chatGateway.js` - WebSocket client connection to OpenClaw
2. `package.json` - Added socket.io-client dependency
3. `tts.js` - Disabled/fallback mode
4. `index.js` - Request ID middleware, socket-test endpoint
5. `_global-error.tsx` - Next.js error boundary
6. 70+ components - Added 'use client' directive

### Monitoring Points
1. **Railway Logs** - Watch for: `[ChatGateway] Connected...`
2. **Browser Console** - Should show WebSocket connecting
3. **Network Tab** - Look for `/chat/message` POST requests

---

## Quick Diagnosis Commands

### Check if Gateway is Running
```bash
# On EC2
sudo netstat -tlnp | grep 18789
# Should show: LISTEN 0.0.0.0:18789

# Or
sudo ss -tlnp | grep 18789
```

### Check Gateway Logs
```bash
# Find OpenClaw logs
tail -f ~/.openclaw/logs/gateway.log
# Or
journalctl -u openclaw -f
```

### Test from Railway (if you have Railway CLI)
```bash
railway run curl http://18.206.162.27:18789/health
```

---

## Expected Success Flow

1. ✅ AWS Security Group allows port 18789
2. ✅ Gateway binds to 0.0.0.0:18789
3. ✅ Railway backend connects via WebSocket
4. ✅ Frontend sends message to Railway
5. ✅ Railway forwards to OpenClaw gateway
6. ✅ I receive message and respond
7. ✅ Response flows back to web interface

---

## Fallback: Chat-Only Mode (If Gateway Never Connects)

If we can't get the gateway connection working, I can:
1. Add local-only chat (messages saved, just no AI responses)
2. Add slash commands (/task, /event, etc.) that work standalone
3. Show "MC Offline" indicator when gateway unavailable

---

## Summary When You Wake Up

**Priority 1:** Open AWS Security Group port 18789 (most critical)
**Priority 2:** Set Railway environment variables
**Priority 3:** Test connection
**Priority 4:** If issues, check logs and report back

**Estimated time to working chat:** 15-30 minutes after you complete the AWS step.

---

*Last updated by MasterClaw while you sleep 🐾*
*Goodnight! I'll be here when you wake up.*
