import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "RAG Chatbot",
  description: "Monorepo skeleton for a metadata-driven RAG chatbot.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
