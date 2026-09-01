"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/store";
import { api } from "@/lib/api";
import type {
  StudentDashboardRead,
  RequestRead,
  NotificationRead,
} from "@/types/api";
import {
  ClipboardList,
  Clock,
  CheckCircle2,
  Bell,
  PlusCircle,
  MessageSquare,
  Upload,
  Search,
  History,
  HelpCircle,
  ArrowRight,
  FileText,
  Bot,
  Loader2,
  ChevronRight,
  AlertCircle,
} from "lucide-react";

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  submitted: "bg-blue-100 text-blue-700",
  in_review: "bg-yellow-100 text-yellow-700",
  assigned: "bg-purple-100 text-purple-700",
  processing: "bg-indigo-100 text-indigo-700",
  resolved: "bg-green-100 text-green-700",
  closed: "bg-gray-100 text-gray-500",
  rejected: "bg-red-100 text-red-700",
};

function formatRelativeTime(dateStr: string) {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "Just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHrs = Math.floor(diffMin / 60);
  if (diffHrs < 24) return `${diffHrs}h ago`;
  const diffDays = Math.floor(diffHrs / 24);
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export default function DashboardPage() {
  const { user } = useAuthStore();
  const router = useRouter();
  const [stats, setStats] = useState<StudentDashboardRead | null>(null);
  const [recentRequests, setRecentRequests] = useState<RequestRead[]>([]);
  const [recentNotifications, setRecentNotifications] = useState<NotificationRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const [statsData, requestsData, notificationsData] = await Promise.allSettled([
          api.students.getDashboard(),
          api.requests.list(1, 5),
          api.notifications.list(1, 5),
        ]);

        if (statsData.status === "fulfilled") setStats(statsData.value);
        if (requestsData.status === "fulfilled") setRecentRequests(requestsData.value.data);
        if (notificationsData.status === "fulfilled") setRecentNotifications(notificationsData.value.data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load dashboard");
      } finally {
        setLoading(false);
      }
    };
    fetchDashboard();
  }, []);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  const statCards = [
    { label: "Active Requests", value: stats?.active_requests ?? 0, icon: ClipboardList, color: "text-blue-600", bg: "bg-blue-50" },
    { label: "Pending", value: stats?.pending_requests ?? 0, icon: Clock, color: "text-amber-600", bg: "bg-amber-50" },
    { label: "Resolved (30 Days)", value: stats?.resolved_requests ?? 0, icon: CheckCircle2, color: "text-green-600", bg: "bg-green-50" },
    { label: "Unread Notifications", value: stats?.unread_notifications ?? 0, icon: Bell, color: "text-purple-600", bg: "bg-purple-50" },
  ];

  const quickActions = [
    { label: "New Request", href: "/dashboard/requests/new", icon: PlusCircle, color: "bg-blue-500" },
    { label: "Chat with AI", href: "/chat", icon: MessageSquare, color: "bg-purple-500" },
    { label: "Upload Document", href: "/dashboard/requests/new", icon: Upload, color: "bg-emerald-500" },
    { label: "Search", href: "/dashboard/requests", icon: Search, color: "bg-amber-500" },
    { label: "My History", href: "/dashboard/history", icon: History, color: "bg-indigo-500" },
    { label: "Contact Support", href: "mailto:support@smiu.edu.pk", icon: HelpCircle, color: "bg-rose-500" },
  ];

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6">
      {error && (
        <div className="rounded-lg border border-danger/20 bg-danger/5 px-4 py-3 text-sm text-danger">
          {error}
        </div>
      )}

      {/* Welcome Section */}
      <div className="rounded-xl bg-gradient-to-r from-primary to-primary-hover p-6 text-white">
        <h1 className="text-2xl font-bold">
          Welcome back, {user?.full_name?.split(" ")[0] || "Student"}!
        </h1>
        <p className="mt-1 text-sm text-white/80">
          Here&apos;s what&apos;s happening with your requests today.
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <Link
            href="/dashboard/requests/new"
            className="inline-flex items-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-medium text-primary hover:bg-white/90 transition-colors"
          >
            <PlusCircle className="h-4 w-4" />
            New Request
          </Link>
          <Link
            href="/chat"
            className="inline-flex items-center gap-2 rounded-lg bg-white/20 px-4 py-2 text-sm font-medium text-white hover:bg-white/30 transition-colors"
          >
            <MessageSquare className="h-4 w-4" />
            Chat with AI
          </Link>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map((card) => (
          <div
            key={card.label}
            className="rounded-xl border border-border bg-surface p-5 shadow-sm"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-text-secondary">{card.label}</p>
                <p className="mt-2 text-3xl font-bold text-text-primary">{card.value}</p>
              </div>
              <div className={`flex h-12 w-12 items-center justify-center rounded-xl ${card.bg}`}>
                <card.icon className={`h-6 w-6 ${card.color}`} />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* My Recent Requests */}
        <div className="lg:col-span-2 rounded-xl border border-border bg-surface shadow-sm">
          <div className="flex items-center justify-between border-b border-border px-5 py-4">
            <h2 className="text-lg font-semibold text-text-primary">My Recent Requests</h2>
            <Link
              href="/dashboard/requests"
              className="text-sm font-medium text-primary hover:text-primary-hover flex items-center gap-1"
            >
              View All <ChevronRight className="h-4 w-4" />
            </Link>
          </div>
          <div className="divide-y divide-border">
            {recentRequests.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <FileText className="h-10 w-10 text-text-muted" />
                <p className="mt-3 text-sm font-medium text-text-primary">No requests yet</p>
                <p className="mt-1 text-xs text-text-secondary">Create your first request to get started.</p>
                <Link
                  href="/dashboard/requests/new"
                  className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover"
                >
                  <PlusCircle className="h-4 w-4" />
                  New Request
                </Link>
              </div>
            ) : (
              recentRequests.map((req) => (
                <div key={req.id} className="flex items-center justify-between px-5 py-3 hover:bg-muted/50">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-text-primary truncate">{req.title}</p>
                    <p className="mt-0.5 text-xs text-text-muted">
                      {req.request_no} &middot; {formatRelativeTime(req.created_at)}
                    </p>
                  </div>
                  <span className={`ml-4 inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLORS[req.status] || "bg-gray-100 text-gray-700"}`}>
                    {req.status.replace("_", " ")}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Request Overview Chart */}
        <div className="rounded-xl border border-border bg-surface shadow-sm">
          <div className="border-b border-border px-5 py-4">
            <h2 className="text-lg font-semibold text-text-primary">Request Overview</h2>
          </div>
          <div className="p-5">
            <div className="space-y-4">
              {[
                { label: "Active", value: stats?.active_requests ?? 0, color: "bg-blue-500", max: Math.max(stats?.active_requests ?? 0, stats?.pending_requests ?? 0, stats?.resolved_requests ?? 0, 1) },
                { label: "Pending", value: stats?.pending_requests ?? 0, color: "bg-amber-500", max: Math.max(stats?.active_requests ?? 0, stats?.pending_requests ?? 0, stats?.resolved_requests ?? 0, 1) },
                { label: "Resolved", value: stats?.resolved_requests ?? 0, color: "bg-green-500", max: Math.max(stats?.active_requests ?? 0, stats?.pending_requests ?? 0, stats?.resolved_requests ?? 0, 1) },
              ].map((item) => (
                <div key={item.label}>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-text-secondary">{item.label}</span>
                    <span className="font-medium text-text-primary">{item.value}</span>
                  </div>
                  <div className="mt-2 h-2.5 overflow-hidden rounded-full bg-muted">
                    <div
                      className={`h-full rounded-full ${item.color} transition-all duration-500`}
                      style={{ width: `${item.max > 0 ? (item.value / item.max) * 100 : 0}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
            {(!stats || (stats.active_requests === 0 && stats.pending_requests === 0 && stats.resolved_requests === 0)) && (
              <p className="mt-4 text-center text-xs text-text-muted">No request data yet</p>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Quick Actions */}
        <div className="rounded-xl border border-border bg-surface shadow-sm">
          <div className="border-b border-border px-5 py-4">
            <h2 className="text-lg font-semibold text-text-primary">Quick Actions</h2>
          </div>
          <div className="grid grid-cols-2 gap-3 p-5">
            {quickActions.map((action) => (
              <Link
                key={action.label}
                href={action.href}
                className="flex flex-col items-center gap-2 rounded-xl border border-border p-4 text-center hover:border-primary hover:bg-primary-soft transition-all"
              >
                <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${action.color} text-white`}>
                  <action.icon className="h-5 w-5" />
                </div>
                <span className="text-xs font-medium text-text-primary">{action.label}</span>
              </Link>
            ))}
          </div>
        </div>

        {/* Recent Notifications */}
        <div className="rounded-xl border border-border bg-surface shadow-sm">
          <div className="flex items-center justify-between border-b border-border px-5 py-4">
            <h2 className="text-lg font-semibold text-text-primary">Recent Notifications</h2>
            <Link
              href="/dashboard/notifications"
              className="text-sm font-medium text-primary hover:text-primary-hover flex items-center gap-1"
            >
              View All <ChevronRight className="h-4 w-4" />
            </Link>
          </div>
          <div className="divide-y divide-border">
            {recentNotifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <Bell className="h-10 w-10 text-text-muted" />
                <p className="mt-3 text-sm font-medium text-text-primary">No notifications</p>
                <p className="mt-1 text-xs text-text-secondary">You&apos;re all caught up!</p>
              </div>
            ) : (
              recentNotifications.map((notif) => (
                <div key={notif.id} className="px-5 py-3 hover:bg-muted/50">
                  <div className="flex items-start gap-3">
                    <div className={`mt-0.5 flex h-2 w-2 flex-shrink-0 rounded-full ${notif.read_at ? "bg-transparent" : "bg-primary"}`} />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-text-primary">{notif.title}</p>
                      {notif.body && (
                        <p className="mt-0.5 text-xs text-text-secondary line-clamp-2">{notif.body}</p>
                      )}
                      <p className="mt-1 text-xs text-text-muted">{formatRelativeTime(notif.created_at)}</p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Help / Robot Widget */}
        <div className="rounded-xl border border-border bg-gradient-to-br from-primary-soft to-surface p-6 shadow-sm">
          <div className="flex flex-col items-center text-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10">
              <Bot className="h-8 w-8 text-primary" />
            </div>
            <h3 className="mt-4 text-lg font-semibold text-text-primary">Need Help?</h3>
            <p className="mt-1 text-sm text-text-secondary">
              Our AI assistant is here to help you with any questions.
            </p>
            <Link
              href="/chat"
              className="mt-4 inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-white hover:bg-primary-hover transition-colors"
            >
              <MessageSquare className="h-4 w-4" />
              Chat Now
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
