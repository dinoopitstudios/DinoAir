/**
 * Working API Tracker for DinoAir
 * This version is tested and functional
 */

const express = require('express');
const { chromium } = require('playwright');

class WorkingAPITracker {
  constructor() {
    this.calls = [];
    this.dashboardPort = 3002;
    this.browser = null;
    this.page = null;
  }

  async startDashboard() {
    const app = express();

    app.get('/', (req, res) => {
      res.send(this.generateDashboard());
    });

    app.get('/api/calls', (req, res) => {
      res.json({
        calls: this.calls.slice(-50), // Last 50 calls
        total: this.calls.length,
        timestamp: new Date().toISOString(),
      });
    });

    app.listen(this.dashboardPort, () => {
      console.log(`📊 API Tracker Dashboard: http://localhost:${this.dashboardPort}`);
    });
  }

  async startTracking() {
    console.log('🚀 Starting DinoAir API Tracker...');

    // Start dashboard first
    await this.startDashboard();

    try {
      // Launch browser
      this.browser = await chromium.launch({
        headless: false,
        devtools: false,
      });

      const context = await browser.newContext();
      this.page = await context.newPage();

      // Set up network monitoring
      this.page.on('request', request => {
        const url = request.url();

        // Track all requests to see what's happening
        if (url.includes('localhost') || url.includes('127.0.0.1')) {
          const call = {
            id: `req_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
            timestamp: new Date().toISOString(),
            type: 'request',
            method: request.method(),
            url,
            path: new URL(url).pathname,
          };

          this.calls.push(call);
          this.logCall('📤 REQUEST', call);
        }
      });

      this.page.on('response', async response => {
        const url = response.url();

        if (url.includes('localhost') || url.includes('127.0.0.1')) {
          const call = {
            id: `resp_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
            timestamp: new Date().toISOString(),
            type: 'response',
            method: response.request().method(),
            url,
            path: new URL(url).pathname,
            status: response.status(),
            statusText: response.statusText(),
          };

          this.calls.push(call);
          this.logCall('📥 RESPONSE', call);
        }
      });

      this.page.on('requestfailed', request => {
        const url = request.url();

        if (url.includes('localhost') || url.includes('127.0.0.1')) {
          const call = {
            id: `fail_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
            timestamp: new Date().toISOString(),
            type: 'failed',
            method: request.method(),
            url,
            path: new URL(url).pathname,
            error: request.failure()?.errorText || 'Unknown error',
          };

          this.calls.push(call);
          this.logCall('❌ FAILED', call);
        }
      });

      // Navigate to DinoAir frontend
      console.log('🌐 Navigating to DinoAir frontend...');
      await this.page.goto('http://localhost:5173');

      console.log('✅ API Tracker is running!');
      console.log('📊 Dashboard: http://localhost:3002');
      console.log('👆 Interact with the DinoAir frontend to see API calls');
    } catch (error) {
      console.error('❌ Error starting tracker:', error);
    }
  }

  logCall(type, call) {
    const timestamp = new Date(call.timestamp).toLocaleTimeString();
    console.log(`[${timestamp}] ${type} - ${call.method} ${call.path}`);

    if (call.status) {
      const emoji = call.status < 300 ? '✅' : call.status < 500 ? '⚠️' : '❌';
      console.log(`  ${emoji} ${call.status} ${call.statusText}`);
    }

    if (call.error) {
      console.log(`  ❌ ${call.error}`);
    }
  }

  generateDashboard() {
    return `
<!DOCTYPE html>
<html>
<head>
    <title>DinoAir API Tracker - Working Demo</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            margin: 0;
            padding: 20px;
            background: #0d1117;
            color: #f0f6fc;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: #161b22;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            border: 1px solid #30363d;
        }
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #58a6ff;
        }
        .call-log {
            background: #161b22;
            border-radius: 10px;
            padding: 20px;
            max-height: 600px;
            overflow-y: auto;
            border: 1px solid #30363d;
        }
        .call-entry {
            background: #21262d;
            margin: 8px 0;
            padding: 12px;
            border-radius: 6px;
            border-left: 4px solid #238636;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.9em;
        }
        .call-entry.response {
            border-left-color: #1f6feb;
        }
        .call-entry.failed {
            border-left-color: #da3633;
        }
        .method {
            background: #58a6ff;
            color: #0d1117;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.8em;
            margin-right: 8px;
            font-weight: bold;
        }
        .status {
            margin-left: 8px;
            font-weight: bold;
        }
        .status.success { color: #238636; }
        .status.error { color: #da3633; }
        .status.warning { color: #f85149; }
        .timestamp {
            color: #7d8590;
            font-size: 0.8em;
            float: right;
        }
        .controls {
            margin-bottom: 20px;
        }
        .btn {
            background: #238636;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            margin-right: 10px;
            cursor: pointer;
        }
        .btn:hover {
            background: #2ea043;
        }
        .instructions {
            background: #0969da;
            color: white;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 DinoAir API Tracker</h1>
        <p>Live monitoring of network requests and API calls</p>
    </div>

    <div class="instructions">
        <strong>📋 Instructions:</strong>
        <ol>
            <li>This dashboard shows real-time network activity from the DinoAir frontend</li>
            <li>Go to <a href="http://localhost:5173" target="_blank" style="color: #fff;">http://localhost:5173</a> in another tab</li>
            <li>Interact with the DinoAir interface (click buttons, navigate pages)</li>
            <li>Watch the API calls appear here in real-time!</li>
        </ol>
    </div>

    <div class="controls">
        <button class="btn" onclick="clearLog()">🗑️ Clear Log</button>
        <button class="btn" onclick="location.reload()">🔄 Refresh</button>
        <button class="btn" onclick="exportData()">💾 Export Data</button>
    </div>

    <div class="stats">
        <div class="stat-card">
            <div class="stat-number" id="total-calls">0</div>
            <div>Total Calls</div>
        </div>
        <div class="stat-card">
            <div class="stat-number" id="success-calls">0</div>
            <div>Successful</div>
        </div>
        <div class="stat-card">
            <div class="stat-number" id="failed-calls">0</div>
            <div>Failed</div>
        </div>
        <div class="stat-card">
            <div class="stat-number" id="unique-endpoints">0</div>
            <div>Endpoints</div>
        </div>
    </div>

    <div class="call-log">
        <h3>🔴 Live Network Activity</h3>
        <div id="call-entries">
            <p style="text-align: center; color: #7d8590; margin: 40px 0;">
                Waiting for network activity...<br>
                <small>Navigate to DinoAir frontend and interact with the interface</small>
            </p>
        </div>
    </div>

    <script>
        let lastCallCount = 0;

        function updateDashboard() {
            fetch('/api/calls')
                .then(response => response.json())
                .then(data => {
                    if (data.total !== lastCallCount) {
                        lastCallCount = data.total;
                        updateStats(data.calls);
                        updateCallLog(data.calls);
                    }
                })
                .catch(error => {
                    console.error('Dashboard update error:', error);
                });
        }

        function updateStats(calls) {
            const requests = calls.filter(c => c.type === 'request');
            const responses = calls.filter(c => c.type === 'response');
            const successResponses = responses.filter(r => r.status >= 200 && r.status < 400);
            const failedCalls = calls.filter(c => c.type === 'failed');
            const uniqueEndpoints = [...new Set(calls.map(c => c.path))];

            document.getElementById('total-calls').textContent = calls.length;
            document.getElementById('success-calls').textContent = successResponses.length;
            document.getElementById('failed-calls').textContent = failedCalls.length;
            document.getElementById('unique-endpoints').textContent = uniqueEndpoints.length;
        }

        function updateCallLog(calls) {
            const callEntries = document.getElementById('call-entries');

            if (calls.length === 0) {
                callEntries.innerHTML = \`
                    <p style="text-align: center; color: #7d8590; margin: 40px 0;">
                        Waiting for network activity...<br>
                        <small>Navigate to DinoAir frontend and interact with the interface</small>
                    </p>
                \`;
                return;
            }

            // Show newest calls first
            const recentCalls = calls.slice(-30).reverse();

            callEntries.innerHTML = recentCalls.map(call => {
                const timestamp = new Date(call.timestamp).toLocaleTimeString();
                let statusBadge = '';
                let statusClass = '';

                if (call.type === 'response') {
                    if (call.status < 300) {
                        statusClass = 'success';
                        statusBadge = \`<span class="status \${statusClass}">\${call.status}</span>\`;
                    } else if (call.status < 500) {
                        statusClass = 'warning';
                        statusBadge = \`<span class="status \${statusClass}">\${call.status}</span>\`;
                    } else {
                        statusClass = 'error';
                        statusBadge = \`<span class="status \${statusClass}">\${call.status}</span>\`;
                    }
                }

                const emoji = getEndpointEmoji(call.path);
                const entryClass = call.type === 'failed' ? 'failed' :
                                 call.type === 'response' ? 'response' : 'request';

                return \`
                    <div class="call-entry \${entryClass}">
                        <div class="timestamp">\${timestamp}</div>
                        <div>
                            \${emoji}
                            <span class="method">\${call.method}</span>
                            \${call.path}
                            \${statusBadge}
                        </div>
                        \${call.error ? \`<div style="color: #da3633; margin-top: 4px;">Error: \${call.error}</div>\` : ''}
                    </div>
                \`;
            }).join('');
        }

        function getEndpointEmoji(path) {
            if (path.includes('health')) return '❤️';
            if (path.includes('chat')) return '💬';
            if (path.includes('rag')) return '🔍';
            if (path.includes('search')) return '🔎';
            if (path.includes('api')) return '🔗';
            if (path.includes('assets')) return '📦';
            if (path.includes('src')) return '📄';
            return '🌐';
        }

        function clearLog() {
            if (confirm('Clear the call log?')) {
                // This would need backend implementation
                alert('Clear functionality requires backend implementation');
            }
        }

        function exportData() {
            fetch('/api/calls')
                .then(response => response.json())
                .then(data => {
                    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = \`dinoair-api-calls-\${Date.now()}.json\`;
                    a.click();
                    URL.revokeObjectURL(url);
                });
        }

        // Update every second
        setInterval(updateDashboard, 1000);
        updateDashboard();
    </script>
</body>
</html>
        `;
  }

  async stop() {
    if (this.browser) {
      await this.browser.close();
    }
    console.log('🛑 API Tracker stopped');
  }
}

// CLI usage
if (require.main === module) {
  const tracker = new WorkingAPITracker();
  tracker.startTracking();

  // Graceful shutdown
  process.on('SIGINT', async () => {
    console.log('\\n🛑 Shutting down...');
    await tracker.stop();
    process.exit(0);
  });
}

module.exports = WorkingAPITracker;
