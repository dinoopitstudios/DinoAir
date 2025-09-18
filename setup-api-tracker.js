#!/usr/bin/env node

/**
 * DinoAir API Tracker Setup Script
 * Installs dependencies and sets up the live API tracking system
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

class TrackerSetup {
  constructor() {
    this.rootDir = process.cwd();
    this.trackerDir = path.join(this.rootDir, 'api-tracker');
  }

  async setup() {
    console.log('🚀 Setting up DinoAir API Tracker...\n');

    try {
      // Create tracker directory
      this.createTrackerDirectory();

      // Install dependencies
      await this.installDependencies();

      // Create configuration files
      this.createConfigFiles();

      // Create start scripts
      this.createStartScripts();

      console.log('\n✅ Setup complete!');
      console.log('\n📋 To start tracking:');
      console.log('   1. Start your DinoAir backend: npm run api');
      console.log('   2. Start your DinoAir frontend: npm run dev');
      console.log('   3. Start the API tracker: npm run track:api');
      console.log('   4. Open the live dashboard: http://localhost:3001');
      console.log('   5. Interact with DinoAir GUI to see live API tracking!');
    } catch (error) {
      console.error('❌ Setup failed:', error.message);
      process.exit(1);
    }
  }

  createTrackerDirectory() {
    console.log('📁 Creating tracker directory...');

    if (!fs.existsSync(this.trackerDir)) {
      fs.mkdirSync(this.trackerDir, { recursive: true });
    }

    // Create subdirectories
    const subdirs = ['logs', 'reports', 'config'];
    subdirs.forEach(dir => {
      const dirPath = path.join(this.trackerDir, dir);
      if (!fs.existsSync(dirPath)) {
        fs.mkdirSync(dirPath);
      }
    });

    console.log('✅ Tracker directory created');
  }

  async installDependencies() {
    console.log('📦 Installing dependencies...');

    try {
      // Check if we're in a Node.js project
      const packageJsonPath = path.join(this.rootDir, 'package.json');
      let packageJson = {};

      if (fs.existsSync(packageJsonPath)) {
        packageJson = JSON.parse(fs.readFileSync(packageJsonPath, 'utf8'));
      }

      // Add tracker dependencies
      if (!packageJson.devDependencies) {
        packageJson.devDependencies = {};
      }

      packageJson.devDependencies.playwright = '^1.40.0';
      packageJson.devDependencies.express = '^4.18.0';
      packageJson.devDependencies['@playwright/test'] = '^1.40.0';

      // Add tracker scripts
      if (!packageJson.scripts) {
        packageJson.scripts = {};
      }

      packageJson.scripts['track:api'] = 'node api-tracker/tracker.js';
      packageJson.scripts['track:setup'] = 'node api-tracker/setup.js';
      packageJson.scripts['track:dashboard'] = 'node api-tracker/dashboard-server.js';

      // Write updated package.json
      fs.writeFileSync(packageJsonPath, JSON.stringify(packageJson, null, 2));

      // Install dependencies
      console.log('   Installing Playwright and Express...');
      execSync('npm install', { stdio: 'inherit' });

      // Install Playwright browsers
      console.log('   Installing Playwright browsers...');
      execSync('npx playwright install chromium', { stdio: 'inherit' });

      console.log('✅ Dependencies installed');
    } catch (error) {
      throw new Error(`Failed to install dependencies: ${error.message}`);
    }
  }

  createConfigFiles() {
    console.log('⚙️ Creating configuration files...');

    // Create tracker configuration
    const trackerConfig = {
      frontend: {
        url: 'http://localhost:5173',
        waitForLoadState: 'networkidle',
      },
      backend: {
        url: 'http://127.0.0.1:24801',
        healthEndpoint: '/health',
      },
      dashboard: {
        port: 3001,
        updateInterval: 1000,
      },
      tracking: {
        captureRequests: true,
        captureResponses: true,
        captureHeaders: true,
        captureBodies: true,
        maxLogSize: 1000,
      },
      browser: {
        headless: false,
        devtools: true,
        recordVideo: true,
      },
    };

    fs.writeFileSync(
      path.join(this.trackerDir, 'config', 'tracker-config.json'),
      JSON.stringify(trackerConfig, null, 2)
    );

    // Create Playwright configuration
    const playwrightConfig = `
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './api-tracker/tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    video: 'retain-on-failure',
    screenshot: 'only-on-failure'
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    }
  ],
  webServer: [
    {
      command: 'npm run dev',
      port: 5173,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'npm run api',
      port: 24801,
      reuseExistingServer: !process.env.CI,
    }
  ],
});
        `;

    fs.writeFileSync(
      path.join(this.rootDir, 'playwright.config.api-tracker.ts'),
      playwrightConfig.trim()
    );

    console.log('✅ Configuration files created');
  }

  createStartScripts() {
    console.log('📝 Creating start scripts...');

    // Move main tracker file to tracker directory
    const trackerSource = path.join(this.rootDir, 'api-tracker.js');
    const trackerDest = path.join(this.trackerDir, 'tracker.js');

    if (fs.existsSync(trackerSource)) {
      fs.copyFileSync(trackerSource, trackerDest);
    }

    // Create dashboard server
    const dashboardServer = `
const express = require('express');
const path = require('path');
const fs = require('fs');

class DashboardServer {
    constructor() {
        this.app = express();
        this.port = 3001;
        this.trackerData = {
            calls: [],
            sessions: [],
            stats: {}
        };
    }

    start() {
        // Serve static files
        this.app.use('/static', express.static(path.join(__dirname, '../')));

        // API endpoints
        this.app.get('/api/calls', (req, res) => {
            res.json({
                calls: this.trackerData.calls.slice(-100), // Last 100 calls
                timestamp: new Date().toISOString()
            });
        });

        this.app.get('/api/stats', (req, res) => {
            res.json(this.calculateStats());
        });

        // Dashboard HTML
        this.app.get('/', (req, res) => {
            const dashboardPath = path.join(__dirname, '../api-flow-dashboard.html');
            if (fs.existsSync(dashboardPath)) {
                res.sendFile(dashboardPath);
            } else {
                res.send('Dashboard not found. Please run setup again.');
            }
        });

        this.app.listen(this.port, () => {
            console.log(\`🌐 Dashboard server running at http://localhost:\${this.port}\`);
        });
    }

    calculateStats() {
        const calls = this.trackerData.calls;
        const requests = calls.filter(c => c.type === 'request');
        const responses = calls.filter(c => c.type === 'response');
        const errors = calls.filter(c => c.type === 'failed' ||
            (c.type === 'response' && c.status >= 400));

        return {
            totalRequests: requests.length,
            totalResponses: responses.length,
            errorCount: errors.length,
            successRate: responses.length > 0 ?
                ((responses.length - errors.length) / responses.length * 100).toFixed(1) : 100,
            avgResponseTime: this.calculateAvgResponseTime(responses)
        };
    }

    calculateAvgResponseTime(responses) {
        if (responses.length === 0) return 0;

        const times = responses
            .filter(r => r.timing && r.timing.completed && r.timing.started)
            .map(r => r.timing.completed - r.timing.started);

        return times.length > 0 ?
            Math.round(times.reduce((a, b) => a + b, 0) / times.length) : 0;
    }

    updateData(newData) {
        this.trackerData = { ...this.trackerData, ...newData };
    }
}

if (require.main === module) {
    const server = new DashboardServer();
    server.start();
}

module.exports = DashboardServer;
        `;

    fs.writeFileSync(path.join(this.trackerDir, 'dashboard-server.js'), dashboardServer.trim());

    // Create main run script
    const runScript = `
#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');

console.log('🚀 Starting DinoAir API Tracker...');

// Start dashboard server
console.log('📊 Starting dashboard server...');
const dashboard = spawn('node', [path.join(__dirname, 'dashboard-server.js')], {
    stdio: 'inherit'
});

// Start main tracker
console.log('🔍 Starting API tracker...');
const tracker = spawn('node', [path.join(__dirname, 'tracker.js')], {
    stdio: 'inherit'
});

// Handle shutdown
process.on('SIGINT', () => {
    console.log('\\n🛑 Shutting down tracker...');
    dashboard.kill();
    tracker.kill();
    process.exit(0);
});

dashboard.on('error', (err) => {
    console.error('❌ Dashboard server error:', err);
});

tracker.on('error', (err) => {
    console.error('❌ Tracker error:', err);
});
        `;

    fs.writeFileSync(path.join(this.trackerDir, 'run.js'), runScript.trim());

    // Make scripts executable
    try {
      fs.chmodSync(path.join(this.trackerDir, 'run.js'), '755');
    } catch (e) {
      // Windows doesn't support chmod
    }

    console.log('✅ Start scripts created');
  }
}

// Run setup if called directly
if (require.main === module) {
  const setup = new TrackerSetup();
  setup.setup();
}

module.exports = TrackerSetup;
