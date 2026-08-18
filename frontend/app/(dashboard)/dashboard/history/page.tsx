"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { ConversationRead } from "@/types/api";
import EmptyState from "@/components/ui/EmptyState";
import {
  History,
  MessageSquare,
  Search,
  Trash2,
  Archive,
  RotateCcw,
  Clock,
} from "lucide-react";
import { format, isToday, isYesterday, isThisWeek } from "date-fns";

type Tab = "active" | "archived";

export default function HistoryPage() {
  const router = useRouter();
  const [conversations, setConversations] = useState<ConversationRead[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>("active");
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);

  const loadConversations = async (pageNum: number) => {
    try {
      const data = await api.conversations.list(pageNum, 20);
      if (pageNum === 1) {
        setConversations(data);
      } else {
        setConversations((prev) => [...prev, ...data]);
      }
      setHasMore(data.length === 20);
    } catch {
      // Error handled silently
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadConversations(1);
  }, []);

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Delete this conversation?")) return;
    try {
      await api.conversations.delete(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
    } catch {
      // Error handled silently
    }
  };

  const handleArchive = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.conversations.archive(id);
      setConversations((prev) =>
        prev.map((c) => (c.id === id ? { ...c, status: "archived" as const } : c))
      );
    } catch {
      // Error handled silently
    }
  };

  const handleRestore = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.conversations.restore(id);
      setConversations((prev) =>
        prev.map((c) => (c.id === id ? { ...c, status: "active" as const } : c))
      );
    } catch {
      // Error handled silently
    }
  };

  const filtered = conversations
    .filter((c) =>
      activeTab === "active" ? c.status === "active" : c.status === "archived"
    )
    .filter((c) =>
      searchQuery
        ? (c.title || "").toLowerCase().includes(searchQuery.toLowerCase())
        : true
    );

  const groupConversations = (items: ConversationRead[]) => {
    const groups: { label: string; items: ConversationRead[] }[] = [];
    const today: ConversationRead[] = [];
    const yesterday: ConversationRead[] = [];
    const thisWeek: ConversationRead[] = [];
    const older: ConversationRead[] = [];

    items.forEach((item) => {
      const date = new Date(item.last_message_at || item.created_at);
      if (isToday(date)) today.push(item);
      else if (isYesterday(date)) yesterday.push(item);
      else if (isThisWeek(date)) thisWeek.push(item);
      else older.push(item);
    });

    if (today.length) groups.push({ label: "Today", items: today });
    if (yesterday.length) groups.push({ label: "Yesterday", items: yesterday });
    if (thisWeek.length) groups.push({ label: "This Week", items: thisWeek });
    if (older.length) groups.push({ label: "Older", items: older });

    return groups;
  };

  const groups = groupConversations(filtered);

  return (
    <div className="mx-auto max-w-4xl px-4 py-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-text-primary">
          Conversation History
        </h1>
        <p className="mt-1 text-sm text-text-secondary">
          Browse and resume your AI conversations
        </p>
      </div>

      {/* Tabs and search */}
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex gap-1 rounded-lg bg-muted p-1">
          <button
            onClick={() => setActiveTab("active")}
            className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
              activeTab === "active"
                ? "bg-surface text-text-primary shadow-sm"
                : "text-text-secondary hover:text-text-primary"
            }`}
          >
            Active
          </button>
          <button
            onClick={() => setActiveTab("archived")}
            className={`rounded-md px-4 py-1.5 text-sm font-medium transition-colors ${
              activeTab === "archived"
                ? "bg-surface text-text-primary shadow-sm"
                : "text-text-secondary hover:text-text-primary"
            }`}
          >
            Archived
          </button>
        </div>

        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            placeholder="Search conversations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-9 w-full rounded-lg border border-border bg-surface pl-9 pr-4 text-sm text-text-primary placeholder-text-muted focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 sm:w-64"
          />
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      ) : groups.length === 0 ? (
        <EmptyState
          icon={History}
          title="No conversation history"
          description="Your AI conversations will be saved here."
          action={
            <button
              onClick={() => router.push("/chat")}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover"
            >
              Start new chat
            </button>
          }
        />
      ) : (
        <div className="space-y-6">
          {groups.map((group) => (
            <div key={group.label}>
              <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-text-muted">
                {group.label}
              </h2>
              <div className="space-y-1">
                {group.items.map((conversation) => (
                  <button
                    key={conversation.id}
                    onClick={() => router.push(`/chat/${conversation.id}`)}
                    className="group flex w-full items-center gap-3 rounded-xl border border-border bg-surface p-4 text-left shadow-sm transition-all hover:border-primary/50 hover:shadow-md"
                  >
                    <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-primary-soft">
                      <MessageSquare className="h-5 w-5 text-primary" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-text-primary">
                        {conversation.title || "New Conversation"}
                      </p>
                      <div className="mt-0.5 flex items-center gap-2 text-xs text-text-muted">
                        <Clock className="h-3 w-3" />
                        <span>
                          {conversation.last_message_at
                            ? format(
                                new Date(conversation.last_message_at),
                                "MMM d, HH:mm"
                              )
                            : format(
                                new Date(conversation.created_at),
                                "MMM d, HH:mm"
                              )}
                        </span>
                        <span>·</span>
                        <span>
                          {conversation.message_count} message
                          {conversation.message_count !== 1 ? "s" : ""}
                        </span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                      {activeTab === "active" ? (
                        <button
                          onClick={(e) => handleArchive(conversation.id, e)}
                          className="rounded-lg p-1.5 text-text-muted hover:bg-muted hover:text-text-secondary"
                          aria-label="Archive"
                        >
                          <Archive className="h-4 w-4" />
                        </button>
                      ) : (
                        <button
                          onClick={(e) => handleRestore(conversation.id, e)}
                          className="rounded-lg p-1.5 text-text-muted hover:bg-muted hover:text-text-secondary"
                          aria-label="Restore"
                        >
                          <RotateCcw className="h-4 w-4" />
                        </button>
                      )}
                      <button
                        onClick={(e) => handleDelete(conversation.id, e)}
                        className="rounded-lg p-1.5 text-text-muted hover:bg-danger/10 hover:text-danger"
                        aria-label="Delete"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ))}

          {/* Load more */}
          {hasMore && (
            <div className="flex justify-center pt-4">
              <button
                onClick={() => {
                  setPage((p) => p + 1);
                  loadConversations(page + 1);
                }}
                className="rounded-lg border border-border bg-surface px-4 py-2 text-sm font-medium text-text-secondary hover:bg-muted"
              >
                Load more
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
