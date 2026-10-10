import { useEffect, useState } from "react";
import { fetchCourses, fetchStates } from "./api";
import Browse from "./components/Browse";
import Recommend from "./components/Recommend";
import AskAi from "./components/AskAi";
import ChatBot from "./components/ChatBot";

const TABS = [
  { id: "browse", label: "Browse colleges" },
  { id: "match", label: "Match my priorities" },
  { id: "ai", label: "Ask AI" },
];

export default function App() {
  const [tab, setTab] = useState("browse");
  const [states, setStates] = useState([]);
  const [courses, setCourses] = useState([]);

  // Dropdown values for both tabs, loaded once
  useEffect(() => {
    fetchStates().then(setStates).catch(() => {});
    fetchCourses().then(setCourses).catch(() => {});
  }, []);

  return (
    <div className="mx-auto max-w-6xl px-4 pb-16 pt-8 sm:px-6">
      <header className="border-b border-line pb-6">
        <h1 className="text-3xl font-bold tracking-tight">Find a college in India</h1>
        <p className="mt-2 max-w-xl text-muted">
          Search by name, state, course and fees, or tell us what matters most and we'll rank the best fits.
        </p>

        <div role="tablist" aria-label="Ways to search" className="mt-6 flex gap-1">
          {TABS.map((t) => (
            <button
              key={t.id}
              role="tab"
              id={`tab-${t.id}`}
              aria-selected={tab === t.id}
              aria-controls={`panel-${t.id}`}
              onClick={() => setTab(t.id)}
              className={
                "rounded-md px-4 py-2 text-sm font-semibold transition-colors " +
                "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent " +
                (tab === t.id ? "bg-ink text-white" : "text-muted hover:bg-white hover:text-ink")
              }
            >
              {t.label}
            </button>
          ))}
        </div>
      </header>

      {/* Both panels stay mounted so filters and results survive switching tabs */}
      <main className="pt-8">
        <div role="tabpanel" id="panel-browse" aria-labelledby="tab-browse" hidden={tab !== "browse"}>
          <Browse states={states} courses={courses} />
        </div>
        <div role="tabpanel" id="panel-match" aria-labelledby="tab-match" hidden={tab !== "match"}>
          <Recommend states={states} courses={courses} />
        </div>
        <div role="tabpanel" id="panel-ai" aria-labelledby="tab-ai" hidden={tab !== "ai"}>
          <AskAi states={states} courses={courses} />
        </div>
      </main>

      <ChatBot />
    </div>
  );
}
