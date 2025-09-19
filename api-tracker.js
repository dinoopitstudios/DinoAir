/**
 * DinoAir Live API Call Tracker
 *
 * This script uses Playwright to monitor real-time API calls when users interact
 * with the DinoAir GUI. It captures the complete request flow from frontend
 * through middleware to backend services.
 */

const fs = require('fs');
const path = require('path');

const { chromium } = require('playwright');

/**
 * Class to track DinoAir API calls in real-time using Playwright.
 * Captures request and response flows and manages logging and dashboard display.
 */
class DinoAirAPITracker {
  constructor() {
    this.apiCalls = [];
    this.currentSession = {
      startTime: new Date(),
      calls: [],
    };
    this.outputDir = './api-tracking-logs';
    this.dashboardPort = 3001;

    // Ensure output directory exists
    if (!fs.existsSync(this.outputDir)) {
      fs.mkdirSync(this.outputDir, { recursive: true });
    }
  }

  /**
   * Starts the API tracking session by launching a browser, setting up monitoring,
   * and opening the DinoAir frontend.
   *
   * @returns {Promise<{browser: import('playwright').Browser, page: import('playwright').Page, context: import('playwright').BrowserContext}>} Objects for browser, page, and context.
   */
  async startTracking() {
    console.log('🚀 Starting DinoAir API Tracker...');

    // Launch browser with debugging enabled
    const browser = await chromium.launch({
      headless: false,
      devtools: true,
      args: ['--remote-debugging-port=9222'],
    });

    const context = await browser.newContext({
      // Record all network activity
      recordVideo: {
        dir: this.outputDir,
        size: { width: 1280, height: 720 },
      },
    });

    const page = await context.newPage();

    // Set up network request/response interception
    await this.setupNetworkMonitoring(page);

    // Navigate to DinoAir frontend
    console.log('📱 Navigating to DinoAir frontend...');
    await page.goto('http://localhost:5173');

    // Wait for the page to load
    await page.waitForLoadState('networkidle');
    console.log('✅ DinoAir loaded successfully');

    // Start real-time dashboard
    this.startDashboard();

    // Set up page event listeners for user interactions
    await this.setupInteractionTracking(page);

    console.log('🎯 API Tracker is now monitoring live interactions!');
    console.log('📊 View live dashboard at: http://localhost:3001');
    console.log('👆 Interact with the DinoAir GUI to see API calls in real-time');

    // Keep the tracker running
    return { browser, page, context };
  }

