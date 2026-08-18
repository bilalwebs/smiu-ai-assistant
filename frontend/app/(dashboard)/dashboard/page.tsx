"use client";

import {
  ClipboardList,
  MessageSquare,
  Bell,
  CheckCircle,
  Clock,
} from "lucide-react";

const STATS = [
  { label: "Active Requests", value: "—", icon: ClipboardList, color: "text-primary" },
  { label: "Pending", value: "—", icon: Clock, color: "text-warning" },
  { label: "Resolved (30d)", value: "—", icon: CheckCircle, color: "text-success" },
  { label: "Unread Notifications", value: "—", icon: Bell, color: "text-information" },
];

export default function DashboardPage() {
  return (
    <div className="mx-auto max-w-7xl px-6 py-8">
      {/* Welcome banner */}
      <div className="mb-8 rounded-2xl bg-gradient-to-r from-primary to-accent p-6 text-white shadow-lg">
        <h1 className="text-2xl font-bold">Welcome to SMIU AI Assistant</h1>
        <p className="mt-1 text-white/80">
          Your intelligent university workflow assistant
        </p>
        <div className="mt-4 flex gap-3">
          <a
            href="/chat"
            className="rounded-lg bg-white px-4 py-2 text-sm font-semibold text-primary shadow-sm hover:bg-white/90"
          >
            Chat with AI
          </a>
          <a
            href="/dashboard/requests/new"
            className="rounded-lg border border-white/30 px-4 py-2 text-sm font-medium text-white hover:bg-white/10"
          >
            New Request
          </a>
        </div>
      </div>

      {/* Stats */}
      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {STATS.map((stat) => (
          <div
            key={stat.label}
            className="rounded-xl border border-border bg-surface p-4 shadow-sm"
          >
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
                <stat.icon className={`h-5 w-5 ${stat.color}`} />
              </div>
              <div>
                <p className="text-2xl font-bold text-text-primary">
                  {stat.value}
                </p>
                <p className="text-xs text-text-secondary">{stat.label}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-xl border border-border bg-surface p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-text-primary">
            Quick Actions
          </h2>
          <div className="grid grid-cols-2 gap-3">
            <a
              href="/chat"
              className="flex items-center gap-3 rounded-lg border border-border p-3 transition-colors hover:border-primary/50 hover:bg-primary-soft"
            >
              <MessageSquare className="h-5 w-5 text-primary" />
              <span className="text-sm font-medium text-text-primary">
                Chat with AI
              </span>
            </a>
            <a
              href="/dashboard/requests/new"
              className="flex items-center gap-3 rounded-lg border border-border p-3 transition-colors hover:border-primary/50 hover:bg-primary-soft"
            >
              <ClipboardList className="h-5 w-5 text-primary" />
              <span className="text-sm font-medium text-text-primary">
                New Request
              </span>
            </a>
          </div>
        </div>

        <div className="rounded-xl border border-border bg-surface p-6 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-text-primary">
            Recent Activity
          </h2>
          <p className="text-sm text-text-secondary">
            No recent activity yet. Start a conversation or create a request.
          </p>
        </div>
      </div>
    </div>
  );
}
