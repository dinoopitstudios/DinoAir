/**
 * Interactive GUI Demo for DinoAir API Tracker
 * This script will automatically interact with the DinoAir frontend
 * and show live API calls being captured
 */

const express = require('express');
const { chromium } = require('playwright');

class InteractiveGUIDemo {
  constructor() {
    this.calls = [];
    this.dashboardPort = 3003;
    this.browser = null;
    this.page = null;
    this.demoSteps = [
      { action: 'navigate', target: 'Home', description: '🏠 Navigate to Home page' },
      { action: 'click', target: 'Chat', description: '💬 Click on Chat navigation' },
      { action: 'click', target: 'Projects', description: '📁 Click on Projects navigation' },
      { action: 'click', target: 'Notes', description: '📝 Click on Notes navigation' },
      { action: 'click', target: 'Files', description: '📂 Click on Files navigation' },
      { action: 'refresh', description: '🔄 Refresh page to trigger API calls' },
    ];
    this.currentStep = 0;
  }

  async startDashboard() {
    const app = express();

    app.get('/', (req, res) => {
      res.send(this.generateInteractiveDashboard());
    });

    app.get('/api/calls', (req, res) => {
      res.json({
        calls: this.calls.slice(-30),
        total: this.calls.length,
        timestamp: new Date().toISOString(),
        currentStep: this.currentStep,
        totalSteps: this.demoSteps.length,
      });
    });

    app.post('/api/demo/next', async (req, res) => {
      try {
        const result = await this.performNextDemoStep();
        res.json(result);
      } catch (error) {
        res.status(500).json({
          success: false,
          error: error.message,
        });
      }
    });

    app.listen(this.dashboardPort, () => {
      console.log(`🎮 Interactive GUI Demo Dashboard: http://localhost:${this.dashboardPort}`);
    });
  }

  async startDemo() {
    console.log('🎯 Starting Interactive GUI Demo...');

    await this.startDashboard();

    try {
      this.browser = await chromium.launch({
        headless: false,
        devtools: false,
      });

      const context = await this.browser.newContext();
      this.page = await context.newPage();

      this.setupNetworkMonitoring();

      console.log('🌐 Navigating to DinoAir frontend...');
      await this.page.goto('http://localhost:5173');

      console.log('✅ Demo ready!');
      console.log('🎮 Dashboard: http://localhost:3003');
      console.log('👆 Use the dashboard to trigger automated GUI interactions');

      // Start automated demo after a short delay
      setTimeout(() => {
        this.startAutomatedDemo();
      }, 3000);
    } catch (error) {
      console.error('❌ Error starting demo:', error);
    }
  }

  setupNetworkMonitoring() {
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
  }

  async startAutomatedDemo() {
    console.log('🚀 Starting automated GUI interactions...');

    for (let i = 0; i < this.demoSteps.length; i++) {
      const step = this.demoSteps[i];
      this.currentStep = i + 1;

      console.log(`\n🎬 Step ${this.currentStep}/${this.demoSteps.length}: ${step.description}`);

      try {
        await this.performGUIAction(step);
        await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2 seconds between actions
      } catch (error) {
        console.error(`❌ Error in step ${this.currentStep}:`, error.message);
      }
    }

    console.log('\n🎉 Automated demo completed!');
    console.log('🎮 Continue using the interactive dashboard for more actions');
  }

  async performNextDemoStep() {
    if (!this.currentStep) {
      this.currentStep = 0;
    }

    if (this.currentStep >= this.demoSteps.length) {
      console.log('🎉 All demo steps completed! Restarting from the beginning...');
      this.currentStep = 0;
    }

    const step = this.demoSteps[this.currentStep];
    console.log(
      `\n🎬 Manual Step ${this.currentStep + 1}/${this.demoSteps.length}: ${step.description}`
    );

    try {
      await this.performGUIAction(step);
      this.currentStep++;
      return {
        success: true,
        step: this.currentStep,
        description: step.description,
        nextStep:
          this.currentStep < this.demoSteps.length
            ? this.demoSteps[this.currentStep].description
            : 'Demo completed - will restart',
      };
    } catch (error) {
      console.error(`❌ Error in manual step ${this.currentStep + 1}:`, error.message);
      return {
        success: false,
        error: error.message,
        step: this.currentStep + 1,
      };
    }
  }

  async performGUIAction(step) {
    switch (step.action) {
      case 'navigate':
        if (step.target === 'Home') {
          await this.page.click('a[href="/"]');
        }
        break;

      case 'click':
        await this.clickNavigation(step.target);
        break;

      case 'refresh':
        await this.page.reload();
        break;
    }
  }

