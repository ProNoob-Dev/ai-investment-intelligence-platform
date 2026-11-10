"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { loadPortfolio, sendChatMessage } from "@/lib/api/endpoints";
import { ChatBubble, TypingIndicator, WelcomeView } from "@/components/chat/ChatComponents";
import { Button } from "@/components/ui/ui";
import type { ChatMessageData } from "@/lib/types/chat";
import type { Goal } from "@/lib/types/portfolio";

const SESSION_ID = "default";

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessageData[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [portfolio, setPortfolio] = useState<Goal[]>([]);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    loadPortfolio("default").then((data) => setPortfolio(data.goals ?? [])).catch(() => undefined);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const ask = useCallback(
    async (text: string) => {
      const question = text.trim();
      if (!question || sending) return;
      setSending(true);
      setError(null);
      const userMsg: ChatMessageData = {
        role: "user",
        content: question,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      try {
        const res = await sendChatMessage({
          message: question,
          session_id: SESSION_ID,
          context_data: portfolio.length > 0 ? { portfolio } : undefined,
        });
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: res.content, timestamp: res.timestamp, data: res.data as any },
        ]);
      } catch (err) {
        setError(err instanceof Error ? err.message : "The assistant could not reply.");
      } finally {
        setSending(false);
      }
    },
    [sending, portfolio],
  );

  return (
    <div className="mx-auto flex max-w-3xl flex-col px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-medium tracking-tight sm:text-4xl">Research chat</h1>
      <p className="mt-3 max-w-2xl text-[17px] leading-relaxed text-muted">
        Ask about a stock, a comparison, or today’s opportunities. Answers use
        live prices and news, not memory.
      </p>

      {messages.length === 0 && !sending ? (
        <WelcomeView onAsk={ask} />
      ) : (
        <div className="mt-8 space-y-4">
          {messages.map((msg, i) => (
            <ChatBubble key={`${msg.timestamp}-${i}`} message={msg} />
          ))}
          {sending && <TypingIndicator />}
          <div ref={bottomRef} />
        </div>
      )}

      {error && (
        <div className="mt-4 rounded-sm border border-[#c2402a]/30 bg-[#c2402a]/[0.05] p-4" role="alert">
          <p className="text-sm text-[#c2402a]">{error}</p>
        </div>
      )}

      <form
        className="mt-8 flex gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          ask(input);
        }}
      >
        <label htmlFor="chat-input" className="sr-only">
          Ask the research assistant
        </label>
        <input
          id="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="How is RELIANCE doing?"
          autoComplete="off"
          className="h-12 flex-1 rounded-sm border border-ink/20 bg-white px-4 text-[15px] placeholder:text-muted focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
        />
        <Button type="submit" disabled={sending || !input.trim()}>
          {sending ? "Thinking…" : "Send"}
        </Button>
      </form>
      <p className="mt-3 font-mono text-xs text-muted">
        The assistant can analyse stocks, compare them, and summarise opportunities.
        It does not give personalised investment advice.
      </p>
    </div>
  );
}
