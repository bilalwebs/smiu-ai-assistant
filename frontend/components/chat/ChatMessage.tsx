"use client";

import { useState } from "react";
import { Copy, Check, ChevronDown, ChevronUp, Bot, User } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ChatCitationRead } from "@/types/api";
import { format } from "date-fns";

interface ChatMessageProps {
  role: "user" | "assistant" | "system";
  content: string;
  agentKey?: string | null;
  citations?: ChatCitationRead[];
  timestamp?: string;
  status?: string;
}

export default function ChatMessage({
  role,
  content,
  agentKey,
  citations = [],
  timestamp,
  status,
}: ChatMessageProps) {
  const [copied, setCopied] = useState(false);
  const [showSources, setShowSources] = useState(false);

  const isUser = role === "user";

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className={cn(
        "group flex gap-3 px-4 py-3",
        isUser ? "flex-row-reverse" : "flex-row"
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          "flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-primary-soft" : "bg-muted"
        )}
      >
        {isUser ? (
          <User className="h-4 w-4 text-primary" />
        ) : (
          <Bot className="h-4 w-4 text-accent" />
        )}
      </div>

      {/* Message body */}
      <div className={cn("flex max-w-[75%] flex-col gap-1", isUser && "items-end")}>
        {/* Agent badge for assistant */}
        {!isUser && agentKey && (
          <span className="text-xs font-medium text-text-muted capitalize">
            {agentKey.replace("_", " ")} Agent
          </span>
        )}

        {/* Bubble */}
        <div
          className={cn(
            "rounded-xl px-4 py-3 text-sm leading-relaxed",
            isUser
              ? "bg-primary text-white"
              : "border border-border bg-surface text-text-primary shadow-sm"
          )}
        >
          <div className="whitespace-pre-wrap break-words">{content}</div>
        </div>

        {/* Actions row */}
        <div className="flex items-center gap-2">
          {timestamp && (
            <span className="text-xs text-text-muted">
              {format(new Date(timestamp), "HH:mm")}
            </span>
          )}

          {!isUser && (
            <>
              <button
                onClick={handleCopy}
                className="flex h-6 w-6 items-center justify-center rounded text-text-muted opacity-0 transition-opacity hover:text-text-secondary group-hover:opacity-100"
                aria-label="Copy message"
              >
                {copied ? (
                  <Check className="h-3.5 w-3.5 text-success" />
                ) : (
                  <Copy className="h-3.5 w-3.5" />
                )}
              </button>

              {citations.length > 0 && (
                <button
                  onClick={() => setShowSources(!showSources)}
                  className="flex items-center gap-1 text-xs text-primary hover:text-primary-hover"
                >
                  Sources: {citations.length}
                  {showSources ? (
                    <ChevronUp className="h-3 w-3" />
                  ) : (
                    <ChevronDown className="h-3 w-3" />
                  )}
                </button>
              )}
            </>
          )}
        </div>

        {/* Citations */}
        {!isUser && showSources && citations.length > 0 && (
          <div className="mt-1 space-y-1">
            {citations.map((citation, i) => (
              <div
                key={i}
                className="rounded-lg border border-border bg-muted/50 px-3 py-2 text-xs"
              >
                <p className="font-medium text-text-primary">
                  {citation.source_title}
                </p>
                {citation.snippet && (
                  <p className="mt-0.5 text-text-secondary line-clamp-2">
                    {citation.snippet}
                  </p>
                )}
                {citation.source_url && (
                  <a
                    href={citation.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-1 inline-block text-primary hover:underline"
                  >
                    View source
                  </a>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