  async clickNavigation(target) {
    try {
      // Try to find navigation links by text content
      const navSelectors = [
        `a:has-text("${target}")`,
        `[aria-label="${target}"]`,
        `[title="${target}"]`,
        `text=${target}`,
      ];

      for (const selector of navSelectors) {
        try {
          await this.page.click(selector, { timeout: 2000 });
          console.log(`✅ Clicked ${target} navigation`);
          return;
        } catch (e) {
          // Try next selector
        }
      }

      console.log(`⚠️ Could not find ${target} navigation element`);
    } catch (error) {
      console.error(`❌ Error clicking ${target}:`, error.message);
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

  generateInteractiveDashboard() {
    return `
<!DOCTYPE html>
<html>
<head>
    <title>🎮 Interactive DinoAir GUI Demo</title>
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
        .demo-controls {
            background: #161b22;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            border: 1px solid #30363d;
        }
        .demo-step {
            background: #21262d;
            padding: 15px;
            border-radius: 8px;
            margin: 10px 0;
            border-left: 4px solid #58a6ff;
        }
        .demo-step.active {
            border-left-color: #238636;
            background: #1a2f1a;
        }
        .demo-step.completed {
            border-left-color: #7d8590;
            opacity: 0.7;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
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
            font-size: 1.5em;
            font-weight: bold;
            color: #58a6ff;
        }
        .call-log {
            background: #161b22;
            border-radius: 10px;
            padding: 20px;
            max-height: 400px;
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
        .btn {
            background: #238636;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            margin: 5px;
            cursor: pointer;
            font-size: 1em;
        }
        .btn:hover {
            background: #2ea043;
        }
        .btn:disabled {
            background: #7d8590;
            cursor: not-allowed;
        }
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #21262d;
            border-radius: 4px;
            overflow: hidden;
            margin: 10px 0;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #238636, #2ea043);
            transition: width 0.3s ease;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎮 Interactive DinoAir GUI Demo</h1>
        <p>Automated GUI interactions with live API tracking</p>
    </div>

    <div class="demo-controls">
        <h3>🎬 Demo Progress</h3>
        <div class="progress-bar">
            <div class="progress-fill" id="progress-fill" style="width: 0%"></div>
        </div>
        <p id="demo-status">Waiting for demo to start...</p>

        <div id="demo-steps">
            <!-- Steps will be populated by JavaScript -->
        </div>

        <button class="btn" onclick="triggerNextStep()" id="next-btn">
            🎯 Trigger Next GUI Action
        </button>
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
            <div class="stat-number" id="current-step">0</div>
            <div>Current Step</div>
        </div>
    </div>

    <div class="call-log">
        <h3>🔴 Live API Calls</h3>
        <div id="call-entries">
            <p style="text-align: center; color: #7d8590; margin: 40px 0;">
                Starting GUI interactions...<br>
                <small>Watch API calls appear as we interact with DinoAir</small>
            </p>
        </div>
    </div>

    <script>
        let lastCallCount = 0;
        const demoSteps = [
            { description: '🏠 Navigate to Home page' },
            { description: '💬 Click on Chat navigation' },
            { description: '📁 Click on Projects navigation' },
            { description: '📝 Click on Notes navigation' },
            { description: '📂 Click on Files navigation' },
            { description: '🔄 Refresh page to trigger API calls' }
        ];

        function updateDashboard() {
            fetch('/api/calls')
                .then(response => response.json())
                .then(data => {
                    updateStats(data);
                    updateCallLog(data.calls);
                    updateDemoProgress(data);
                })
                .catch(error => {
                    console.error('Dashboard update error:', error);
                });
        }

        function updateStats(data) {
            const responses = data.calls.filter(c => c.type === 'response');
            const successResponses = responses.filter(r => r.status >= 200 && r.status < 400);
            const failedCalls = data.calls.filter(c => c.type === 'failed');

            document.getElementById('total-calls').textContent = data.total;
            document.getElementById('success-calls').textContent = successResponses.length;
            document.getElementById('failed-calls').textContent = failedCalls.length;
            document.getElementById('current-step').textContent = data.currentStep || 0;
        }

        function updateDemoProgress(data) {
            const currentStep = data.currentStep || 0;
            const totalSteps = data.totalSteps || demoSteps.length;
            const progress = (currentStep / totalSteps) * 100;

            document.getElementById('progress-fill').style.width = progress + '%';
            document.getElementById('demo-status').textContent =
                currentStep === 0 ? 'Demo starting...' :
                currentStep >= totalSteps ? '🎉 Demo completed!' :
                \`Step \${currentStep}/\${totalSteps}: \${demoSteps[currentStep - 1]?.description || 'In progress...'}\`;

            updateStepsDisplay(currentStep, totalSteps);
        }

        function updateStepsDisplay(currentStep, totalSteps) {
            const stepsContainer = document.getElementById('demo-steps');
            stepsContainer.innerHTML = demoSteps.map((step, index) => {
                const stepNumber = index + 1;
                let className = 'demo-step';
                if (stepNumber < currentStep) className += ' completed';
                if (stepNumber === currentStep) className += ' active';

                return \`
                    <div class="\${className}">
                        <strong>Step \${stepNumber}:</strong> \${step.description}
                    </div>
                \`;
            }).join('');
        }

        function updateCallLog(calls) {
            const callEntries = document.getElementById('call-entries');

            if (calls.length === 0) {
                callEntries.innerHTML = \`
                    <p style="text-align: center; color: #7d8590; margin: 40px 0;">
                        Starting GUI interactions...<br>
                        <small>Watch API calls appear as we interact with DinoAir</small>
                    </p>
                \`;
                return;
            }

            const recentCalls = calls.slice(-15).reverse();

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
                        <div style="float: right; color: #7d8590; font-size: 0.8em;">\${timestamp}</div>
                        <div>
                            \${emoji} <strong>\${call.method}</strong> \${call.path}\${statusText}
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

        function triggerNextStep() {
            fetch('/api/demo/next', { method: 'POST' })
                .then(response => response.json())
                .then(data => {
                    console.log('Triggered step:', data.step);
                })
                .catch(error => {
                    console.error('Error triggering step:', error);
                });
        }

        // Update every second
        setInterval(updateDashboard, 1000);
        updateDashboard();
        updateStepsDisplay(0, demoSteps.length);
    </script>
</body>
</html>
    `;
  }

  async stop() {
    if (this.browser) {
      await this.browser.close();
    }
    console.log('🛑 Interactive demo stopped');
  }
}

if (require.main === module) {
  const demo = new InteractiveGUIDemo();
  demo.startDemo();

  process.on('SIGINT', async () => {
    console.log('\n🛑 Shutting down...');
    await demo.stop();
    process.exit(0);
  });
}

module.exports = InteractiveGUIDemo;
