import { test, expect } from '@playwright/test';

test.describe('Server Status Diagnostics', () => {
  test('Check if servers are accessible', async ({ request }) => {
    console.log('=== Server Diagnostic Test ===');

    // Test API server
    console.log('Testing API server on http://127.0.0.1:24801...');
    try {
      const apiResponse = await request.get('http://127.0.0.1:24801/health', {
        timeout: 5000,
      });
      console.log(`✅ API Server Status: ${apiResponse.status()}`);
    } catch (error) {
      console.log(`❌ API Server Error: ${error}`);
    }

    // Test frontend server
    console.log('Testing frontend server on http://localhost:5173...');
    try {
      const frontendResponse = await request.get('http://localhost:5173', {
        timeout: 5000,
      });
      console.log(`✅ Frontend Server Status: ${frontendResponse.status()}`);
    } catch (error) {
      console.log(`❌ Frontend Server Error: ${error}`);
    }

    // Test if ports are actually listening
    console.log('Checking port status...');
  });
});
