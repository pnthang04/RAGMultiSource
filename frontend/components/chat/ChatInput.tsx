"use client";

import { useState } from "react";

import { ScopeSelector } from "@/components/documents/ScopeSelector";
import { RetrievalScope } from "@/lib/constants";

type Props = {
  onSend: (question: string, scope: RetrievalScope) => Promise<void>;
  defaultScope: RetrievalScope;
};

export function ChatInput({ onSend, defaultScope }: Props) {
  const [question, setQuestion] = useState("");
  const [scope, setScope] = useState<RetrievalScope>(defaultScope);

  return (
    <form
      className="stack"
      onSubmit={async (event) => {
        event.preventDefault();
        if (!question.trim()) return;
        await onSend(question.trim(), scope);
        setQuestion("");
      }}
    >
      <div className="field">
        <label>Question</label>
        <textarea className="textarea" value={question} onChange={(event) => setQuestion(event.target.value)} />
      </div>
      <ScopeSelector value={scope} onChange={setScope} />
      <button className="button" type="submit">
        Send
      </button>
    </form>
  );
}
