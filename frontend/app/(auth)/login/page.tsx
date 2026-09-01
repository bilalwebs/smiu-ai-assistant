"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/store";
import { api, ApiError } from "@/lib/api";
import Image from "next/image";
import {
  Eye,
  EyeOff,
  Loader2,
  Mail,
  Lock,
  ArrowRight,
  Shield,
  Chrome,
  MailCheck,
  Zap,
} from "lucide-react";
import AuthPromoPanel from "@/components/auth/AuthPromoPanel";
import MicrosoftIcon from "@/components/auth/MicrosoftIcon";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuthStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");
  const [forgotLoading, setForgotLoading] = useState(false);
  const [forgotSuccess, setForgotSuccess] = useState("");
  const [forgotError, setForgotError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      await login(email, password, rememberMe);
      router.push("/dashboard");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Login failed. Please try again."
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setForgotError("");
    setForgotSuccess("");
    setForgotLoading(true);
    try {
      const result = await api.auth.forgotPassword(forgotEmail);
      setForgotSuccess(
        result.message ||
          "If that email address exists, a password reset link has been sent."
      );
    } catch (err) {
      if (err instanceof ApiError) {
        setForgotError(err.message);
      } else {
        setForgotError("Something went wrong. Please try again.");
      }
    } finally {
      setForgotLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen">
      <AuthPromoPanel
        headingDark="Welcome"
        headingBlue="Back!"
        description="Login to your account and continue your journey with AI-powered university services."
        features={[
          {
            icon: <Shield className="h-5 w-5" />,
            title: "Secure & Reliable",
            description:
              "Your data is protected with enterprise-grade security.",
          },
          {
            icon: <Zap className="h-5 w-5" />,
            title: "Smart & Efficient",
            description:
              "AI agents work 24/7 to make your academic journey easier.",
          },
          {
            icon: <MailCheck className="h-5 w-5" />,
            title: "Always Here for You",
            description: "Get instant assistance anytime, anywhere.",
          },
        ]}
      />

      {/* Login form */}
      <div className="flex flex-1 items-center justify-center px-6 py-12">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <div className="relative h-10 w-10 flex-shrink-0">
              <Image
                src="/assets/logo.png"
                alt="SMIU Logo"
                fill
                className="object-contain"
                sizes="40px"
                priority
              />
            </div>
            <span className="text-xl font-bold text-text-primary">SMIU AI</span>
          </div>

          {/* Header */}
          <h2 className="text-2xl font-bold text-text-primary">
            Login to Your Account
          </h2>
          <p className="mt-1 text-sm text-text-secondary">
            Enter your credentials to access your dashboard
          </p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            {error && (
              <div className="rounded-lg border border-danger/20 bg-danger/5 px-4 py-3 text-sm text-danger">
                {error}
              </div>
            )}

            {/* Email */}
            <div>
              <label
                htmlFor="email"
                className="mb-1.5 block text-sm font-medium text-text-primary"
              >
                Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="h-11 w-full rounded-lg border border-border bg-surface pl-10 pr-4 text-sm text-text-primary placeholder-text-muted transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                  placeholder="Enter your email"
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <div className="mb-1.5 flex items-center justify-between">
                <label
                  htmlFor="password"
                  className="text-sm font-medium text-text-primary"
                >
                  Password
                </label>
                <button
                  type="button"
                  onClick={() => {
                    setShowForgotPassword(true);
                    setForgotEmail(email);
                    setForgotError("");
                    setForgotSuccess("");
                  }}
                  className="text-xs font-medium text-primary hover:text-primary-hover"
                >
                  Forgot Password?
                </button>
              </div>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="h-11 w-full rounded-lg border border-border bg-surface pl-10 pr-11 text-sm text-text-primary placeholder-text-muted transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                  placeholder="Enter your password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            {/* Remember me */}
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="h-4 w-4 rounded border-border text-primary focus:ring-primary/20"
                />
                <span className="text-sm text-text-secondary">Remember me</span>
              </label>
              <span className="text-sm text-text-muted">Keep me signed in</span>
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={isLoading}
              className="flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-primary font-medium text-white transition-colors hover:bg-primary-hover disabled:opacity-50"
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  Login
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </form>

          {/* Divider */}
          <div className="my-6 flex items-center gap-3">
            <div className="h-px flex-1 bg-border" />
            <span className="text-xs text-text-muted">or continue with</span>
            <div className="h-px flex-1 bg-border" />
          </div>

          {/* Social buttons */}
          <div className="space-y-3">
            <button
              type="button"
              disabled
              className="flex h-11 w-full items-center justify-center gap-3 rounded-lg border border-border bg-surface text-sm font-medium text-text-muted transition-colors cursor-not-allowed opacity-60"
              title="Google OAuth not yet configured on the backend"
            >
              <Chrome className="h-5 w-5" />
              Continue with Google
            </button>
            <button
              type="button"
              disabled
              className="flex h-11 w-full items-center justify-center gap-3 rounded-lg border border-border bg-surface text-sm font-medium text-text-muted transition-colors cursor-not-allowed opacity-60"
              title="Microsoft OAuth not yet configured on the backend"
            >
              <MicrosoftIcon className="h-5 w-5" />
              Continue with Microsoft
            </button>
            <button
              type="button"
              disabled
              className="flex h-11 w-full items-center justify-center gap-3 rounded-lg border border-border bg-surface text-sm font-medium text-text-muted transition-colors cursor-not-allowed opacity-60"
              title="SMIU Email verification not yet configured on the backend"
            >
              <Mail className="h-5 w-5" />
              Continue with SMIU Email
            </button>
          </div>

          {/* Register link */}
          <p className="mt-6 text-center text-sm text-text-secondary">
            Don&apos;t have an account?{" "}
            <a
              href="/register"
              className="font-medium text-primary hover:text-primary-hover"
            >
              Sign up here
            </a>
          </p>

          {/* Terms */}
          <div className="mt-6 flex items-start justify-center gap-2 text-center">
            <Shield className="mt-0.5 h-4 w-4 shrink-0 text-text-muted" />
            <p className="text-xs text-text-muted">
              By logging in, you agree to our{" "}
              <a href="#" className="text-primary hover:underline">
                Terms of Service
              </a>{" "}
              and{" "}
              <a href="#" className="text-primary hover:underline">
                Privacy Policy
              </a>
              .
            </p>
          </div>
        </div>
      </div>

      {/* Forgot Password Modal */}
      {showForgotPassword && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4">
          <div className="w-full max-w-md rounded-xl bg-surface p-6 shadow-lg">
            <h3 className="text-lg font-bold text-text-primary">
              Reset Your Password
            </h3>
            <p className="mt-1 text-sm text-text-secondary">
              Enter your email and we&apos;ll send you a reset link.
            </p>

            {forgotSuccess ? (
              <div className="mt-4 rounded-lg border border-success/20 bg-success/5 px-4 py-3 text-sm text-success">
                {forgotSuccess}
              </div>
            ) : (
              <form onSubmit={handleForgotPassword} className="mt-4 space-y-4">
                {forgotError && (
                  <div className="rounded-lg border border-danger/20 bg-danger/5 px-4 py-3 text-sm text-danger">
                    {forgotError}
                  </div>
                )}
                <div>
                  <label
                    htmlFor="forgotEmail"
                    className="mb-1.5 block text-sm font-medium text-text-primary"
                  >
                    Email Address
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
                    <input
                      id="forgotEmail"
                      type="email"
                      value={forgotEmail}
                      onChange={(e) => setForgotEmail(e.target.value)}
                      required
                      className="h-11 w-full rounded-lg border border-border bg-background pl-10 pr-4 text-sm text-text-primary placeholder-text-muted focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                      placeholder="Enter your email"
                    />
                  </div>
                </div>
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => setShowForgotPassword(false)}
                    className="flex h-11 flex-1 items-center justify-center rounded-lg border border-border font-medium text-text-secondary transition-colors hover:bg-muted"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={forgotLoading}
                    className="flex h-11 flex-1 items-center justify-center gap-2 rounded-lg bg-primary font-medium text-white transition-colors hover:bg-primary-hover disabled:opacity-50"
                  >
                    {forgotLoading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      "Send Reset Link"
                    )}
                  </button>
                </div>
              </form>
            )}

            {forgotSuccess && (
              <button
                type="button"
                onClick={() => setShowForgotPassword(false)}
                className="mt-4 flex h-11 w-full items-center justify-center rounded-lg border border-border font-medium text-text-secondary transition-colors hover:bg-muted"
              >
                Close
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
