"use client";

import { useState, useRef, useEffect, useCallback, use } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { MessageRead, ChatCitationRead, DocumentRead } from "@/types/api";
import ChatMessage from "@/components/chat/ChatMessage";
import ChatInput from "@/components/chat/ChatInput";
import { Bot, ArrowLeft, History } from "lucide-react";

export default function ConversationChatPage({
  params,
}: {
  params: Promise<{ conversationId: string }>;
}) {
  const { conversationId } = use(params);
  const router = useRouter();
  const [messages, setMessages] = useState<
    Array<{
      id: string;
      role: "user" | "assistant";
      content: string;
      agentKey?: string | null;
      citations: ChatCitationRead[];
      timestamp: string;
    }>
  >([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attachments, setAttachments] = useState<DocumentRead[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  // Load existing messages
  useEffect(() => {
    const loadMessages = async () => {
      try {
        const history = await api.messages.list(conversationId);
        const messagesWithCitations = await Promise.all(
          history.map(async (msg) => {
            let citations: ChatCitationRead[] = [];
            if (msg.role === "assistant") {
              try {
                citations = await api.chat.getSources(msg.id);
              } catch {
                // sources may not exist yet
              }
            }
            return {
              id: msg.id,
              role: msg.role as "user" | "assistant",
              content: msg.content,
              agentKey: msg.agent_key,
              citations,
              timestamp: msg.created_at,
            };
          })
        );
        setMessages(messagesWithCitations);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Failed to load conversation."
        );
      } finally {
        setIsLoading(false);
      }
    };
    loadMessages();
  }, [conversationId]);

  // Load existing attachments
  useEffect(() => {
    const loadAttachments = async () => {
      try {
        const docs = await api.documents.list(conversationId);
        setAttachments(docs);
      } catch {
        // Silently ignore — attachments are optional context
      }
    };
    loadAttachments();
  }, [conversationId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleAttach = async (file: File) => {
    setIsUploading(true);
    setError(null);
    try {
      const result = await api.documents.upload(conversationId, file);
      setAttachments((prev) => [...prev, result.document]);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to upload file."
      );
    } finally {
      setIsUploading(false);
    }
  };

  const handleRemoveAttachment = (docId: string) => {
    setAttachments((prev) => prev.filter((a) => a.id !== docId));
  };

  const handleSend = async (message: string, documentIds?: string[]) => {
    if (isSending) return;

    const userMessage = {
      id: `temp-${Date.now()}`,
      role: "user" as const,
      content: message,
      citations: [],
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsSending(true);
    setIsStreaming(true);
    setError(null);

    try {
      const response = await api.chat.send(
        message,
        conversationId,
        undefined,
        documentIds
      );

      const assistantMessage = {
        id: response.assistant_message_id,
        role: "assistant" as const,
        content: response.answer,
        agentKey: response.active_agent,
        citations: response.citations,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [
        ...prev.slice(0, -1),
        { ...prev[prev.length - 1], id: response.user_message_id },
        assistantMessage,
      ]);
      setAttachments([]);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to get response."
      );
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setIsSending(false);
      setIsStreaming(false);
    }
  };

  const handleStop = () => {
    setIsSending(false);
    setIsStreaming(false);
  };

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Chat header */}
      <div className="flex items-center gap-3 border-b border-border bg-surface px-4 py-3">
        <button
          onClick={() => router.push("/dashboard/history")}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-text-secondary hover:bg-muted"
          aria-label="Back to history"
        >
          <ArrowLeft className="h-4 w-4" />
        </button>
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-primary to-accent">
            <Bot className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-text-primary">
              SMIU AI Assistant
            </h1>
            <div className="flex items-center gap-1.5">
              <div className="h-1.5 w-1.5 rounded-full bg-success animate-pulse" />
              <span className="text-xs text-text-muted">Online</span>
            </div>
          </div>
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto scrollbar-thin">
        {error && (
          <div className="mx-auto max-w-3xl px-4 py-2">
            <div className="rounded-lg border border-danger/20 bg-danger/5 px-4 py-3 text-sm text-danger">
              {error}
              <button
                onClick={() => setError(null)}
                className="ml-2 font-medium underline"
              >
                Dismiss
              </button>
            </div>
          </div>
        )}

        <div className="mx-auto max-w-3xl py-4">
          {messages.map((msg) => (
            <ChatMessage
              key={msg.id}
              role={msg.role}
              content={msg.content}
              agentKey={msg.agentKey}
              citations={msg.citations}
              timestamp={msg.timestamp}
              messageId={msg.id}
            />
          ))}

          {/* Loading indicator */}
          {isSending && messages[messages.length - 1]?.role === "user" && (
            <div className="flex gap-3 px-4 py-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted">
                <Bot className="h-4 w-4 text-accent" />
              </div>
              <div className="rounded-xl border border-border bg-surface px-4 py-3 shadow-sm">
                <div className="flex items-center gap-1">
                  <div className="h-2 w-2 animate-bounce rounded-full bg-text-muted [animation-delay:-0.3s]" />
                  <div className="h-2 w-2 animate-bounce rounded-full bg-text-muted [animation-delay:-0.15s]" />
                  <div className="h-2 w-2 animate-bounce rounded-full bg-text-muted" />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input area */}
      <ChatInput
        onSend={handleSend}
        onStop={handleStop}
        disabled={isSending}
        isStreaming={isStreaming}
        attachments={attachments}
        onAttach={handleAttach}
        onRemoveAttachment={handleRemoveAttachment}
        isUploading={isUploading}
      />
    </div>
  );
}
