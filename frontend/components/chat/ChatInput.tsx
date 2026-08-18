"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Paperclip, Square, X, FileText, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { DocumentRead } from "@/types/api";

interface ChatInputProps {
  onSend: (message: string, documentIds?: string[]) => void;
  onStop?: () => void;
  disabled?: boolean;
  isStreaming?: boolean;
  placeholder?: string;
  attachments?: DocumentRead[];
  onAttach?: (file: File) => Promise<void>;
  onRemoveAttachment?: (docId: string) => void;
  isUploading?: boolean;
}

export default function ChatInput({
  onSend,
  onStop,
  disabled = false,
  isStreaming = false,
  placeholder = "Type your message...",
  attachments = [],
  onAttach,
  onRemoveAttachment,
  isUploading = false,
}: ChatInputProps) {
  const [message, setMessage] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const adjustHeight = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
  }, []);

  useEffect(() => {
    adjustHeight();
  }, [message, adjustHeight]);

  const handleSubmit = () => {
    const trimmed = message.trim();
    if (!trimmed || disabled) return;
    const docIds = attachments.map((a) => a.id);
    onSend(trimmed, docIds.length > 0 ? docIds : undefined);
    setMessage("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !onAttach) return;
    await onAttach(file);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const formatSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="border-t border-border bg-surface p-4">
      <div className="mx-auto max-w-3xl">
        {/* Attached files preview */}
        {attachments.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-2">
            {attachments.map((doc) => (
              <div
                key={doc.id}
                className={cn(
                  "flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs",
                  doc.status === "processed"
                    ? "border-success/30 bg-success/5 text-success"
                    : doc.status === "failed"
                      ? "border-danger/30 bg-danger/5 text-danger"
                      : "border-warning/30 bg-warning/5 text-warning"
                )}
              >
                <FileText className="h-3.5 w-3.5 flex-shrink-0" />
                <span className="max-w-[120px] truncate font-medium">
                  {doc.original_filename}
                </span>
                <span className="text-text-muted">
                  {formatSize(doc.size_bytes)}
                </span>
                {onRemoveAttachment && (
                  <button
                    onClick={() => onRemoveAttachment(doc.id)}
                    className="ml-0.5 flex h-4 w-4 items-center justify-center rounded-full text-text-muted hover:bg-muted hover:text-text-secondary"
                    aria-label={`Remove ${doc.original_filename}`}
                  >
                    <X className="h-3 w-3" />
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        <div className="flex items-end gap-2 rounded-xl border border-border bg-surface p-2 shadow-sm focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={handleFileSelect}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled || isUploading}
            className={cn(
              "flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg transition-colors",
              disabled || isUploading
                ? "text-text-muted opacity-50"
                : "text-text-muted hover:bg-muted hover:text-text-secondary"
            )}
            aria-label="Attach file"
          >
            {isUploading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Paperclip className="h-4 w-4" />
            )}
          </button>

          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled || isStreaming}
            rows={1}
            className="max-h-[200px] min-h-[36px] flex-1 resize-none bg-transparent py-2 text-sm text-text-primary placeholder-text-muted focus:outline-none disabled:opacity-50"
          />

          {isStreaming ? (
            <button
              onClick={onStop}
              className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-danger text-white hover:bg-danger/90"
              aria-label="Stop generating"
            >
              <Square className="h-4 w-4" />
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={!message.trim() || disabled}
              className={cn(
                "flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg transition-colors",
                message.trim() && !disabled
                  ? "bg-primary text-white hover:bg-primary-hover"
                  : "bg-muted text-text-muted"
              )}
              aria-label="Send message"
            >
              <Send className="h-4 w-4" />
            </button>
          )}
        </div>
        <p className="mt-2 text-center text-xs text-text-muted">
          Press Enter to send, Shift+Enter for a new line
        </p>
      </div>
    </div>
  );
}
