"use client";

import { useState } from "react";
import { useAuthStore } from "@/lib/store";
import {
  User,
  Lock,
  Bell,
  Eye,
  Globe,
  Palette,
  Shield,
  ChevronRight,
  Loader2,
} from "lucide-react";

const SETTINGS_SECTIONS = [
  {
    id: "account",
    label: "Account",
    icon: User,
    description: "Manage your account settings",
  },
  {
    id: "password",
    label: "Password",
    icon: Lock,
    description: "Change your password",
  },
  {
    id: "notifications",
    label: "Notifications",
    icon: Bell,
    description: "Configure notification preferences",
  },
  {
    id: "privacy",
    label: "Privacy",
    icon: Eye,
    description: "Manage privacy settings",
  },
  {
    id: "appearance",
    label: "Appearance",
    icon: Palette,
    description: "Customize the look and feel",
  },
  {
    id: "language",
    label: "Language",
    icon: Globe,
    description: "Set your preferred language",
  },
] as const;

export default function SettingsPage() {
  const { user } = useAuthStore();
  const [activeSection, setActiveSection] = useState("account");
  const [saving, setSaving] = useState(false);

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Settings</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Manage your account preferences
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
        {/* Sidebar */}
        <div className="rounded-xl border border-border bg-surface p-2 shadow-sm">
          {SETTINGS_SECTIONS.map((section) => (
            <button
              key={section.id}
              onClick={() => setActiveSection(section.id)}
              className={`flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium transition-colors ${
                activeSection === section.id
                  ? "bg-primary-soft text-primary"
                  : "text-text-secondary hover:bg-muted hover:text-text-primary"
              }`}
            >
              <section.icon className="h-4 w-4 flex-shrink-0" />
              <span>{section.label}</span>
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="lg:col-span-3 rounded-xl border border-border bg-surface p-6 shadow-sm">
          {activeSection === "account" && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-text-primary">Account Settings</h2>
              <p className="text-sm text-text-secondary">
                Your account information is managed by the university administration.
              </p>
              <div className="space-y-3">
                <div className="flex items-center justify-between rounded-lg border border-border p-4">
                  <div>
                    <p className="text-sm font-medium text-text-primary">Email</p>
                    <p className="text-sm text-text-secondary">{user?.email}</p>
                  </div>
                  <span className="rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-700">
                    Verified
                  </span>
                </div>
                <div className="flex items-center justify-between rounded-lg border border-border p-4">
                  <div>
                    <p className="text-sm font-medium text-text-primary">Role</p>
                    <p className="text-sm text-text-secondary capitalize">{user?.role}</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeSection === "password" && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-text-primary">Change Password</h2>
              <p className="text-sm text-text-secondary">
                Password changes are managed through the authentication system.
              </p>
              <div className="rounded-lg border border-border bg-muted/50 p-4">
                <div className="flex items-start gap-3">
                  <Shield className="mt-0.5 h-5 w-5 flex-shrink-0 text-primary" />
                  <div>
                    <p className="text-sm font-medium text-text-primary">Password Policy</p>
                    <ul className="mt-1 space-y-1 text-xs text-text-secondary">
                      <li>At least 8 characters</li>
                      <li>One uppercase letter</li>
                      <li>One lowercase letter</li>
                      <li>One number or symbol</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeSection === "notifications" && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-text-primary">Notification Preferences</h2>
              <p className="text-sm text-text-secondary">
                Configure how you receive notifications.
              </p>
              <div className="space-y-3">
                {[
                  { label: "Email Notifications", description: "Receive notifications via email", enabled: false },
                  { label: "Request Updates", description: "Get notified when request status changes", enabled: true },
                  { label: "AI Responses", description: "Notify when AI assistant responds", enabled: true },
                  { label: "System Announcements", description: "University-wide announcements", enabled: true },
                ].map((item) => (
                  <div key={item.label} className="flex items-center justify-between rounded-lg border border-border p-4">
                    <div>
                      <p className="text-sm font-medium text-text-primary">{item.label}</p>
                      <p className="text-xs text-text-secondary">{item.description}</p>
                    </div>
                    <div className={`relative inline-flex h-6 w-11 cursor-pointer items-center rounded-full transition-colors ${item.enabled ? "bg-primary" : "bg-gray-300"}`}>
                      <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${item.enabled ? "translate-x-6" : "translate-x-1"}`} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeSection === "privacy" && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-text-primary">Privacy Settings</h2>
              <p className="text-sm text-text-secondary">
                Manage your privacy preferences.
              </p>
              <div className="rounded-lg border border-border bg-muted/50 p-4">
                <p className="text-sm text-text-secondary">
                  Your data is protected according to university privacy policies.
                  Contact support for data-related requests.
                </p>
              </div>
            </div>
          )}

          {activeSection === "appearance" && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-text-primary">Appearance</h2>
              <p className="text-sm text-text-secondary">
                Customize the look and feel of the application.
              </p>
              <div className="rounded-lg border border-border bg-muted/50 p-4">
                <p className="text-sm text-text-secondary">
                  Theme customization coming soon. Currently using the default light theme.
                </p>
              </div>
            </div>
          )}

          {activeSection === "language" && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-text-primary">Language</h2>
              <p className="text-sm text-text-secondary">
                Set your preferred language for the interface.
              </p>
              <div className="rounded-lg border border-border p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-text-primary">Interface Language</p>
                    <p className="text-sm text-text-secondary">English (Default)</p>
                  </div>
                  <ChevronRight className="h-4 w-4 text-text-muted" />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
