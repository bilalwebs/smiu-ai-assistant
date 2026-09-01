"use client";

import { Bell, Search, Menu } from "lucide-react";
import { useAuthStore } from "@/lib/store";
import { useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import { api } from "@/lib/api";

interface HeaderProps {
  onMenuToggle?: () => void;
}

export default function Header({ onMenuToggle }: HeaderProps) {
  const { user } = useAuthStore();
  const router = useRouter();
  const [searchFocused, setSearchFocused] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    const fetchUnread = async () => {
      try {
        const data = await api.notifications.unreadCount();
        setUnreadCount(data.unread);
      } catch {
        // ignore
      }
    };
    fetchUnread();
    const interval = setInterval(fetchUnread, 60000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-surface px-4 sm:px-6">
      {/* Left side */}
      <div className="flex items-center gap-4">
        <button
          onClick={onMenuToggle}
          className="flex h-9 w-9 items-center justify-center rounded-lg text-text-secondary hover:bg-muted lg:hidden"
          aria-label="Toggle menu"
        >
          <Menu className="h-5 w-5" />
        </button>

        {/* Search */}
        <div className="relative hidden sm:block">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            placeholder="Search..."
            className="h-9 w-64 rounded-lg border border-border bg-muted pl-9 pr-4 text-sm text-text-primary placeholder-text-muted focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            onFocus={() => setSearchFocused(true)}
            onBlur={() => setSearchFocused(false)}
          />
        </div>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => router.push("/dashboard/notifications")}
          className="relative flex h-9 w-9 items-center justify-center rounded-lg text-text-secondary hover:bg-muted"
          aria-label="Notifications"
        >
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <span className="absolute -right-0.5 -top-0.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-danger px-1 text-[10px] font-bold text-white">
              {unreadCount > 99 ? "99+" : unreadCount}
            </span>
          )}
        </button>

        <button
          onClick={() => router.push("/dashboard/profile")}
          className="flex items-center gap-2 rounded-lg p-1 hover:bg-muted"
        >
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary-soft text-sm font-semibold text-primary">
            {user?.full_name?.charAt(0)?.toUpperCase() || "U"}
          </div>
          <span className="hidden text-sm font-medium text-text-primary md:block">
            {user?.full_name || "User"}
          </span>
        </button>

        <button
          onClick={async () => {
            const { useAuthStore } = await import("@/lib/store");
            const { logout } = useAuthStore.getState();
            await logout();
            router.push("/login");
          }}
          className="flex h-9 w-9 items-center justify-center rounded-lg text-text-secondary hover:bg-muted hover:text-danger"
          aria-label="Sign out"
          title="Sign out"
        >
          <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
          </svg>
        </button>
      </div>
    </header>
  );
}
