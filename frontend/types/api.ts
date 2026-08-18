export interface UserRead {
  id: string;
  email: string;
  full_name: string;
  role: "student" | "admin" | "faculty";
  status: "active" | "inactive" | "suspended" | "pending";
  email_verified_at: string | null;
  phone: string | null;
  avatar_url: string | null;
  last_login_at: string | null;
  locale: string;
  preferences: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  refresh_expires_in: number;
  user: UserRead;
}

export interface ConversationRead {
  id: string;
  user_id: string;
  department_id: string | null;
  title: string | null;
  summary: string | null;
  status: "active" | "archived";
  current_agent: string | null;
  message_count: number;
  total_tokens: number;
  started_at: string;
  last_message_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface MessageRead {
  id: string;
  conversation_id: string;
  parent_message_id: string | null;
  role: "user" | "assistant" | "system" | "tool";
  agent_key: string | null;
  content: string;
  content_format: string;
  status: "queued" | "streaming" | "completed" | "error" | "stopped";
  model: string | null;
  token_usage: Record<string, unknown> | null;
  latency_ms: number | null;
  error_code: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatResponse {
  conversation_id: string;
  user_message_id: string;
  assistant_message_id: string;
  answer: string;
  status: string;
  active_agent: string | null;
  handoff: {
    routed_to: string;
    previous_agent: string;
    reason: string | null;
  } | null;
  citations: ChatCitationRead[];
}

export interface DocumentRead {
  id: string;
  user_id: string | null;
  conversation_id: string | null;
  category: string;
  original_filename: string;
  content_type: string | null;
  size_bytes: number;
  status: "pending" | "processed" | "failed";
  created_at: string;
  updated_at: string;
}

export interface DocumentUploadResponse {
  document: DocumentRead;
  message: string;
}

export interface ChatCitationRead {
  source_title: string;
  source_url: string | null;
  category: string | null;
  snippet: string | null;
  relevance_score: number | null;
  knowledge_document_id: string | null;
  knowledge_chunk_id: string | null;
}

export interface PaginationMeta {
  page: number;
  limit: number;
  total_items: number;
  total_pages: number;
}

export interface SuccessResponse<T> {
  success: boolean;
  data: T;
  message?: string;
  pagination?: PaginationMeta;
}
