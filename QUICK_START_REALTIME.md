# 🚀 Real-Time Architecture - Quick Start Guide

## Step 1: Verify Backend is Running

```bash
# From project root
cd backend
uvicorn backend.app:app --reload --port 8000
```

**Expected Console Output:**
```
🚀 Starting Enterprise Insider Threat Detection Platform...
📊 Initializing database...
⚙️ Starting background ML worker...
🚀 ML Worker started - listening for events...
✅ ML worker started - event-driven processing enabled
✨ Platform started successfully!
📡 Real-time architecture: API → Queue → Worker → ML → DB → WebSocket
INFO:     Uvicorn running on http://0.0.0.0:8000
```

✅ **Key Indicators:**
- "ML Worker started" - Background processor is running
- "Real-time architecture" - Event-driven system active
- WebSocket endpoint available at `ws://localhost:8000/ws/admin`

---

## Step 2: Verify Frontend is Running

```bash
# From project root
cd frontend
npm run dev
```

**Expected Output:**
```
  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

---

## Step 3: Test Real-Time Flow

### A. Login as Analyst
```
URL: http://localhost:5173/login
Username: john_analyst
Password: analyst123
```

### B. Open Dashboard
```
URL: http://localhost:5173/dashboard
```

**Check Top-Right Indicators:**
- 🟢 **Live** (green dot pulsing) - WebSocket connected
- 🟢 **Pipeline Active** - ML worker running

---

## Step 4: Trigger Real-Time Event

### Option 1: Via User Dashboard
1. Login as regular user (alice_user / user123)
2. Go to Documents
3. Upload or modify a document
4. **Watch analyst dashboard update in real-time!**

### Option 2: Via API (curl)
```bash
# Get auth token first
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=alice_user&password=user123" | jq -r '.access_token')

# Trigger event
curl -X POST http://localhost:8000/api/events/ingest \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "document_id": "DOC001",
    "document_name": "test.pdf",
    "target_department": "FINANCE",
    "action": "download",
    "bytes_transferred": 50000
  }'
```

---

## Step 5: Observe Real-Time Updates

### Backend Console (ML Worker)
```
Processing event #1 - download on test.pdf
✅ Event processed and broadcast - Queue: 0
```

### Frontend Console (Browser DevTools)
```javascript
✅ WebSocket connected
📨 Real-time update: {type: "new_event", event_id: "EVT-...", ...}
📨 Real-time update: {type: "new_alert", alert_id: "ALT-...", ...}
```

### Dashboard UI
- New alert appears at top **without page refresh**
- Alert count updates automatically
- Event stream updates live

---

## 🧪 Verify Each Component

### 1. Event Queue Status
```bash
curl http://localhost:8000/api/events/queue/status

# Expected Response:
{
  "queue_size": 0,
  "queue_capacity": 1000,
  "utilization_percent": 0.0,
  "is_healthy": true,
  "status": "healthy"
}
```

### 2. WebSocket Connections
```bash
curl http://localhost:8000/ws/status

# Expected Response:
{
  "active_connections": 1,
  "connected_users": ["USR002"]
}
```

### 3. ML Pipeline Status
```bash
curl http://localhost:8000/api/ml/status

# Expected Response:
{
  "status": "operational",
  "model_trained": true,
  "documents_registered": 18,
  "config": {...}
}
```

---

## 📊 Performance Comparison

### Before (Synchronous)
```
User uploads document
  ↓ (wait 3-5 seconds - ML processing blocks API)
Response received
  ↓ (analyst manually refreshes dashboard)
Alert visible
```
**Total Time**: 5-10 seconds

### After (Event-Driven)
```
User uploads document
  ↓ (<50ms - instant queue response)
Response received immediately
  ↓ (ML processes in background)
  ↓ (WebSocket broadcasts update)
Alert appears on dashboard instantly
```
**Total Time**: <1 second

---

## 🎯 Success Indicators

✅ **Backend**
- ML worker logs "listening for events"
- No errors in console
- WebSocket endpoint accessible

✅ **Frontend**
- "Live" indicator shows green
- Browser console shows WebSocket connection
- No connection errors

✅ **Real-Time Flow**
- Events queued instantly (API response <50ms)
- ML worker processes in background
- Dashboard updates without refresh
- Alerts appear in real-time

---

## 🐛 Quick Troubleshooting

### WebSocket won't connect?
```javascript
// Check in Browser Console:
localStorage.getItem('access_token')  // Should return JWT token
```
**Fix**: Re-login to get fresh token

### No real-time updates?
1. Check "Live" indicator - should be green
2. Open browser DevTools → Network → WS tab
3. Should see active WebSocket connection

### ML worker not processing?
1. Check backend console for errors
2. Verify queue status endpoint
3. Restart backend if needed

---

## 🎉 You're Done!

Your enterprise insider threat detection system now has:

✅ **Event-driven architecture**  
✅ **Non-blocking API**  
✅ **Background ML processing**  
✅ **Real-time WebSocket updates**  
✅ **Live dashboard**  

**This is production-grade real-time ML!**

---

## Next Steps

1. **Monitor queue health**: Keep an eye on `/api/events/queue/status`
2. **Watch WebSocket connections**: Check `/ws/status` periodically
3. **Enable notifications**: Allow browser notifications for critical alerts
4. **Scale horizontally**: Add more ML workers for higher throughput

For detailed architecture documentation, see: [REALTIME_ARCHITECTURE.md](./REALTIME_ARCHITECTURE.md)
