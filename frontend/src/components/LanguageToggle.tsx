import { useTranslation } from "react-i18next";

export function LanguageToggle() {
  const { i18n } = useTranslation();
  const isFr = i18n.language === "fr";

  return (
    <button
      onClick={() => i18n.changeLanguage(isFr ? "en" : "fr")}
      title={isFr ? "Switch to English" : "Passer en français"}
      className="flex items-center justify-center h-7 w-14 rounded-md text-xs font-semibold border border-input bg-background hover:bg-white/5 transition-colors text-muted-foreground hover:text-foreground"
    >
      {isFr ? "FR" : "EN"}
      <span className="text-muted-foreground/40 mx-0.5">|</span>
      {isFr ? "EN" : "FR"}
    </button>
  );
}
