import { useEffect, useRef, useState } from "react";
import { sendChat } from "../api";

const SUGGESTIONS = [
  "Which colleges have the best placements under ₹2 lakh fees?",
  "Compare Amity Noida and Galgotias",
  "Cheapest good college in Lucknow?",
];

const GREETING = {
  role: "assistant",
  content: "Hi! Ask me about the private B.Tech colleges in Uttar Pradesh: fees, placements, ratings, or which one suits you.",
};

// Keep the request small: the backend accepts at most 20 messages
const HISTORY_LIMIT = 12;

export default function ChatBot() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([GREETING]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [messages, loading, open]);

  async function send(text) {
    const content = text.trim();
    if (!content || loading) return;
    const next = [...messages, { role: "user", content }];
    setMessages(next);
    setInput("");
    setError("");
    setLoading(true);
    try {
      // The greeting is UI only, so it is not sent
      const history = next.slice(1).slice(-HISTORY_LIMIT);
      const { reply } = await sendChat(history);
      setMessages([...next, { role: "assistant", content: reply }]);
    } catch (err) {
      setError(err.response?.data?.message || "Could not reach the backend on port 8080.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      {open && (
        <section
          aria-label="College assistant chat"
          className="fixed bottom-20 right-4 z-50 flex h-[32rem] max-h-[calc(100vh-7rem)] w-[calc(100vw-2rem)] max-w-sm flex-col overflow-hidden rounded-lg border border-line bg-white shadow-xl sm:right-6"
        >
          <header className="flex items-center justify-between bg-ink px-4 py-3 text-white">
            <h2 className="text-sm font-semibold">College assistant</h2>
            <button
              onClick={() => setOpen(false)}
              aria-label="Close chat"
              className="rounded px-2 text-lg leading-none hover:bg-white/10 focus-visible:outline-2 focus-visible:outline-white"
            >
              ×
            </button>
          </header>

          <div className="flex-1 space-y-3 overflow-y-auto bg-paper p-4 text-sm" aria-live="polite">
            {messages.map((m, i) => (
              <div key={i} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
                <p
                  className={
                    "max-w-[85%] whitespace-pre-wrap rounded-lg px-3 py-2 leading-relaxed " +
                    (m.role === "user" ? "bg-accent text-white" : "border border-line bg-white")
                  }
                >
                  {m.content}
                </p>
              </div>
            ))}

            {messages.length === 1 && (
              <div className="flex flex-col items-start gap-2 pt-1">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="rounded-full border border-line bg-white px-3 py-1.5 text-left text-xs text-muted hover:border-accent hover:text-ink focus-visible:outline-2 focus-visible:outline-accent"
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}

            {loading && <p className="text-muted">Thinking…</p>}
            {error && (
              <p className="rounded-md border border-red-200 bg-red-50 p-3 text-red-800" role="alert">
                {error}
              </p>
            )}
            <div ref={bottomRef} />
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
            className="flex gap-2 border-t border-line bg-white p-3"
          >
            <label htmlFor="chat-input" className="sr-only">
              Your question
            </label>
            <input
              id="chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              maxLength={500}
              placeholder="Ask about colleges…"
              className="min-w-0 flex-1 rounded-md border border-line px-3 py-2 text-sm focus-visible:outline-2 focus-visible:outline-accent"
            />
            <button
              type="submit"
              disabled={!input.trim() || loading}
              className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent-dark focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-40"
            >
              Send
            </button>
          </form>
        </section>
      )}

      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="fixed bottom-4 right-4 z-50 rounded-full bg-accent px-5 py-3 text-sm font-semibold text-white shadow-lg hover:bg-accent-dark focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent sm:right-6"
      >
        {open ? "Close chat" : "Chat with us"}
      </button>
    </>
  );
}
