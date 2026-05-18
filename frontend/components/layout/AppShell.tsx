"use client";

import type { PropsWithChildren } from "react";
import Link from "next/link";

export function AppShell({ children }: PropsWithChildren) {
  return (
    <main className="page-shell">
      <header className="topbar">
        <div>
          <div className="brand">RAG Chatbot</div>
          <div className="muted">Monorepo scaffold</div>
        </div>
        <nav className="nav">
          <Link href="/">Home</Link>
          <Link href="/chat">Chat</Link>
          <Link href="/documents">Documents</Link>
        </nav>
      </header>
      {children}
    </main>
  );
}
