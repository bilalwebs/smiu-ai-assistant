"use client";

import { Bell, Search, Menu } from "lucide-react";
import { useAuthStore } from "@/lib/store";
import { useRouter } from "next/navigation";
import { useState } from "react";

interface HeaderProps {
  onMenuToggle?: () => void;
}

export default function Header({ onMenuToggle }: HeaderProps) {
  const { user } = useAuthStore();
  const router = useRouter();
  const [searchFocused, setSearchFocused] = useState(false);

  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-surface px-6">
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
            placeholder="Search... (⌘K)"
            className="h-9 w-64 rounded-lg border border-border bg-muted pl-9 pr-4 text-sm text-text-primary placeholder-text-muted focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            onFocus={() => setSearchFocused(true)}
            onBlur={() => setSearchFocused(false)}
          />
        </div>
      </div>

      {/* Right side */}
      <div className="flex items-center gap-2">
        <button
          className="relative flex h-9 w-9 items-center justify-center rounded-lg text-text-secondary hover:bg-muted"
          aria-label="Notifications"
        >
          <Bell className="h-5 w-5" />
          <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-danger" />
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
      </div>
    </header>
  );
}
