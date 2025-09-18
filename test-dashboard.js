const fs = require('fs');
const path = require('path');

const express = require('express');

// Simple dashboard server to test the concept
class SimpleDashboard {
  constructor() {
    this.app = express();
    this.port = 3001;
    this.calls = [];
  }

  start() {
    // Serve static dashboard
    this.app.get('/', (req, res) => {
      res.send(this.generateDashboard());
    });

    // API endpoint for call data
    this.app.get('/api/calls', (req, res) => {
      res.json({
        calls: this.calls,
        timestamp: new Date().toISOString(),
      });
    });

    // Simulate some API calls for testing
    this.simulateCalls();

    this.app.listen(this.port, () => {
      console.log(`🌐 Test Dashboard running at http://localhost:${this.port}`);
    });
  }

  simulateCalls() {
    // Add some mock API calls to test the dashboard
    setTimeout(() => {
      this.calls.push({
        id: 'call_1',
        timestamp: new Date().toISOString(),
        type: 'request',
        method: 'GET',
        path: '/health',
        headers: { 'x-trace-id': 'abc123' },
      });

      this.calls.push({
        id: 'call_2',
        timestamp: new Date().toISOString(),
        type: 'response',
        method: 'GET',
        path: '/health',
        status: 200,
        headers: { 'x-trace-id': 'abc123' },
      });
    }, 2000);

    setTimeout(() => {
      this.calls.push({
        id: 'call_3',
        timestamp: new Date().toISOString(),
        type: 'request',
        method: 'POST',
        path: '/chat',
        headers: { 'x-trace-id': 'def456' },
      });

      this.calls.push({
        id: 'call_4',
        timestamp: new Date().toISOString(),
        type: 'response',
        method: 'POST',
        path: '/chat',
        status: 200,
        headers: { 'x-trace-id': 'def456' },
      });
    }, 4000);
  }

  generateDashboard() {
    return `
<!DOCTYPE html>
<html>
<head>
    <title>DinoAir API Tracker - Test Dashboard</title>
    <style>
        body {
            font-family: 'Segoe UI', sans-serif;
            margin: 0;
            padding: 20px;
            background: #0d1117;
            color: #ffffff;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
        }
        .call-log {
            background: #161b22;
            border-radius: 10px;
            padding: 20px;
            max-height: 600px;
            overflow-y: auto;
        }
        .call-entry {
            background: #21262d;
            margin: 10px 0;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #28a745;
        }
        .call-entry.response {
            border-left-color: #17a2b8;
        }
        .method-badge {
            background: #667eea;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            margin-right: 10px;
        }
        .timestamp {
            color: #8b949e;
            font-size: 0.8em;
            float: right;
        }
        .status {
            color: #28a745;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 DinoAir API Tracker - Test Dashboard</h1>
        <p>Testing API call visualization concept</p>
    </div>

    <div class="call-log">
        <h3>🔴 API Call Log (Simulated)</h3>
        <div id="call-entries">
            <p>Loading simulated API calls...</p>
        </div>
    </div>

    <script>
        function updateDashboard() {
            fetch('/api/calls')
                .then(response => response.json())
                .then(data => {
                    updateCallLog(data.calls);
                })
                .catch(error => {
                    console.error('Error fetching data:', error);
                });
        }

        function updateCallLog(calls) {
            const callEntries = document.getElementById('call-entries');

            if (calls.length === 0) {
                callEntries.innerHTML = '<p>No API calls yet...</p>';
                return;
            }

            callEntries.innerHTML = calls.map(call => {
                const isResponse = call.type === 'response';
                const entryClass = isResponse ? 'response' : 'request';

                let statusBadge = '';
                if (isResponse) {
                    statusBadge = \`<span class="status">\${call.status}</span>\`;
                }

                const emoji = getEndpointEmoji(call.path);

                return \`
                    <div class="call-entry \${entryClass}">
                        <div class="timestamp">\${new Date(call.timestamp).toLocaleTimeString()}</div>
                        <div>
                            \${emoji}
                            <span class="method-badge">\${call.method}</span>
                            \${call.path}
                            \${statusBadge}
                        </div>
                        \${call.headers && call.headers['x-trace-id'] ?
                            \`<div style="font-size: 0.8em; color: #8b949e; margin-top: 4px;">
                                Trace: \${call.headers['x-trace-id']}
                            </div>\` : ''}
                    </div>
                \`;
            }).join('');
        }

        function getEndpointEmoji(path) {
            if (path === '/health') return '❤️';
            if (path === '/chat') return '💬';
            if (path.startsWith('/rag/')) return '🔍';
            if (path.startsWith('/search/')) return '🔎';
            return '🔗';
        }

        // Update every 2 seconds
        setInterval(updateDashboard, 2000);
        updateDashboard();
    </script>
</body>
</html>
        `;
  }
}

const dashboard = new SimpleDashboard();
dashboard.start();
