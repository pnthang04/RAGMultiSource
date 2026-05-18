import Link from "next/link";

export default function HomePage() {
  return (
    <main className="page-shell">
      <div className="topbar">
        <div>
          <div className="brand">RAG Chatbot</div>
          <div className="muted">FastAPI + Next.js + MongoDB + Chroma</div>
        </div>
        <nav className="nav">
          <Link href="/chat">Chat</Link>
          <Link href="/documents">Documents</Link>
        </nav>
      </div>
      <section className="card">
        <h1>Metadata-first retrieval</h1>
        <p className="muted">
          System documents and user uploads are separated by metadata filters. Chunks carry document_id, chunk_id,
          source_type, owner_user_id, session_id, filename, page_number, section_title, and visibility.
        </p>
      </section>
    </main>
  );
}
