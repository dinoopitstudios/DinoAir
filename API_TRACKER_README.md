# DinoAir Live API Tracker

## 🚀 Real-Time API Call Monitoring for GUI Interactions

This system provides live tracking and visualization of API calls as users interact with the DinoAir GUI. Using Playwright to intercept network traffic, it shows the complete request flow from frontend through middleware to backend services.

## ✨ Features

### 📊 **Live Visual Dashboard**

- **Real-time flow diagram** showing request path through middleware pipeline
- **Interactive node visualization** with click-to-explore details
- **Animated request flows** with color-coded success/error states
- **Live statistics** including success rates and response times

### 🔍 **Comprehensive Request Tracking**

- **Network interception** captures all API calls to DinoAir backend
- **Middleware visibility** shows auth, body limits, timeouts, CORS processing
- **Header analysis** including trace IDs, auth tokens, content types
- **Payload capture** for both requests and responses (JSON/text)

### 📈 **Analytics & Reporting**

- **Performance metrics** with response time analysis
- **Success/failure rates** with error categorization
- **Request frequency** tracking (requests per minute)
- **Export functionality** for detailed analysis

### 🎯 **GUI Interaction Focus**

- **Click tracking** on interactive elements
- **Form submission** monitoring
- **Page navigation** correlation with API calls
- **User action context** for understanding API triggers

## 🛠️ Installation & Setup

### Quick Setup

```bash
# Install the tracker system
node setup-api-tracker.js

# This will:
# 1. Install Playwright and Express dependencies
# 2. Create tracker configuration files
# 3. Set up dashboard server
# 4. Add npm scripts to package.json
```

### Manual Installation

```bash
# Install dependencies
npm install playwright express @playwright/test

# Install Playwright browsers
npx playwright install chromium
```

## 🚦 Usage

### Start Complete Tracking System

```bash
# Start DinoAir backend (Terminal 1)
npm run api

# Start DinoAir frontend (Terminal 2)
npm run dev

# Start API tracker (Terminal 3)
npm run track:api
```

### Access Live Dashboard

1. Open http://localhost:3001 in your browser
2. Click "▶️ Start Tracking"
3. Interact with DinoAir GUI at http://localhost:5173
4. Watch real-time API call visualization!

## 📊 Dashboard Features

### Flow Visualization

- **Frontend → API Library → Middleware Stack → Backend**
- **Animated request paths** showing middleware processing
- **Color-coded status indicators:**
  - 🔵 **Active**: Request in progress
  - 🟢 **Success**: 2xx responses
  - 🔴 **Error**: 4xx/5xx responses or failures

### Live Statistics Panel

- **Total Requests**: Count of all API calls
- **Success Rate**: Percentage of successful requests
- **Average Response Time**: Performance metric
- **Requests/Minute**: Current activity level

### Call Log

- **Real-time entries** for every API call
- **Method badges** (GET, POST, PUT, etc.)
- **Endpoint paths** with emoji indicators
- **Trace ID tracking** for request correlation
- **Timestamp information** for timing analysis

## 🔍 What Gets Tracked

### API Endpoints Monitored

- ❤️ `/health` - Health checks (public)
- 💬 `/chat` - AI chat interactions
- 🔍 `/rag/*` - Document ingestion & context retrieval
- 🔎 `/search/*` - Keyword and vector search
- 🛠️ `/tools/*` - Tool execution
- 🌐 `/translate` - Code translation
- 📊 `/metrics` - System metrics

### Middleware Processing

1. **CORS Validation** - Cross-origin request handling
2. **Request ID** - UUID generation and trace header addition
3. **GZip Compression** - Response compression
4. **Logging** - Structured request/response logging
5. **Timeout Protection** - 30-second request limits
6. **Authentication** - `X-DinoAir-Auth` header validation
7. **Body Size Limits** - 10MB maximum request size
8. **Content Type** - JSON validation for POST requests

### Data Captured

```javascript
{
  "id": "call_1234567890_abc123",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "type": "request|response|failed",
  "method": "POST",
  "url": "http://127.0.0.1:24801/chat",
  "path": "/chat",
  "headers": {
    "x-dinoair-auth": "...",
    "x-trace-id": "uuid-here",
    "content-type": "application/json"
  },
  "requestBody": {...},
  "status": 200,
  "responseBody": {...},
  "timing": {
    "started": 1234567890,
    "completed": 1234567892
  }
}
```

## 🎮 Interactive Features

### Dashboard Controls

