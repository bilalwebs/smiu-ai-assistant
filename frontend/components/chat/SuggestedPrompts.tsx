"use client";

import { GraduationCap, FileText, HelpCircle, MessageSquare } from "lucide-react";

interface SuggestedPromptsProps {
  onSelect: (prompt: string) => void;
}

const PROMPTS = [
  {
    icon: GraduationCap,
    label: "Admissions",
    question: "What are the admission requirements for undergraduate programs at SMIU?",
  },
  {
    icon: FileText,
    label: "Exams",
    question: "When are the upcoming examination dates and how can I check my results?",
  },
  {
    icon: HelpCircle,
    label: "FAQ",
    question: "What are the office timings and how do I contact student affairs?",
  },
  {
    icon: MessageSquare,
    label: "General",
    question: "How can I submit a request to the university administration?",
  },
];

export default function SuggestedPrompts({ onSelect }: SuggestedPromptsProps) {
  return (
    <div className="flex flex-col items-center justify-center px-4 py-8">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary-soft">
        <MessageSquare className="h-8 w-8 text-primary" />
      </div>
      <h2 className="mt-4 text-xl font-semibold text-text-primary">
        What can I help you with today?
      </h2>
      <p className="mt-1 text-sm text-text-secondary">
        Ask about admissions, exams, or anything university-related.
      </p>

      <div className="mt-6 grid w-full max-w-lg grid-cols-1 gap-2 sm:grid-cols-2">
        {PROMPTS.map((prompt) => (
          <button
            key={prompt.label}
            onClick={() => onSelect(prompt.question)}
            className="flex items-start gap-3 rounded-xl border border-border bg-surface p-3 text-left shadow-sm transition-all hover:border-primary hover:shadow-md"
          >
            <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-primary-soft">
              <prompt.icon className="h-4 w-4 text-primary" />
            </div>
            <div>
              <p className="text-sm font-medium text-text-primary">{prompt.label}</p>
              <p className="mt-0.5 text-xs text-text-secondary line-clamp-2">
                {prompt.question}
              </p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
