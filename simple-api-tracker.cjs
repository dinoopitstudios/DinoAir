/**
 * Simplified Working API Tracker for DinoAir
 * Focus on core functionality with clean code
 */

const express = require('express');
const { chromium } = require('playwright');

/**
 * DinoAirAPITracker tracks API calls from the DinoAir frontend,
 * logs requests and responses, and provides a dashboard server.
 */
class DinoAirAPITracker {
  constructor() {
    this.calls = [];
    this.dashboardPort = 3002;
    this.browser = null;
    this.page = null;
  }

  /**
   * Starts the Express server for the dashboard at the configured port.
   * @returns {Promise<void>}
   */
  async startDashboard() {
    const app = express();

    app.get('/', (req, res) => {
      res.send(this.generateDashboard());
    });

    app.get('/api/calls', (req, res) => {
      res.json({
        calls: this.calls.slice(-50),
        total: this.calls.length,
        timestamp: new Date().toISOString(),
      });
    });

    app.listen(this.dashboardPort, () => {
      console.log(`📊 DinoAir API Tracker: http://localhost:${this.dashboardPort}`);
    });
  }

  /**
   * Starts tracking API calls by launching the browser,
   * setting up request/response handlers, and navigating to the frontend.
   * Also initializes the dashboard server.
   * @returns {Promise<void>}
   */
  async startTracking() {
    console.log('🚀 Starting DinoAir API Tracker...');

    await this.startDashboard();

    try {
      this.browser = await chromium.launch({
        headless: false,
        devtools: false,
      });

      const context = await this.browser.newContext();
      this.page = await context.newPage();

      this.page.on('request', request => {
        const url = request.url();

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
  /**
   * Logs the result of an API call to the console with an appropriate status emoji.
   * @param {{status: number, statusText: string, error?: string}} call - The API call response object.
   * @returns {void}
   */
  logCall(call) {
      const emoji = call.status < 300 ? '✅' : call.status < 500 ? '⚠️' : '❌';
      console.log(`  ${emoji} ${call.status} ${call.statusText}`);
    }

    if (call.error) {
      console.log(`  ❌ ${call.error}`);
    }
  }

  /**
   * Generates the HTML for the dashboard page.
   * @returns {string}
   */
  generateDashboard() {
    return `
<!DOCTYPE html>
<html>
<head>
    <title>DinoAir API Tracker</title>
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
`;}
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
        .timestamp {
            color: #7d8590;
            font-size: 0.8em;
            float: right;
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
        <p>Live monitoring of API calls and network requests</p>
    </div>

    <div class="instructions">
        <strong>📋 Instructions:</strong>
        <ol>
            <li>Go to <a href="http://localhost:5173" target="_blank" style="color: #fff;">DinoAir Frontend</a></li>
            <li>Interact with the interface (chat, search, etc.)</li>
            <li>Watch API calls appear here in real-time!</li>
        </ol>
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
                <small>Navigate to DinoAir and interact with the interface</small>
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
                        <small>Navigate to DinoAir and interact with the interface</small>
                    </p>
                \`;
                return;
            }

            const recentCalls = calls.slice(-20).reverse();

            callEntries.innerHTML = recentCalls.map(call => {
                const timestamp = new Date(call.timestamp).toLocaleTimeString();
                const emoji = getEndpointEmoji(call.path);
                const entryClass = call.type === 'failed' ? 'failed' :
                                 call.type === 'response' ? 'response' : 'request';

                let statusText = '';
                if (call.status) {
                    statusText = \`<span style="margin-left: 8px; font-weight: bold; color: \${
                        call.status < 300 ? '#238636' : call.status < 500 ? '#f85149' : '#da3633'
                    };">\${call.status}</span>\`;
                }

                return \`
                    <div class="call-entry \${entryClass}">
                        <div class="timestamp">\${timestamp}</div>
                        <div>
                            \${emoji}
                            <span class="method">\${call.method}</span>
                            \${call.path}
                            \${statusText}
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
            return '🌐';
        }

        setInterval(updateDashboard, 1000);
        updateDashboard();
    </script>
</body>
</html>
    `;
  }

  /**
   * Stops the API Tracker by closing the browser instance and logging the stop event.
   * @returns {Promise<void>} A promise that resolves when the browser is closed.
   */
  async stop() {
    if (this.browser) {
      await this.browser.close();
    }
    console.log('🛑 API Tracker stopped');
  }
}

if (require.main === module) {
  const tracker = new DinoAirAPITracker();
  tracker.startTracking();

  process.on('SIGINT', async () => {
    console.log('\n🛑 Shutting down...');
    await tracker.stop();
    process.exit(0);
  });
}

module.exports = DinoAirAPITracker;
