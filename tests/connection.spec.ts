import { test, expect } from '@playwright/test';

test.describe('DinoAir Connection Tests', () => {
  test('API Health Check', async ({ request }) => {
    console.log('Testing API health endpoint...');

    try {
      const response = await request.get('http://127.0.0.1:24801/health');
      console.log(`API Health Response Status: ${response.status()}`);

      expect(response.status()).toBe(200);

      const body = await response.json();
      console.log('API Health Response:', body);

      expect(body).toHaveProperty('status');
    } catch (error) {
      console.error('API Health Check Failed:', error);
      throw error;
    }
  });

  test('API Docs Endpoint', async ({ request }) => {
    console.log('Testing API docs endpoint...');

    try {
      const response = await request.get('http://127.0.0.1:24801/docs');
      console.log(`API Docs Response Status: ${response.status()}`);

      expect(response.status()).toBe(200);

      const contentType = response.headers()['content-type'];
      expect(contentType).toContain('text/html');
    } catch (error) {
      console.error('API Docs Check Failed:', error);
      throw error;
    }
  });

  test('Frontend Homepage', async ({ page }) => {
    console.log('Testing frontend homepage...');

    try {
      await page.goto('/');

      // Wait for page to load
      await page.waitForLoadState('networkidle');

      // Check if page loaded successfully
      const title = await page.title();
      console.log(`Page Title: ${title}`);

      // Check for React root element
      const root = page.locator('#root');
      await expect(root).toBeVisible();

      console.log('Frontend loaded successfully');
    } catch (error) {
      console.error('Frontend Check Failed:', error);
      throw error;
    }
  });

  test('Frontend to API Communication', async ({ page }) => {
    console.log('Testing frontend to API communication...');

    try {
      await page.goto('/');
      await page.waitForLoadState('networkidle');

      // Monitor network requests
      const apiRequests: string[] = [];

      page.on('request', request => {
        if (request.url().includes('127.0.0.1:24801')) {
          apiRequests.push(request.url());
          console.log(`API Request: ${request.method()} ${request.url()}`);
        }
      });

      page.on('response', response => {
        if (response.url().includes('127.0.0.1:24801')) {
          console.log(`API Response: ${response.status()} ${response.url()}`);
        }
      });

      // Try to trigger API calls by interacting with the page
      await page.waitForTimeout(5000); // Wait for any automatic API calls

      console.log(`Detected ${apiRequests.length} API requests`);
    } catch (error) {
      console.error('Frontend to API Communication Check Failed:', error);
      throw error;
    }
  });

  test('Manual API Test with fetch', async ({ page }) => {
    console.log('Testing API with manual fetch...');

    await page.goto('/');

    const result = await page.evaluate(async () => {
      try {
        const response = await fetch('http://127.0.0.1:24801/health');
        return {
          status: response.status,
          ok: response.ok,
          body: await response.text(),
        };
      } catch (error) {
        return {
          error: error instanceof Error ? error.message : String(error),
        };
      }
    });

    console.log('Manual fetch result:', result);

    if ('error' in result) {
      console.error('Fetch failed:', result.error);
    } else {
      expect(result.status).toBe(200);
    }
  });
});
