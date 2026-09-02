import type {
  ChatResponse,
  ConversationRead,
  DepartmentRead,
  DocumentRead,
  DocumentUploadResponse,
  MessageRead,
  NotificationRead,
  PaginationMeta,
  RequestCreate,
  RequestRead,
  StudentDashboardRead,
  StudentRead,
  SuccessResponse,
  TokenResponse,
  UnreadCountRead,
  UserRead,
} from "@/types/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("smiu_access_token");
}

function setTokens(access: string, refresh: string): void {
  localStorage.setItem("smiu_access_token", access);
  localStorage.setItem("smiu_refresh_token", refresh);
}

function clearTokens(): void {
  localStorage.removeItem("smiu_access_token");
  localStorage.removeItem("smiu_refresh_token");
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const isFormData = options.body instanceof FormData;
  const headers: Record<string, string> = {
    ...(!isFormData ? { "Content-Type": "application/json" } : {}),
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      headers["Authorization"] = `Bearer ${getToken()}`;
      const retryRes = await fetch(`${API_URL}${path}`, { ...options, headers });
      if (!retryRes.ok) {
        const body = await retryRes.json().catch(() => ({}));
        throw new ApiError(retryRes.status, body?.error?.message || body?.message || `Request failed (${retryRes.status})`);
      }
      const body = await retryRes.json() as SuccessResponse<T>;
      return body.data;
    }
    clearTokens();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
    throw new ApiError(401, "Session expired");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body?.error?.message || body?.message || `Request failed (${res.status})`);
  }

  const body = await res.json() as SuccessResponse<T>;
  return body.data;
}

interface RawSuccessResponse<T> {
  success: boolean;
  data: T;
  meta?: {
    request_id?: string;
    timestamp?: string;
    pagination?: {
      page: number;
      limit: number;
      offset: number;
      total: number;
      total_pages: number;
      next_page: number | null;
      prev_page: number | null;
    };
  };
}

async function requestPaginated<T>(
  path: string,
  options: RequestInit = {}
): Promise<{ data: T; pagination: PaginationMeta | null }> {
  const token = getToken();
  const isFormData = options.body instanceof FormData;
  const headers: Record<string, string> = {
    ...(!isFormData ? { "Content-Type": "application/json" } : {}),
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (res.status === 401) {
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      headers["Authorization"] = `Bearer ${getToken()}`;
      const retryRes = await fetch(`${API_URL}${path}`, { ...options, headers });
      if (!retryRes.ok) {
        const body = await retryRes.json().catch(() => ({}));
        throw new ApiError(retryRes.status, body?.error?.message || body?.message || `Request failed (${retryRes.status})`);
      }
      const body = await retryRes.json() as RawSuccessResponse<T>;
      const raw = body.meta?.pagination;
      const pagination: PaginationMeta | null = raw
        ? { page: raw.page, limit: raw.limit, total: raw.total, total_pages: raw.total_pages }
        : null;
      return { data: body.data, pagination };
    }
    clearTokens();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
    throw new ApiError(401, "Session expired");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body?.error?.message || body?.message || `Request failed (${res.status})`);
  }

  const body = await res.json() as RawSuccessResponse<T>;
  const raw = body.meta?.pagination;
  const pagination: PaginationMeta | null = raw
    ? { page: raw.page, limit: raw.limit, total: raw.total, total_pages: raw.total_pages }
    : null;
  return { data: body.data, pagination };
}