  /**
   * Sets up network monitoring on the provided page, intercepting requests and responses
   * to the DinoAir backend and logging them.
   *
   * @param {import('playwright').Page} page - The Playwright Page object to monitor.
   * @returns {Promise<void>}
   */
  async setupNetworkMonitoring(page) {
    console.log('🔌 Setting up network monitoring...');

    // Intercept all network requests
    page.on('request', async request => {
      const url = request.url();

      // Only track API calls to the DinoAir backend
      if (url.includes('127.0.0.1:24801') || url.includes('localhost:24801')) {
        const callData = {
          id: `call_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          timestamp: new Date().toISOString(),
          type: 'request',
          method: request.method(),
          url,
          path: new URL(url).pathname,
          headers: await request.allHeaders(),
          resourceType: request.resourceType(),
          timing: {
            started: Date.now(),
          },
        };

        // Capture request body for POST/PUT/PATCH
        if (['POST', 'PUT', 'PATCH'].includes(request.method())) {
          try {
            callData.requestBody = request.postData();
          } catch (e) {
            callData.requestBody = '[Binary or unreadable data]';
          }
        }

        this.currentSession.calls.push(callData);
        this.logAPICall('📤 REQUEST', callData);
      }
    });

    // Intercept all network responses
    page.on('response', async response => {
      const url = response.url();

      if (url.includes('127.0.0.1:24801') || url.includes('localhost:24801')) {
        const callData = {
          id: `resp_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          timestamp: new Date().toISOString(),
          type: 'response',
          method: response.request().method(),
          url,
          path: new URL(url).pathname,
          status: response.status(),
          statusText: response.statusText(),
          headers: await response.allHeaders(),
          timing: {
            completed: Date.now(),
          },
        };

        // Capture response body
        try {
          const contentType = response.headers()['content-type'] || '';
          if (contentType.includes('application/json')) {
            callData.responseBody = await response.json();
          } else if (contentType.includes('text/')) {
            callData.responseBody = await response.text();
          } else {
            callData.responseBody = '[Binary or non-text data]';
          }
        } catch (e) {
          callData.responseBody = '[Could not capture response body]';
        }

        this.currentSession.calls.push(callData);
        this.logAPICall('📥 RESPONSE', callData);

        // Update dashboard in real-time
        this.updateDashboard();
      }
    });

    // Track network failures
    page.on('requestfailed', async request => {
      const url = request.url();

      if (url.includes('127.0.0.1:24801') || url.includes('localhost:24801')) {
        const callData = {
          id: `fail_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          timestamp: new Date().toISOString(),
          type: 'failed',
          method: request.method(),
          url,
          path: new URL(url).pathname,
          failureText: request.failure()?.errorText || 'Unknown error',
          timing: {
            failed: Date.now(),
          },
        };

        this.currentSession.calls.push(callData);
        this.logAPICall('❌ FAILED', callData);
      }
    });
  }

  async setupInteractionTracking(page) {
    // Track clicks that might trigger API calls
    await page.evaluate(() => {
      // Add click tracking to all buttons and interactive elements
      document.addEventListener('click', event => {
        const target = event.target;
        const elementInfo = {
          tagName: target.tagName,
          className: target.className,
          id: target.id,
          textContent: target.textContent?.slice(0, 50) || '',
          timestamp: new Date().toISOString(),
        };

        console.log('🖱️ User clicked:', elementInfo);
      });

      // Track form submissions
      document.addEventListener('submit', event => {
        console.log('📝 Form submitted:', {
          action: event.target.action,
          method: event.target.method,
          timestamp: new Date().toISOString(),
        });
      });
    });
  }

  /**
   * Logs an API call with a timestamp, type, and request/response details.
   * @param {string} type - The category or type of the API call.
   * @param {Object} data - Details about the API request/response.
   * @param {string} data.method - The HTTP method used in the call.
   * @param {string} data.path - The endpoint path accessed.
   * @param {Object} [data.headers] - The headers sent with the request.
   * @param {string} [data.headers.x-trace-id] - The trace ID for distributed tracing.
   * @param {number} [data.status] - The HTTP status code returned.
   * @param {string} [data.statusText] - The status text associated with the HTTP status code.
   * @returns {void}
   */
  logAPICall(type, data) {
    const timestamp = new Date().toISOString();
    const logEntry = `[${timestamp}] ${type} - ${data.method} ${data.path}`;

    console.log(logEntry);

    // Enhanced logging for specific endpoints
    if (data.path === '/chat') {
      console.log('  💬 Chat API call detected');
    } else if (data.path.startsWith('/rag/')) {
      console.log('  🔍 RAG operation detected');
    } else if (data.path.startsWith('/search/')) {
      console.log('  🔎 Search operation detected');
    } else if (data.path === '/health') {
      console.log('  ❤️ Health check');
    }

    // Log headers that show middleware processing
    if (data.headers && data.headers['x-trace-id']) {
      console.log(`  📍 Trace ID: ${data.headers['x-trace-id']}`);
    }

    if (data.status) {
      const statusEmoji = data.status < 300 ? '✅' : data.status < 500 ? '⚠️' : '❌';
      console.log(`  ${statusEmoji} Status: ${data.status} ${data.statusText || ''}`);
    }

    // Save to log file
    this.saveToLogFile(logEntry, data);
  }

  /**
   * Saves a log entry and associated data to a daily JSON log file.
   * @param {string} logEntry - The log entry description.
   * @param {*} data - The data to be logged.
   */
  saveToLogFile(logEntry, data) {
    const logFile = path.join(
      this.outputDir,
      `api-calls-${new Date().toISOString().split('T')[0]}.json`
    );

    let existingLogs = [];
    if (fs.existsSync(logFile)) {
      try {
        existingLogs = JSON.parse(fs.readFileSync(logFile, 'utf8'));
      } catch (e) {
        existingLogs = [];
      }
    }

    existingLogs.push({
      logEntry,
      data,
      sessionId: this.currentSession.startTime.toISOString(),
    });

    fs.writeFileSync(logFile, JSON.stringify(existingLogs, null, 2));
  }

  /**
   * Initializes and starts the live dashboard server for real-time API call tracking.
   */
  startDashboard() {
    const express = require('express');
    const app = express();

    // Serve static dashboard files
    app.use('/static', express.static(path.join(__dirname, 'dashboard-assets')));
  /**
   * Starts the dashboard server by defining API endpoints for live data and dashboard UI,
   * and begins listening on the configured port.
   * @returns {void}
   */
  // API endpoint for live data
  app.get('/api/calls', (req, res) => {
    res.json({
      session: this.currentSession,
      calls: this.currentSession.calls.slice(-50), // Last 50 calls
    });
  });

  // Dashboard HTML
  app.get('/', (req, res) => {
    res.send(this.generateDashboardHTML());
  });

  app.listen(this.dashboardPort, () => {
    console.log(`📊 Dashboard running at http://localhost:${this.dashboardPort}`);
  });
    return `
<!DOCTYPE html>
<html>
<head>
    <title>DinoAir API Call Tracker - Live Dashboard</title>
    <meta charset="utf-8">
    <style>
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            margin: 0;
            padding: 20px;
            background: #1a1a1a;
            color: #ffffff;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 2em;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: #2d2d2d;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            border-left: 4px solid #667eea;
        }
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }
        .call-log {
            background: #2d2d2d;
            border-radius: 8px;
            padding: 20px;
            max-height: 600px;
            overflow-y: auto;
        }
`;
  }
        .call-entry {
            background: #3d3d3d;
            margin: 10px 0;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #28a745;
        }
        .call-entry.response {
            border-left-color: #17a2b8;
        }
        .call-entry.failed {
            border-left-color: #dc3545;
        }
        .call-header {
            font-weight: bold;
            margin-bottom: 5px;
        }
        .call-details {
            font-size: 0.9em;
            color: #cccccc;
        }
        .method-badge {
            background: #667eea;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            margin-right: 10px;
        }
        .status-badge {
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            margin-left: 10px;
        }
        .status-success { background: #28a745; color: white; }
        .status-error { background: #dc3545; color: white; }
        .status-warning { background: #ffc107; color: black; }
        .auto-refresh {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #667eea;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 20px;
            cursor: pointer;
        }
        .timestamp {
            color: #888;
            font-size: 0.8em;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 DinoAir API Call Tracker</h1>
        <p>Live monitoring of API calls during GUI interactions</p>
    </div>

    <div class="stats">
        <div class="stat-card">
            <div class="stat-number" id="total-calls">0</div>
            <div>Total API Calls</div>
        </div>
        <div class="stat-card">
            <div class="stat-number" id="successful-calls">0</div>
            <div>Successful</div>
        </div>
        <div class="stat-card">
            <div class="stat-number" id="failed-calls">0</div>
            <div>Failed</div>
        </div>
        <div class="stat-card">
            <div class="stat-number" id="avg-response-time">0ms</div>
            <div>Avg Response Time</div>
        </div>
    </div>

    <div class="call-log">
        <h3>🔴 Live API Call Log</h3>
        <div id="call-entries">
            <p>Waiting for API calls... Interact with the DinoAir GUI to see live tracking!</p>
        </div>
    </div>

    <button class="auto-refresh" onclick="toggleAutoRefresh()">
        <span id="refresh-status">Auto-refresh: ON</span>
    </button>

    <script>
        let autoRefresh = true;
        let refreshInterval;

        function updateDashboard() {
            fetch('/api/calls')
                .then(response => response.json())
                .then(data => {
                    updateStats(data.calls);
                    updateCallLog(data.calls);
                })
                .catch(error => {
                    console.error('Error fetching data:', error);
                });
        }

        function updateStats(calls) {
            const totalCalls = calls.length;
            const successfulCalls = calls.filter(call =>
                call.type === 'response' && call.status >= 200 && call.status < 400
            ).length;
            const failedCalls = calls.filter(call =>
                call.type === 'failed' || (call.type === 'response' && call.status >= 400)
            ).length;

            document.getElementById('total-calls').textContent = totalCalls;
            document.getElementById('successful-calls').textContent = successfulCalls;
            document.getElementById('failed-calls').textContent = failedCalls;
        }

        function updateCallLog(calls) {
            const callEntries = document.getElementById('call-entries');

            if (calls.length === 0) {
                callEntries.innerHTML = '<p>Waiting for API calls... Interact with the DinoAir GUI to see live tracking!</p>';
                return;
            }

            const recentCalls = calls.slice(-20).reverse(); // Show last 20 calls, newest first

            callEntries.innerHTML = recentCalls.map(call => {
                const isResponse = call.type === 'response';
                const isFailed = call.type === 'failed';
                const entryClass = isFailed ? 'failed' : (isResponse ? 'response' : 'request');

                let statusBadge = '';
                if (isResponse) {
                    const statusClass = call.status < 300 ? 'status-success' :
                                      call.status < 500 ? 'status-warning' : 'status-error';
                    statusBadge = \`<span class="status-badge \${statusClass}">\${call.status}</span>\`;
                }

                const endpoint = call.path || new URL(call.url).pathname;
                const emoji = getEndpointEmoji(endpoint);

                return \`
                    <div class="call-entry \${entryClass}">
                        <div class="call-header">
                            \${emoji} <span class="method-badge">\${call.method}</span>
                            \${endpoint}
                            \${statusBadge}
                        </div>
                        <div class="call-details">
                            <div class="timestamp">\${new Date(call.timestamp).toLocaleTimeString()}</div>
                            \${call.headers && call.headers['x-trace-id'] ?
                                \`<div>Trace ID: \${call.headers['x-trace-id']}</div>\` : ''}
                            \${isFailed ? \`<div style="color: #ff6b6b;">Error: \${call.failureText}</div>\` : ''}
                        </div>
                    </div>
                \`;
            }).join('');
        }

        function getEndpointEmoji(path) {
            if (path === '/health') return '❤️';
            if (path === '/chat') return '💬';
            if (path.startsWith('/rag/')) return '🔍';
            if (path.startsWith('/search/')) return '🔎';
            if (path.startsWith('/tools/')) return '🛠️';
            if (path === '/translate') return '🌐';
            if (path === '/metrics') return '📊';
            return '🔗';
        }

        function toggleAutoRefresh() {
            autoRefresh = !autoRefresh;
            const statusEl = document.getElementById('refresh-status');

            if (autoRefresh) {
                statusEl.textContent = 'Auto-refresh: ON';
                startAutoRefresh();
            } else {
                statusEl.textContent = 'Auto-refresh: OFF';
                if (refreshInterval) {
                    clearInterval(refreshInterval);
                }
            }
        }

        function startAutoRefresh() {
            if (refreshInterval) {
                clearInterval(refreshInterval);
            }
            refreshInterval = setInterval(updateDashboard, 1000); // Update every second
        }

        // Initial load and start auto-refresh
        updateDashboard();
        startAutoRefresh();
    </script>
</body>
</html>
        `;
  }

  updateDashboard() {
    // This method is called when new API calls are detected
    // The dashboard will auto-refresh via client-side polling
  }

  /**
   * Generates and saves the API tracking report.
   *
   * Collects session start/end times, computes duration and summary statistics
   * (total calls, successful calls, failed calls, unique endpoints), writes
   * the report to a JSON file in the output directory, and returns the report.
   *
   * @async
   * @returns {Object} The tracking report object.
   */
  async generateReport() {
    const reportFile = path.join(this.outputDir, `api-tracking-report-${Date.now()}.json`);

    const report = {
      sessionInfo: {
        startTime: this.currentSession.startTime,
        endTime: new Date(),
        duration: Date.now() - this.currentSession.startTime.getTime(),
      },
      summary: {
        totalCalls: this.currentSession.calls.length,
        successfulCalls: this.currentSession.calls.filter(
          c => c.type === 'response' && c.status >= 200 && c.status < 400
        ).length,
        failedCalls: this.currentSession.calls.filter(
          c => c.type === 'failed' || (c.type === 'response' && c.status >= 400)
        ).length,
        endpoints: [...new Set(this.currentSession.calls.map(c => c.path))],
      },
      calls: this.currentSession.calls,
    };

    fs.writeFileSync(reportFile, JSON.stringify(report, null, 2));
    console.log(`📋 Tracking report saved to: ${reportFile}`);

    return report;
  }
}

// CLI Interface
async function main() {
  const tracker = new DinoAirAPITracker();

  try {
    const { browser, page } = await tracker.startTracking();

    // Handle graceful shutdown
    process.on('SIGINT', async () => {
      console.log('\n🛑 Shutting down API tracker...');
      await tracker.generateReport();
      await browser.close();
      console.log('✅ Tracker stopped successfully');
      process.exit(0);
    });

    // Keep the process alive
    console.log('\n📝 Press Ctrl+C to stop tracking and generate report');
    await new Promise(() => {}); // Keep running indefinitely
  } catch (error) {
    console.error('❌ Error starting API tracker:', error);
    process.exit(1);
  }
}

// Export for module usage
module.exports = DinoAirAPITracker;

// Run if called directly
if (require.main === module) {
  main();
}
