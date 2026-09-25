const API_BASE = '/api';

export interface SessionResponse {
  session_id: string;
  topic: string;
  category: string;
  papers: Array<{
    title: string;
    arxiv_id: string;
    status: string;
  }>;
  ingestion_status?: string;
}

export interface Citation {
  source: string;
  source_id: string;
  paper_id: string;
  title: string;
  content: string;
  section?: string;
  page?: number;
  score: number;
  citation_label: string;
  metadata?: {
    title: string;
    arxiv_id?: string;
    page?: number;
    chunk_text?: string;
  };
}

export interface ChatQueryResponse {
  answer: string;
  citations: Citation[];
  repos: Array<{ url: string; name: string }>;
  recommendations: string[];
  drift_warning?: string;
}

export interface EndSessionResponse {
  session_id: string;
  category: string;
  status: string;
}

export async function startSession(topic: string): Promise<SessionResponse> {
  const res = await fetch(`${API_BASE}/chat/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ topic }),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || 'Failed to start session');
  }
  return res.json();
}

export async function sendQuery(
  sessionId: string,
  question: string,
  topK: number = 8
): Promise<ChatQueryResponse> {
  const res = await fetch(`${API_BASE}/chat/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question,
      session_id: sessionId,
      top_k: topK,
    }),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || 'Failed to send query');
  }
  return res.json();
}

export async function endSession(sessionId: string): Promise<EndSessionResponse> {
  const res = await fetch(`${API_BASE}/chat/sessions/${sessionId}/end`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || 'Failed to end session');
  }
  return res.json();
}

export async function getSession(sessionId: string): Promise<SessionResponse> {
  const res = await fetch(`${API_BASE}/chat/sessions/${sessionId}`);
  if (!res.ok) {
    const err = await res.text();
    throw new Error(err || 'Failed to fetch session');
  }
  return res.json();
}
