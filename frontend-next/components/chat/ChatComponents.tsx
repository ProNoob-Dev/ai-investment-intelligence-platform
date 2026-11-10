"use client";

import { cn } from "@/lib/utils/cn";
import type { ChatMessageData } from "@/lib/types/chat";

export function ChatBubble({ message }: { message: ChatMessageData }) {
  const isUser = message.role === "user";
  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[85%] rounded-sm px-4 py-3 text-[15px] leading-relaxed",
          isUser ? "bg-ink text-paper" : "border border-ink/10 bg-white",
        )}
      >
        <p className="whitespace-pre-line">{message.content}</p>
        {message.data && typeof message.data === "object" && "ticker" in message.data && (
          <p className="mt-2 border-t border-ink/10 pt-2 font-mono text-xs text-muted">
            {String(message.data.ticker)} · sentiment{" "}
            {Number((message.data as any).sentiment ?? 0).toFixed(2)} ·{" "}
            {String((message.data as any).recommendation ?? "")}
          </p>
        )}
      </div>
    </div>
  );
}

export function TypingIndicator() {
  return (
    <div className="flex justify-start" aria-label="Assistant is typing">
      <div className="rounded-sm border border-ink/10 bg-white px-4 py-3">
        <span className="flex gap-1">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="h-2 w-2 animate-bounce rounded-full bg-muted"
              style={{ animationDelay: `${i * 0.15}s` }}
            />
          ))}
        </span>
      </div>
    </div>
  );
}

export function WelcomeView({ onAsk }: { onAsk: (question: string) => void }) {
  const prompts = [
    "How is RELIANCE doing?",
    "Compare TCS and INFY",
    "What opportunities are there today?",
    "How is my portfolio doing?",
  ];
  return (
    <div className="py-8 text-center">
      <p className="font-display text-2xl font-medium">Ask about any Indian stock</p>
      <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-muted">
        The assistant fetches live prices, news sentiment and opportunities, then
        explains them in plain language.
      </p>
      <div className="mt-6 flex flex-wrap justify-center gap-2">
        {prompts.map((prompt) => (
          <button
            key={prompt}
            type="button"
            onClick={() => onAsk(prompt)}
            className="rounded-sm border border-ink/15 bg-white px-3 py-2 text-sm transition-colors hover:border-accent hover:text-accent"
          >
            {prompt}
          </button>
        ))}
      </div>
    </div>
  );
}
