import { test, expect } from "@playwright/test";

const uniqueEmail = () => `e2e-scan-${Date.now()}-${Math.floor(Math.random() * 1000)}@gmail.com`;
const PASSWORD = "Test1234!";

test.describe("Scan flow", () => {
  test("create a scan and see findings in the report", async ({ page }) => {
    const email = uniqueEmail();

    // Register & arrive on dashboard
    await page.goto("/register");
    await page.getByLabel(/email/i).fill(email);
    await page.getByLabel(/nom complet/i).fill("E2E User");
    await page.getByLabel(/mot de passe/i).fill(PASSWORD);
    await page.getByRole("button", { name: /créer un compte|s'inscrire/i }).click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 15_000 });

    // Launch a scan
    await page.getByPlaceholder(/https?:\/\//i).fill("https://example.com");
    await page.getByRole("button", { name: /lancer|scanner/i }).click();

    // Wait for the scan card to show "completed"
    await expect(page.getByText(/completed/i).first()).toBeVisible({ timeout: 90_000 });

    // Navigate to the scan detail page via the "Rapport" link
    await page.getByRole("link", { name: /rapport/i }).first().click();
    await expect(page).toHaveURL(/\/scans\/\d+/);

    // The findings list should be visible
    await expect(page.locator("text=/résultat\\(s\\)/i")).toBeVisible();

    // Severity chart appears for example.com (it has missing headers)
    await expect(page.getByText(/répartition par sévérité/i)).toBeVisible();
  });
});
