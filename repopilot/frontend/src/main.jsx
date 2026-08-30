import React, { useEffect, useState } from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import ChatPage from "./pages/ChatPage";
import DashboardPage from "./pages/DashboardPage";
import LandingPage from "./pages/LandingPage";
import "./index.css";

function useTheme() {
  const [theme, setTheme] = useState(() => {
    const stored = localStorage.getItem("theme");
    if (stored) return stored;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem("theme", theme);
  }, [theme]);

  return [theme, setTheme];
}

function NavBar({ theme, onToggleTheme }) {
  const location = useLocation();
  const linkClass = (path) =>
    `px-3 py-2 rounded-md text-sm font-medium ${
      location.pathname === path
        ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
        : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
    }`;
  return (
    <nav className="border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      <div className="max-w-5xl mx-auto px-4 py-3 flex items-center gap-4">
        <Link to="/" className="font-semibold text-slate-900 dark:text-slate-100">RepoPilot</Link>
        <Link className={linkClass("/chat")} to="/chat">Chat</Link>
        <Link className={linkClass("/dashboard")} to="/dashboard">Dashboard</Link>
        <button
          onClick={onToggleTheme}
          title="Toggle theme"
          className="ml-auto text-sm px-2 py-1 rounded-md text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
        >
          {theme === "dark" ? "☀️" : "🌙"}
        </button>
      </div>
    </nav>
  );
}

function App() {
  const [theme, setTheme] = useTheme();
  return (
    <BrowserRouter>
      <NavBar theme={theme} onToggleTheme={() => setTheme((t) => (t === "dark" ? "light" : "dark"))} />
      <div className="max-w-5xl mx-auto px-4 py-6">
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