- **▶️ Start Tracking**: Begin monitoring API calls
- **⏹️ Stop Tracking**: Pause monitoring
- **🗑️ Clear Log**: Reset call history
- **💾 Export Data**: Download tracking data as JSON

### Flow Diagram Interactions

- **Click nodes** to see detailed information
- **Hover effects** for enhanced visibility
- **Animation controls** for request flow visualization

## 📁 File Structure

```
DinoAir/
├── api-tracker/
│   ├── config/
│   │   └── tracker-config.json     # Tracker configuration
│   ├── logs/                       # API call logs
│   ├── reports/                    # Generated reports
│   ├── tracker.js                  # Main tracking script
│   ├── dashboard-server.js         # Dashboard backend
│   └── run.js                      # Startup script
├── api-flow-dashboard.html         # Dashboard UI
├── setup-api-tracker.js           # Setup script
└── playwright.config.api-tracker.ts # Playwright config
```

## 🔧 Configuration

### Tracker Settings (`api-tracker/config/tracker-config.json`)

```json
{
  "frontend": {
    "url": "http://localhost:5173",
    "waitForLoadState": "networkidle"
  },
  "backend": {
    "url": "http://127.0.0.1:24801",
    "healthEndpoint": "/health"
  },
  "dashboard": {
    "port": 3001,
    "updateInterval": 1000
  },
  "tracking": {
    "captureRequests": true,
    "captureResponses": true,
    "captureHeaders": true,
    "captureBodies": true,
    "maxLogSize": 1000
  }
}
```

## 📊 Example Tracking Session

### Chat Interaction Flow

```
1. User clicks "Send" in ChatPage
   📤 REQUEST - POST /chat

2. Middleware Processing (animated in dashboard):
   → CORS validation
   → Request ID assignment (trace_id: abc123)
   → Authentication check
   → Body size validation
   → Route to chat handler

3. Backend Processing:
   → Chat route handler
   → LM Studio integration
   → Response generation

4. Response Return:
   📥 RESPONSE - 200 OK (trace_id: abc123)
   → JSON response with AI message
   → Compressed with GZip
   → Logged with performance metrics
```

### RAG Document Ingestion

```
1. User uploads document in ToolsPage
   📤 REQUEST - POST /rag/ingest/directory

2. Middleware stack processing
3. RAG service handling:
   → Document processing
   → Vector generation
   → Storage in vector database

4. Success response with ingestion results
```

## 🐛 Troubleshooting

### Common Issues

#### Tracker Won't Start

- Ensure DinoAir backend is running on port 24801
- Check that frontend is accessible at localhost:5173
- Verify Playwright browsers are installed: `npx playwright install`

#### No API Calls Visible

- Make sure you're interacting with DinoAir GUI, not just the dashboard
- Check browser console for CORS or network errors
- Verify backend URL in tracker configuration

#### Dashboard Not Loading

- Confirm dashboard server is running on port 3001
- Check for port conflicts with other services
- Ensure `api-flow-dashboard.html` exists

### Debug Mode

```bash
# Run tracker with debug output
DEBUG=1 npm run track:api
```

## 🔮 Advanced Features

### Custom Endpoint Tracking

Add new endpoints to monitor by updating the emoji mapping in the dashboard:

```javascript
function getEndpointEmoji(path) {
  if (path === '/custom-endpoint') return '⚡';
  // ... existing mappings
}
```

### Export Formats

The tracker supports exporting data in multiple formats:

- **JSON**: Complete tracking data with timing information
- **CSV**: Simplified format for spreadsheet analysis
- **HTML Report**: Formatted summary report

### Integration with Testing

The tracker can be integrated with automated testing:

```javascript
// In your Playwright tests
import { APITracker } from './api-tracker/tracker.js';

test('chat functionality with API tracking', async ({ page }) => {
  const tracker = new APITracker();
  await tracker.startTracking();

  // Your test interactions
  await page.goto('http://localhost:5173');
  await page.click('[data-testid="send-chat"]');

  // Analyze API calls
  const calls = tracker.getCallData();
  expect(calls.some(call => call.path === '/chat')).toBeTruthy();
});
```

## 🤝 Contributing

To extend the tracker:

1. **Add new middleware tracking**: Update the flow diagram in `api-flow-dashboard.html`
2. **Enhance visualizations**: Modify D3.js animations for new request types
3. **Add new metrics**: Extend statistics calculation in dashboard server
4. **Custom reports**: Create new export formats in the tracker script

---

**Start tracking your DinoAir API calls now and gain complete visibility into your application's request flow!** 🚀
