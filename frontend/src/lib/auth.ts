/**
 * Token storage helpers.
 * Both tokens are stored in localStorage for portfolio-demo simplicity.
 * Production would use an httpOnly cookie for the refresh token.
 */
const ACCESS_KEY = "wg_access";
const REFRESH_KEY = "wg_refresh";

function persist(access: string, refresh: string): void {
  localStorage.setItem(ACCESS_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export const tokenStorage = {
  getAccess: (): string | null => localStorage.getItem(ACCESS_KEY),
  getRefresh: (): string | null => localStorage.getItem(REFRESH_KEY),
  set: persist,
  setTokens: persist,
  clear: (): void => {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};
