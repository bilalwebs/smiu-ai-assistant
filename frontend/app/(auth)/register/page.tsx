"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/store";
import { api, ApiError } from "@/lib/api";
import type { DepartmentRead } from "@/types/api";
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
  User,
  CreditCard,
  Building2,
  CheckCircle2,
} from "lucide-react";
import AuthPromoPanel from "@/components/auth/AuthPromoPanel";
import MicrosoftIcon from "@/components/auth/MicrosoftIcon";

function validatePassword(pw: string) {
  return {
    length: pw.length >= 8,
    lowercase: /[a-z]/.test(pw),
    uppercase: /[A-Z]/.test(pw),
    numberOrSymbol: /[0-9]/.test(pw) || /[^A-Za-z0-9]/.test(pw),
  };
}

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuthStore();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [studentId, setStudentId] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [agreedToTerms, setAgreedToTerms] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const [departments, setDepartments] = useState<DepartmentRead[]>([]);
  const [departmentsLoading, setDepartmentsLoading] = useState(true);
  const [departmentsError, setDepartmentsError] = useState("");

  useEffect(() => {
    const fetchDepartments = async () => {
      try {
        const data = await api.departments.list();
        setDepartments(data);
      } catch (err) {
        setDepartmentsError(
          err instanceof Error
            ? err.message
            : "Failed to load departments. You can still register without selecting one."
        );
      } finally {
        setDepartmentsLoading(false);
      }
    };
    fetchDepartments();
  }, []);

  const pwRules = validatePassword(password);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!agreedToTerms) {
      setError("You must agree to the Terms of Service and Privacy Policy.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setIsLoading(true);

    try {
      await register({
        email,
        password,
        full_name: fullName,
        enrollment_no: studentId || undefined,
        department_id: departmentId || undefined,
      });
      router.push("/login");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError(
          err instanceof Error
            ? err.message
            : "Registration failed. Please try again."
        );
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen">
      <AuthPromoPanel
        headingDark="Create Your"
        headingBlue="Account"
        description="Join thousands of students using AI to simplify their academic journey."
        features={[
          {
            icon: <CheckCircle2 className="h-5 w-5" />,
            title: "Easy Registration",
            description: "Create your account in just a few steps.",
          },
          {
            icon: <Shield className="h-5 w-5" />,
            title: "Secure & Private",
            description: "Your information is safe with us.",
          },
          {
            icon: <Loader2 className="h-5 w-5" />,
            title: "Get Started Fast",
            description: "Access all features immediately.",
          },
        ]}
      />

      {/* Register form */}
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
            Create Your Account
          </h2>
          <p className="mt-1 text-sm text-text-secondary">
            Fill in your details to get started
          </p>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            {error && (
              <div className="rounded-lg border border-danger/20 bg-danger/5 px-4 py-3 text-sm text-danger">
                {error}
              </div>
            )}

            {/* Full Name */}
            <div>
              <label
                htmlFor="fullName"
                className="mb-1.5 block text-sm font-medium text-text-primary"
              >
                Full Name
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
                <input
                  id="fullName"
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                  className="h-11 w-full rounded-lg border border-border bg-surface pl-10 pr-4 text-sm text-text-primary placeholder-text-muted transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                  placeholder="Enter your full name"
                />
              </div>
            </div>

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

            {/* Student ID */}
            <div>
              <label
                htmlFor="studentId"
                className="mb-1.5 block text-sm font-medium text-text-primary"
              >
                Student ID
              </label>
              <div className="relative">
                <CreditCard className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
                <input
                  id="studentId"
                  type="text"
                  value={studentId}
                  onChange={(e) => setStudentId(e.target.value)}
                  className="h-11 w-full rounded-lg border border-border bg-surface pl-10 pr-4 text-sm text-text-primary placeholder-text-muted transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                  placeholder="Enter your student ID"
                />
              </div>
            </div>

            {/* Department */}
            <div>
              <label
                htmlFor="department"
                className="mb-1.5 block text-sm font-medium text-text-primary"
              >
                Department
              </label>
              <div className="relative">
                <Building2 className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
                <select
                  id="department"
                  value={departmentId}
                  onChange={(e) => setDepartmentId(e.target.value)}
                  disabled={departmentsLoading}
                  className="h-11 w-full appearance-none rounded-lg border border-border bg-surface pl-10 pr-10 text-sm text-text-primary transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-50"
                >
                  <option value="">
                    {departmentsLoading
                      ? "Loading departments..."
                      : "Select your department"}
                  </option>
                  {departments.map((dept) => (
                    <option key={dept.id} value={dept.id}>
                      {dept.name}
                    </option>
                  ))}
                </select>
                <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2">
                  <svg className="h-4 w-4 text-text-muted" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" />
                  </svg>
                </div>
              </div>
              {departmentsError && (
                <p className="mt-1 text-xs text-warning">{departmentsError}</p>
              )}
            </div>
            <div>
              <label
                htmlFor="password"
                className="mb-1.5 block text-sm font-medium text-text-primary"
              >
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="h-11 w-full rounded-lg border border-border bg-surface pl-10 pr-11 text-sm text-text-primary placeholder-text-muted transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                  placeholder="Create a password"
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

            {/* Confirm Password */}
            <div>
              <label
                htmlFor="confirmPassword"
                className="mb-1.5 block text-sm font-medium text-text-primary"
              >
                Confirm Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
                <input
                  id="confirmPassword"
                  type={showConfirmPassword ? "text" : "password"}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  className="h-11 w-full rounded-lg border border-border bg-surface pl-10 pr-11 text-sm text-text-primary placeholder-text-muted transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
                  placeholder="Confirm your password"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary"
                  aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                >
                  {showConfirmPassword ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>

            {/* Password requirements */}
            {password.length > 0 && (
              <div className="rounded-lg border border-border bg-muted/50 p-3">
                <div className="mb-2 text-xs font-medium text-text-secondary">
                  Password must contain:
                </div>
                <div className="grid grid-cols-2 gap-1.5">
                  {([
                    [pwRules.length, "At least 8 characters"],
                    [pwRules.lowercase, "One lowercase letter"],
                    [pwRules.uppercase, "One uppercase letter"],
                    [pwRules.numberOrSymbol, "One number or symbol"],
                  ] as const).map(([met, label]) => (
                    <div key={label} className="flex items-center gap-1.5">
                      <CheckCircle2
                        className={`h-3.5 w-3.5 ${
                          met ? "text-success" : "text-text-muted"
                        }`}
                      />
                      <span
                        className={`text-xs ${
                          met ? "text-success" : "text-text-muted"
                        }`}
                      >
                        {label}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Terms */}
            <label className="flex items-start gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={agreedToTerms}
                onChange={(e) => setAgreedToTerms(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-border text-primary focus:ring-primary/20"
              />
              <span className="text-sm text-text-secondary">
                I agree to the{" "}
                <a href="#" className="text-primary hover:underline">
                  Terms of Service
                </a>{" "}
                and{" "}
                <a href="#" className="text-primary hover:underline">
                  Privacy Policy
                </a>
              </span>
            </label>

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
                  Create Account
                  <ArrowRight className="h-4 w-4" />
                </>
              )}
            </button>
          </form>

          {/* Divider */}
          <div className="my-5 flex items-center gap-3">
            <div className="h-px flex-1 bg-border" />
            <span className="text-xs text-text-muted">or sign up with</span>
            <div className="h-px flex-1 bg-border" />
          </div>

          {/* Social buttons */}
          <div className="flex gap-3">
            <button
              type="button"
              disabled
              className="flex h-11 flex-1 items-center justify-center rounded-lg border border-border bg-surface text-text-muted transition-colors cursor-not-allowed opacity-60"
              aria-label="Sign up with Google"
              title="Google OAuth not yet configured on the backend"
            >
              <Chrome className="h-5 w-5" />
            </button>
            <button
              type="button"
              disabled
              className="flex h-11 flex-1 items-center justify-center rounded-lg border border-border bg-surface text-text-muted transition-colors cursor-not-allowed opacity-60"
              aria-label="Sign up with Microsoft"
              title="Microsoft OAuth not yet configured on the backend"
            >
              <MicrosoftIcon className="h-5 w-5" />
            </button>
            <button
              type="button"
              disabled
              className="flex h-11 flex-1 items-center justify-center rounded-lg border border-border bg-surface text-text-muted transition-colors cursor-not-allowed opacity-60"
              aria-label="Sign up with SMIU Email"
              title="SMIU Email verification not yet configured on the backend"
            >
              <Mail className="h-5 w-5" />
            </button>
          </div>

          {/* Login link */}
          <p className="mt-5 text-center text-sm text-text-secondary">
            Already have an account?{" "}
            <a
              href="/login"
              className="font-medium text-primary hover:text-primary-hover"
            >
              Login here
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
