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
      console.log('📊 Visit the dashboard to see simulated API calls');
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
      console.log('✅ Added health check calls');
    }, 2000);

    setTimeout(() => {
      this.calls.push({
        id: 'call_3',
        timestamp: new Date().toISOString(),
        type: 'request',
        method: 'POST',
        path: '/chat',
        headers: { 'x-trace-id': 'def456' },
        requestBody: { message: 'Hello DinoAir!' },
      });

      this.calls.push({
        id: 'call_4',
        timestamp: new Date().toISOString(),
        type: 'response',
        method: 'POST',
        path: '/chat',
        status: 200,
        headers: { 'x-trace-id': 'def456' },
        responseBody: { response: 'Hello! How can I help you?' },
      });
      console.log('💬 Added chat calls');
    }, 4000);

    setTimeout(() => {
      this.calls.push({
        id: 'call_5',
        timestamp: new Date().toISOString(),
        type: 'request',
        method: 'POST',
        path: '/rag/ingest/directory',
        headers: { 'x-trace-id': 'ghi789' },
      });

      this.calls.push({
        id: 'call_6',
        timestamp: new Date().toISOString(),
        type: 'response',
        method: 'POST',
        path: '/rag/ingest/directory',
        status: 201,
        headers: { 'x-trace-id': 'ghi789' },
      });
      console.log('🔍 Added RAG ingestion calls');
    }, 6000);
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
            border-left: 4px solid #667eea;
        }
        .stat-number {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
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
            margin-left: 10px;
        }
        .trace-id {
            font-size: 0.8em;
            color: #8b949e;
            margin-top: 4px;
        }
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
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 DinoAir API Tracker - Test Dashboard</h1>
        <p>Testing API call visualization concept with simulated data</p>
    </div>

    <div class="stats">
        <div class="stat-card">
            <div class="stat-number" id="total-calls">0</div>
            <div>Total API Calls</div>
        </div>
        <div class="stat-card">
            <div class="stat-number" id="success-rate">100%</div>
            <div>Success Rate</div>
        </div>
        <div class="stat-card">
            <div class="stat-number" id="endpoint-count">0</div>
            <div>Unique Endpoints</div>
        </div>
    </div>

    <div class="call-log">
        <h3>🔴 Live API Call Log (Simulated)</h3>
        <div id="call-entries">
            <p>Loading simulated API calls...</p>
        </div>
    </div>

    <button class="auto-refresh" onclick="location.reload()">🔄 Refresh</button>

    <script>
        function updateDashboard() {
            fetch('/api/calls')
                .then(response => response.json())
                .then(data => {
                    updateStatistics(data.calls);
                    updateCallLog(data.calls);
                })
                .catch(error => {
                    console.error('Error fetching data:', error);
                });
        }

        function updateStatistics(calls) {
            const requests = calls.filter(c => c.type === 'request');
            const responses = calls.filter(c => c.type === 'response');
            const successResponses = responses.filter(r => r.status >= 200 && r.status < 400);
            const uniqueEndpoints = [...new Set(calls.map(c => c.path))];

            const successRate = responses.length > 0 ?
                Math.round((successResponses.length / responses.length) * 100) : 100;

            document.getElementById('total-calls').textContent = calls.length;
            document.getElementById('success-rate').textContent = successRate + '%';
            document.getElementById('endpoint-count').textContent = uniqueEndpoints.length;
        }

        function updateCallLog(calls) {
            const callEntries = document.getElementById('call-entries');

            if (calls.length === 0) {
                callEntries.innerHTML = '<p>No API calls yet... Simulated calls will appear shortly.</p>';
                return;
            }

            callEntries.innerHTML = calls.reverse().map(call => {
                const isResponse = call.type === 'response';
                const entryClass = isResponse ? 'response' : 'request';

                let statusBadge = '';
                if (isResponse) {
                    const statusColor = call.status < 300 ? '#28a745' :
                                      call.status < 500 ? '#f39c12' : '#dc3545';
                    statusBadge = \`<span class="status" style="color: \${statusColor};">\${call.status}</span>\`;
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
                            \`<div class="trace-id">Trace: \${call.headers['x-trace-id']}</div>\` : ''}
                        \${call.requestBody ?
                            \`<div class="trace-id">Request: \${JSON.stringify(call.requestBody).substring(0, 100)}...</div>\` : ''}
                        \${call.responseBody ?
                            \`<div class="trace-id">Response: \${JSON.stringify(call.responseBody).substring(0, 100)}...</div>\` : ''}
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
