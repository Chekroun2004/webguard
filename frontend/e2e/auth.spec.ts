import { test, expect } from "@playwright/test";

const uniqueEmail = () => `e2e-${Date.now()}-${Math.floor(Math.random() * 1000)}@gmail.com`;
const PASSWORD = "Test1234!";

test.describe("Authentication", () => {
  test("register a new user and land on the dashboard", async ({ page }) => {
    const email = uniqueEmail();

    await page.goto("/register");
    await page.getByLabel(/email/i).fill(email);
    await page.getByLabel(/nom complet/i).fill("E2E User");
    await page.getByLabel(/mot de passe/i).fill(PASSWORD);
    await page.getByRole("button", { name: /créer un compte|s'inscrire/i }).click();

    await expect(page).toHaveURL(/\/dashboard/, { timeout: 15_000 });
    await expect(page.getByText(email)).toBeVisible();
  });

  test("logout then login again", async ({ page }) => {
    const email = uniqueEmail();

    // Register
    await page.goto("/register");
    await page.getByLabel(/email/i).fill(email);
    await page.getByLabel(/nom complet/i).fill("E2E User");
    await page.getByLabel(/mot de passe/i).fill(PASSWORD);
    await page.getByRole("button", { name: /créer un compte|s'inscrire/i }).click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 15_000 });

    // Logout
    await page.getByRole("button", { name: /déconnexion|logout/i }).click();
    await expect(page).toHaveURL(/\/login/);

    // Login
    await page.getByLabel(/email/i).fill(email);
    await page.getByLabel(/mot de passe/i).fill(PASSWORD);
    await page.getByRole("button", { name: /se connecter|connexion/i }).click();
    await expect(page).toHaveURL(/\/dashboard/, { timeout: 15_000 });
  });
});
