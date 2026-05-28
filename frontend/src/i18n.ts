import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import fr from "./locales/fr/translation.json";
import en from "./locales/en/translation.json";

const savedLang = (() => {
  try {
    return localStorage.getItem("lang") ?? "fr";
  } catch {
    return "fr";
  }
})();

i18n.use(initReactI18next).init({
  resources: {
    fr: { translation: fr },
    en: { translation: en },
  },
  lng: savedLang,
  fallbackLng: "fr",
  interpolation: { escapeValue: false },
  react: { useSuspense: false },
});

i18n.on("languageChanged", (lng) => {
  try {
    localStorage.setItem("lang", lng);
  } catch { /* ignore */ }
});

export default i18n;
