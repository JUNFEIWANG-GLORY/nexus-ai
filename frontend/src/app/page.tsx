"use client";

import { useState, useEffect } from "react";

export default function Home() {
  const [topic, setTopic] = useState("");
  const [logs, setLogs] = useState<string[]>([]);
  const [report, setReport] = useState("");
  const [loading, setLoading] = useState(false);

  const startResearch = async () => {
    if (!topic) return;
    setLoading(true);
    setLogs([]);
    setReport("");

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const eventSource = new EventSource(
      `${apiUrl}/api/run-research?topic=${encodeURIComponent(topic)}`
    );

    eventSource.onmessage = (event) => {
      // 如果收到结束信号
      if (event.data.includes("[DONE]")) {
        eventSource.close();
        setLoading(false);
        return;
      }

      try {
        const parsed = JSON.parse(event.data);

        if (parsed.type === "log") {
          setLogs((prev) => [...prev, parsed.content]);
        } else if (parsed.type === "report") {
          setReport(parsed.content);
        }
      } catch (e) {
      }
    };

    eventSource.onerror = (err) => {
      console.error("SSE Error:", err);
      eventSource.close();
      setLoading(false);
    };
  };

  return (
    <main className="min-h-screen bg-gray-900 text-white p-8 font-sans">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-purple-500 text-transparent bg-clip-text">
          NexusAI Research Agent
        </h1>
        <p className="text-gray-400 mb-8">Autonomous Multi-Agent Workflow Engine</p>

        {/* Input Section */}
        <div className="flex gap-4 mb-8">
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="Enter a research topic (e.g., Solid State Batteries 2026)"
            className="flex-1 p-4 rounded-lg bg-gray-800 border border-gray-700 focus:border-blue-500 outline-none text-lg text-white"
          />
          <button
            onClick={startResearch}
            disabled={loading}
            className={`px-8 py-4 rounded-lg font-bold transition-all ${
              loading
                ? "bg-gray-600 cursor-not-allowed"
                : "bg-blue-600 hover:bg-blue-700 shadow-lg shadow-blue-500/20"
            }`}
          >
            {loading ? "Agents Working..." : "Start Research"}
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Logs Panel */}
          <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700 h-[500px] overflow-y-auto">
            <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
              <span className="text-green-400">●</span> Live Agent Logs
            </h2>
            <div className="space-y-3">
              {logs.map((log, index) => (
                <div
                  key={index}
                  className="p-3 bg-gray-900 rounded border-l-4 border-blue-500 text-sm font-mono text-gray-300 animate-pulse"
                >
                  {log}
                </div>
              ))}
              {loading && logs.length === 0 && (
                <div className="text-gray-500 text-sm animate-pulse">
                  Initializing agents...
                </div>
              )}
            </div>
          </div>

          {/* Report Panel */}
          <div className="bg-gray-800 rounded-xl p-6 border border-gray-700 h-[500px] overflow-y-auto shadow-2xl">
            <h2 className="text-xl font-semibold mb-4 text-purple-400">
              📄 Final Report
            </h2>
            {report ? (
              <div className="prose prose-invert max-w-none whitespace-pre-line text-gray-200">
                {report}
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-500">
                Waiting for agents to complete research...
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}