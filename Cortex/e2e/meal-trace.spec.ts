import { test, expect } from '@playwright/test';

test.describe('Meal Trace E2E', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the dashboard
    await page.goto('http://localhost:5173');
    
    // Wait for the app to load
    await page.waitForSelector('[data-testid="dashboard"]', { timeout: 10000 });
  });

  test('should complete full meal trace flow', async ({ page }) => {
    // 1. Navigate to InGress and capture a signal
    await page.click('text=InGress');
    await page.waitForSelector('text=Manual Signal Ingestion');
    
    // Fill in the manual ingest form
    await page.fill('input[placeholder="e.g., manual, test, webhook"]', 'e2e-test');
    await page.fill('input[placeholder="e.g., user_action, system_event"]', 'test_event');
    await page.fill('textarea[placeholder="{\\"key\\": \\"value\\"}"]', '{"test": "data"}');
    
    // Submit the form
    await page.click('text=Capture Signal');
    
    // Wait for success message
    await page.waitForSelector('text=Signal captured successfully', { timeout: 5000 });

    // 2. Navigate to InGest and verify processing
    await page.click('text=InGest');
    await page.waitForSelector('text=Queue Status');
    
    // Verify queue status is displayed
    const queueStatus = await page.locator('text=Pending').first();
    await expect(queueStatus).toBeVisible();

    // 3. Navigate to OmegaKG and verify knowledge graph
    await page.click('text=OmegaKG');
    await page.waitForSelector('text=Semantic Search');
    
    // Perform a search
    await page.fill('input[placeholder="Search knowledge graph..."]', 'test');
    await page.click('text=Search');
    
    // Wait for search results
    await page.waitForSelector('text=results', { timeout: 5000 });

    // 4. Navigate to Telemetry and verify meal trace
    await page.click('text=Telemetry');
    await page.waitForSelector('text=Meal Trace Visualization');
    
    // Verify meal trace stages are displayed
    await expect(page.locator('text=Signal Capture')).toBeVisible();
    await expect(page.locator('text=Raw Lake Storage')).toBeVisible();
    await expect(page.locator('text=SimpleMem Processing')).toBeVisible();
  });

  test('should display service health correctly', async ({ page }) => {
    // Navigate to telemetry page
    await page.click('text=Telemetry');
    await page.waitForSelector('text=Service Health Matrix');
    
    // Verify all services are displayed
    await expect(page.locator('text=InGress')).toBeVisible();
    await expect(page.locator('text=InGest')).toBeVisible();
    await expect(page.locator('text=OmegaKG')).toBeVisible();
    await expect(page.locator('text=memOS')).toBeVisible();
    
    // Verify health indicators are present
    const healthCards = await page.locator('[class*="rounded-lg"]').count();
    expect(healthCards).toBeGreaterThanOrEqual(4);
  });

  test('should handle errors gracefully', async ({ page }) => {
    // Navigate to InGress
    await page.click('text=InGress');
    
    // Try to submit invalid JSON
    await page.fill('textarea[placeholder="{\\"key\\": \\"value\\"}"]', 'invalid json');
    await page.click('text=Capture Signal');
    
    // Verify error message is displayed
    await page.waitForSelector('text=Invalid JSON', { timeout: 5000 });
  });
});