async function tryRefreshToken(): Promise<boolean> {
  const refreshToken = localStorage.getItem("smiu_refresh_token");
  if (!refreshToken) return false;
  try {
    const res = await fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return false;
    const body = await res.json() as SuccessResponse<TokenResponse>;
    setTokens(body.data.access_token, body.data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

export const api = {
  auth: {
    login: async (email: string, password: string, rememberMe = false) => {
      const data = await request<TokenResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password, remember_me: rememberMe }),
      });
      setTokens(data.access_token, data.refresh_token);
      return data;
    },
    register: async (payload: {
      email: string;
      password: string;
      full_name: string;
      enrollment_no?: string;
      department_id?: string;
      program_name?: string;
    }) => {
      return request<UserRead>("/auth/register", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    logout: async () => {
      const refreshToken = localStorage.getItem("smiu_refresh_token");
      if (refreshToken) {
        try {
          await request<null>("/auth/logout", {
            method: "POST",
            body: JSON.stringify({ refresh_token: refreshToken }),
          });
        } catch { /* ignore */ }
      }
      clearTokens();
    },
    getMe: async () => {
      return request<UserRead>("/users/me");
    },
    forgotPassword: async (email: string) => {
      return request<{ message: string }>("/auth/forgot-password", {
        method: "POST",
        body: JSON.stringify({ email }),
      });
    },
  },

  departments: {
    list: async () => {
      return request<DepartmentRead[]>("/departments");
    },
  },

  students: {
    getMe: async () => {
      return request<StudentRead>("/students/me");
    },
    getDashboard: async () => {
      return request<StudentDashboardRead>("/students/me/dashboard");
    },
  },

  requests: {
    list: async (page = 1, limit = 20, status?: string) => {
      const params = new URLSearchParams({ page: String(page), limit: String(limit) });
      if (status) params.set("request_status", status);
      return requestPaginated<RequestRead[]>(`/requests?${params.toString()}`);
    },
    create: async (payload: RequestCreate) => {
      return request<RequestRead>("/requests", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    get: async (id: string) => {
      return request<RequestRead>(`/requests/${id}`);
    },
    submit: async (id: string) => {
      return request<RequestRead>(`/requests/${id}/submit`, {
        method: "POST",
      });
    },
  },

  notifications: {
    list: async (page = 1, limit = 20, read?: boolean) => {
      const params = new URLSearchParams({ page: String(page), limit: String(limit) });
      if (read !== undefined) params.set("read", String(read));
      return requestPaginated<NotificationRead[]>(`/notifications?${params.toString()}`);
    },
    unreadCount: async () => {
      return request<UnreadCountRead>("/notifications/unread-count");
    },
    markAllRead: async () => {
      return request<{ marked: number }>("/notifications/read-all", { method: "POST" });
    },
    markRead: async (id: string) => {
      return request<NotificationRead>(`/notifications/${id}/read`, { method: "POST" });
    },
  },

  chat: {
    send: async (message: string, conversationId?: string, departmentId?: string, documentIds?: string[]) => {
      return request<ChatResponse>("/ai/chat", {
        method: "POST",
        body: JSON.stringify({
          message,
          conversation_id: conversationId || null,
          department_id: departmentId || null,
          document_ids: documentIds || [],
        }),
      });
    },
    getSources: async (messageId: string) => {
      return request<import("@/types/api").ChatCitationRead[]>(`/ai/sources/${messageId}`);
    },
    feedback: async (
      sentiment: "positive" | "negative",
      comment?: string,
      messageId?: string,
      conversationId?: string
    ) => {
      return request<import("@/types/api").FeedbackRead>("/ai/feedback", {
        method: "POST",
        body: JSON.stringify({
          message_id: messageId || null,
          conversation_id: conversationId || null,
          sentiment,
          comment: comment || null,
        }),
      });
    },
  },

  documents: {
    upload: async (conversationId: string, file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return request<DocumentUploadResponse>(`/conversations/${conversationId}/attachments`, {
        method: "POST",
        body: formData,
      });
    },
    uploadStandalone: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return request<DocumentUploadResponse>("/documents/upload", {
        method: "POST",
        body: formData,
      });
    },
    list: async (conversationId: string) => {
      return request<DocumentRead[]>(`/conversations/${conversationId}/attachments`);
    },
  },

  conversations: {
    list: async (page = 1, limit = 20) => {
      return request<ConversationRead[]>(`/conversations?page=${page}&limit=${limit}`);
    },
    get: async (id: string) => {
      return request<ConversationRead>(`/conversations/${id}`);
    },
    update: async (id: string, data: { title?: string }) => {
      return request<ConversationRead>(`/conversations/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      });
    },
    delete: async (id: string) => {
      return request<ConversationRead>(`/conversations/${id}`, {
        method: "DELETE",
      });
    },
    archive: async (id: string) => {
      return request<ConversationRead>(`/conversations/${id}/archive`, {
        method: "POST",
      });
    },
    restore: async (id: string) => {
      return request<ConversationRead>(`/conversations/${id}/restore`, {
        method: "POST",
      });
    },
  },

  messages: {
    list: async (conversationId: string, limit = 50) => {
      return request<MessageRead[]>(`/conversations/${conversationId}/messages?limit=${limit}`);
    },
  },
};

export { ApiError, getToken, setTokens, clearTokens };
