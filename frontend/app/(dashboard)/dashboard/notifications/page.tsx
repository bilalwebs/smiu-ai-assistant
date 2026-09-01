"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import type { NotificationRead, PaginationMeta } from "@/types/api";
import {
  Bell,
  CheckCheck,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Filter,
  Search,
} from "lucide-react";

const TYPE_FILTERS = [
  { value: "", label: "All" },
  { value: "request", label: "Requests" },
  { value: "ai", label: "AI" },
  { value: "system", label: "System" },
];

const TYPE_COLORS: Record<string, string> = {
  request: "bg-blue-100 text-blue-700",
  ai: "bg-purple-100 text-purple-700",
  system: "bg-gray-100 text-gray-700",
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
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<NotificationRead[]>([]);
  const [pagination, setPagination] = useState<PaginationMeta | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [markingAll, setMarkingAll] = useState(false);

  const fetchNotifications = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await api.notifications.list(currentPage, 20);
      let filtered = result.data;
      if (typeFilter) {
        filtered = filtered.filter((n) => n.type === typeFilter);
      }
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        filtered = filtered.filter(
          (n) =>
            n.title.toLowerCase().includes(q) ||
            (n.body && n.body.toLowerCase().includes(q))
        );
      }
      setNotifications(filtered);
      setPagination(result.pagination);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load notifications");
    } finally {
      setLoading(false);
    }
  }, [currentPage, typeFilter, searchQuery]);

  useEffect(() => {
    fetchNotifications();
  }, [fetchNotifications]);

  const handleMarkAllRead = async () => {
    setMarkingAll(true);
    try {
      await api.notifications.markAllRead();
      setNotifications((prev) =>
        prev.map((n) => ({ ...n, read_at: n.read_at || new Date().toISOString() }))
      );
    } catch {
      // ignore
    } finally {
      setMarkingAll(false);
    }
  };

  const handleMarkRead = async (id: string) => {
    try {
      await api.notifications.markRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, read_at: new Date().toISOString() } : n))
      );
    } catch {
      // ignore
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Notifications</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Stay updated with your activity
          </p>
        </div>
        <button
          onClick={handleMarkAllRead}
          disabled={markingAll}
          className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium text-text-secondary hover:bg-muted disabled:opacity-50 transition-colors"
        >
          {markingAll ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <CheckCheck className="h-4 w-4" />
          )}
          Mark all as read
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            placeholder="Search notifications..."
            className="h-10 w-full rounded-lg border border-border bg-surface pl-10 pr-4 text-sm text-text-primary placeholder-text-muted focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div className="flex gap-2">
          {TYPE_FILTERS.map((filter) => (
            <button
              key={filter.value}
              onClick={() => {
                setTypeFilter(filter.value);
                setCurrentPage(1);
              }}
              className={`rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                typeFilter === filter.value
                  ? "bg-primary-soft text-primary"
                  : "border border-border text-text-secondary hover:bg-muted"
              }`}
            >
              {filter.label}
            </button>
          ))}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-danger/20 bg-danger/5 px-4 py-3 text-sm text-danger">
          {error}
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : notifications.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
            <Bell className="h-8 w-8 text-text-muted" />
          </div>
          <h3 className="mt-4 text-lg font-semibold text-text-primary">No notifications</h3>
          <p className="mt-1 max-w-sm text-sm text-text-secondary">
            {searchQuery || typeFilter
              ? "Try adjusting your search or filters."
              : "You're all caught up!"}
          </p>
        </div>
      ) : (
        <>
          <div className="divide-y divide-border rounded-xl border border-border bg-surface shadow-sm">
            {notifications.map((notif) => (
              <div
                key={notif.id}
                className={`flex items-start gap-4 px-5 py-4 hover:bg-muted/30 ${
                  !notif.read_at ? "bg-primary-soft/30" : ""
                }`}
              >
                <div className="mt-1 flex-shrink-0">
                  <div
                    className={`flex h-2 w-2 rounded-full ${
                      notif.read_at ? "bg-transparent" : "bg-primary"
                    }`}
                  />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-medium text-text-primary">{notif.title}</p>
                    <span className={`inline-flex flex-shrink-0 items-center rounded-full px-2 py-0.5 text-[10px] font-medium ${TYPE_COLORS[notif.type] || "bg-gray-100 text-gray-700"}`}>
                      {notif.type}
                    </span>
                  </div>
                  {notif.body && (
                    <p className="mt-1 text-sm text-text-secondary line-clamp-2">{notif.body}</p>
                  )}
                  <div className="mt-2 flex items-center gap-3">
                    <span className="text-xs text-text-muted">
                      {formatRelativeTime(notif.created_at)}
                    </span>
                    {!notif.read_at && (
                      <button
                        onClick={() => handleMarkRead(notif.id)}
                        className="text-xs font-medium text-primary hover:text-primary-hover"
                      >
                        Mark as read
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {pagination && pagination.total_pages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-text-secondary">
                Page {pagination.page} of {pagination.total_pages}
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="flex h-9 w-9 items-center justify-center rounded-lg border border-border text-text-secondary hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <button
                  onClick={() => setCurrentPage((p) => Math.min(pagination.total_pages, p + 1))}
                  disabled={currentPage === pagination.total_pages}
                  className="flex h-9 w-9 items-center justify-center rounded-lg border border-border text-text-secondary hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
