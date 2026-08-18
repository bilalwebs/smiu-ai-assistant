"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  ClipboardList,
  PlusCircle,
  MessageSquare,
  History,
  Bell,
  User,
  Settings,
  LogOut,
  Bot,
  ChevronLeft,
} from "lucide-react";
import { useAuthStore } from "@/lib/store";

const NAV_ITEMS = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "My Requests", href: "/dashboard/requests", icon: ClipboardList },
  { label: "New Request", href: "/dashboard/requests/new", icon: PlusCircle },
  { label: "Chat with AI", href: "/chat", icon: MessageSquare },
  { label: "Conversation History", href: "/dashboard/history", icon: History },
  { label: "Notifications", href: "/dashboard/notifications", icon: Bell },
  { label: "Profile", href: "/dashboard/profile", icon: User },
  { label: "Settings", href: "/dashboard/settings", icon: Settings },
] as const;

interface SidebarProps {
  collapsed?: boolean;
  onToggle?: () => void;
}

export default function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();

  return (
    <aside
      className={cn(
        "flex h-screen flex-col border-r border-border bg-surface transition-all duration-250",
        collapsed ? "w-20" : "w-[280px]"
      )}
    >
      {/* Brand */}
      <div className="flex h-16 items-center justify-between border-b border-border px-4">
        {!collapsed && (
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
              <Bot className="h-5 w-5 text-white" />
            </div>
            <div>
              <span className="text-sm font-semibold text-text-primary">SMIU</span>
              <span className="ml-1 text-sm font-semibold text-primary">AI</span>
            </div>
          </div>
        )}
        <button
          onClick={onToggle}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-text-secondary hover:bg-muted"
          aria-label="Toggle sidebar"
        >
          <ChevronLeft
            className={cn(
              "h-4 w-4 transition-transform",
              collapsed && "rotate-180"
            )}
          />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 scrollbar-thin">
        <ul className="space-y-1">
          {NAV_ITEMS.map((item) => {
            const isActive =
              pathname === item.href ||
              (item.href !== "/chat" && item.href !== "/dashboard" && pathname.startsWith(item.href));
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all",
                    isActive
                      ? "bg-primary-soft text-primary"
                      : "text-text-secondary hover:bg-muted hover:text-text-primary",
                    collapsed && "justify-center px-2"
                  )}
                >
                  <item.icon
                    className={cn(
                      "h-5 w-5 flex-shrink-0 transition-colors",
                      isActive
                        ? "text-primary"
                        : "text-text-muted group-hover:text-text-primary"
                    )}
                  />
                  {!collapsed && <span>{item.label}</span>}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* AI Agent Status */}
      {!collapsed && (
        <div className="mx-3 mb-3 rounded-lg border border-border bg-muted/50 p-3">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-success animate-pulse" />
            <span className="text-xs font-medium text-text-secondary">
              AI Agent Status
            </span>
          </div>
          <p className="mt-1 text-xs text-text-muted">All systems operational</p>
        </div>
      )}

      {/* User card */}
      <div
        className={cn(
          "border-t border-border p-3",
          collapsed && "flex justify-center"
        )}
      >
        {collapsed ? (
          <button
            onClick={() => logout()}
            className="flex h-10 w-10 items-center justify-center rounded-lg text-text-muted hover:bg-muted hover:text-danger"
            aria-label="Sign out"
          >
            <LogOut className="h-4 w-4" />
          </button>
        ) : (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 overflow-hidden">
              <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-primary-soft text-sm font-semibold text-primary">
                {user?.full_name?.charAt(0)?.toUpperCase() || "U"}
              </div>
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-text-primary">
                  {user?.full_name || "User"}
                </p>
                <p className="truncate text-xs text-text-muted">
                  {user?.email || ""}
                </p>
              </div>
            </div>
            <button
              onClick={() => logout()}
              className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg text-text-muted hover:bg-muted hover:text-danger"
              aria-label="Sign out"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}
