import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ShieldAlert } from "lucide-react";
import { useTranslation } from "react-i18next";

import { useLogin, useRegister } from "@/hooks/useAuth";
import { ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

export function RegisterPage() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const register = useRegister();
  const login = useLogin();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await register.mutateAsync({ email, password, full_name: fullName || undefined });
      await login.mutateAsync({ email, password });
      void navigate("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : t("common.unexpected_error"));
    }
  };

  const isPending = register.isPending || login.isPending;
  const { t } = useTranslation();

  return (
    <div className="min-h-screen bg-background flex">
      {/* Left panel — animated mesh background */}
      <div
        className="hidden lg:flex lg:w-1/2 relative overflow-hidden flex-col justify-between p-12 text-white border-r border-white/[0.06]"
        style={{ background: "hsl(240 20% 4%)" }}
      >
        {/* Animated glow orbs */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="animate-mesh-2 absolute -top-32 right-0 h-[500px] w-[500px] rounded-full bg-violet-600/25 blur-[100px]" />
          <div className="animate-mesh-1 absolute -bottom-32 -left-32 h-[400px] w-[400px] rounded-full bg-indigo-600/20 blur-[80px]" />
          <div className="animate-mesh-3 absolute top-1/3 left-1/2 h-[300px] w-[300px] rounded-full bg-violet-500/10 blur-[60px]" />
        </div>

        <div className="relative z-10 flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-white/10 backdrop-blur-sm border border-white/20 flex items-center justify-center">
            <ShieldAlert className="h-5 w-5 text-white" />
          </div>
          <span className="font-display font-bold text-xl tracking-tight">WebGuard</span>
        </div>

        <div className="relative z-10 space-y-5">
          <h2 className="font-display text-4xl font-bold leading-tight">
            {t("register.hero_title")}
          </h2>
          <p className="text-white/60 text-sm leading-relaxed max-w-sm">
            {t("register.hero_body")}
          </p>
          <div className="flex gap-6 pt-2">
            <div>
              <p className="text-2xl font-display font-bold">{t("register.stat_free")}</p>
              <p className="text-white/50 text-xs mt-0.5">{t("register.stat_free_label")}</p>
            </div>
            <div className="w-px bg-white/10" />
            <div>
              <p className="text-2xl font-display font-bold">{t("register.stat_time")}</p>
              <p className="text-white/50 text-xs mt-0.5">{t("register.stat_time_label")}</p>
            </div>
            <div className="w-px bg-white/10" />
            <div>
              <p className="text-2xl font-display font-bold">{t("register.stat_scans")}</p>
              <p className="text-white/50 text-xs mt-0.5">{t("register.stat_scans_label")}</p>
            </div>
          </div>
        </div>

        <p className="relative z-10 text-white/30 text-xs">
          WebGuard — Portfolio Master IGOV · FSR-UM5 Rabat
        </p>
      </div>

      {/* Right panel — form */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-md space-y-6">
          {/* Mobile brand */}
          <div className="flex items-center gap-2 lg:hidden">
            <div className="w-7 h-7 rounded-lg bg-gradient-brand flex items-center justify-center">
              <span className="text-white text-xs font-bold">W</span>
            </div>
            <span className="font-bold text-lg">
              <span className="text-[#6366f1]">Web</span>Guard
            </span>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>{t("register.title")}</CardTitle>
              <CardDescription>{t("register.description")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {error && (
                <p className="text-sm text-destructive rounded-lg bg-destructive/10 px-3 py-2 border border-destructive/20">
                  {error}
                </p>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-1.5">
                  <label htmlFor="fullName" className="text-sm font-medium">
                    {t("register.full_name")}{" "}
                    <span className="text-muted-foreground font-normal">{t("register.full_name_optional")}</span>
                  </label>
                  <Input
                    id="fullName"
                    type="text"
                    autoComplete="name"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                  />
                </div>

                <div className="space-y-1.5">
                  <label htmlFor="email" className="text-sm font-medium">
                    {t("register.email")}
                  </label>
                  <Input
                    id="email"
                    type="email"
                    required
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>

                <div className="space-y-1.5">
                  <label htmlFor="password" className="text-sm font-medium">
                    {t("register.password")}{" "}
                    <span className="text-muted-foreground font-normal text-xs">
                      {t("register.password_hint")}
                    </span>
                  </label>
                  <Input
                    id="password"
                    type="password"
                    required
                    minLength={8}
                    autoComplete="new-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </div>

                <Button type="submit" disabled={isPending} className="w-full" size="lg">
                  {isPending ? t("register.submitting") : t("register.submit")}
                </Button>
              </form>

              <p className="text-sm text-muted-foreground text-center">
                {t("register.have_account")}{" "}
                <Link
                  to="/login"
                  className="font-medium text-primary hover:underline underline-offset-4"
                >
                  {t("register.login_link")}
                </Link>
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
