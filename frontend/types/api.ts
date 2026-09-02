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

export interface FeedbackRead {
  id: string;
  user_id: string;
  message_id: string | null;
  conversation_id: string | null;
  feedback_type: string;
  rating: number | null;
  comment: string | null;
  sentiment: string | null;
  status: string;
  created_at: string;
}

export interface PaginationMeta {
  page: number;
  limit: number;
  total: number;
  total_pages: number;
}

export interface SuccessResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}

export interface DepartmentRead {
  id: string;
  code: string;
  name: string;
}

export interface StudentRead {
  id: string;
  user_id: string;
  enrollment_no: string;
  department_id: string | null;
  program_name: string | null;
  program_level: string | null;
  admission_year: number | null;
  batch_year: number | null;
  current_semester: number | null;
  section: string | null;
  cgpa: number | null;
  credit_hours_completed: number | null;
  status: string;
  cnic: string | null;
  date_of_birth: string | null;
  gender: string | null;
  nationality: string | null;
  address: string | null;
  phone: string | null;
  guardian_name: string | null;
  guardian_phone: string | null;
  guardian_relation: string | null;
  emergency_contact_name: string | null;
  emergency_contact_phone: string | null;
  created_at: string;
  updated_at: string;
}

export interface StudentDashboardRead {
  active_requests: number;
  pending_requests: number;
  resolved_requests: number;
  unread_notifications: number;
}

export type RequestType = "admission" | "examination" | "general" | "other";
export type RequestStatus = "draft" | "submitted" | "in_review" | "assigned" | "processing" | "resolved" | "closed" | "rejected";
export type RequestPriority = "critical" | "high" | "medium" | "low";

export interface RequestRead {
  id: string;
  request_no: string;
  user_id: string;
  department_id: string | null;
  request_type: RequestType;
  category: string | null;
  priority: RequestPriority;
  status: RequestStatus;
  title: string;
  description: string | null;
  source: string;
  conversation_id: string | null;
  assigned_to: string | null;
  due_date: string | null;
  resolution_notes: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  rejected_at: string | null;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface RequestCreate {
  request_type: RequestType;
  title: string;
  category?: string;
  department_id?: string;
  description?: string;
  priority?: RequestPriority;
  status?: RequestStatus;
}

export type NotificationType = "request" | "ai" | "system";
export type NotificationPriority = "critical" | "high" | "medium" | "low";

export interface NotificationRead {
  id: string;
  user_id: string;
  request_id: string | null;
  type: NotificationType;
  priority: NotificationPriority;
  title: string;
  body: string | null;
  link: string | null;
  icon: string | null;
  read_at: string | null;
  delivered_at: string | null;
  created_at: string;
}

export interface UnreadCountRead {
  unread: number;
}
