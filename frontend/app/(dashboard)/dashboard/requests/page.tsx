"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { RequestRead, PaginationMeta, DepartmentRead } from "@/types/api";
import {
  Search,
  PlusCircle,
  Filter,
  ChevronLeft,
  ChevronRight,
  Eye,
  Loader2,
  FileText,
  Send,
} from "lucide-react";

const STATUS_OPTIONS = [
  { value: "", label: "All Status" },
  { value: "draft", label: "Draft" },
  { value: "submitted", label: "Submitted" },
  { value: "in_review", label: "In Review" },
  { value: "assigned", label: "Assigned" },
  { value: "processing", label: "Processing" },
  { value: "resolved", label: "Resolved" },
  { value: "closed", label: "Closed" },
  { value: "rejected", label: "Rejected" },
];

const STATUS_COLORS: Record<string, string> = {
  draft: "bg-gray-100 text-gray-700",
  submitted: "bg-blue-100 text-blue-700",
  in_review: "bg-yellow-100 text-yellow-700",
  assigned: "bg-purple-100 text-purple-700",
  processing: "bg-indigo-100 text-indigo-700",
  resolved: "bg-green-100 text-green-700",
  closed: "bg-gray-100 text-gray-500",
  rejected: "bg-red-100 text-red-700",
};

const PRIORITY_COLORS: Record<string, string> = {
  critical: "text-red-600",
  high: "text-orange-500",
  medium: "text-blue-500",
  low: "text-gray-400",
};

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function MyRequestsPage() {
  const [requests, setRequests] = useState<RequestRead[]>([]);
  const [departments, setDepartments] = useState<DepartmentRead[]>([]);
  const [pagination, setPagination] = useState<PaginationMeta | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [submittingId, setSubmittingId] = useState<string | null>(null);

  useEffect(() => {
    api.departments.list().then(setDepartments).catch(() => {});
  }, []);

  const deptMap = useCallback(
    (id: string | null) => {
      if (!id) return "—";
      return departments.find((d) => d.id === id)?.name || "—";
    },
    [departments]
  );

  const fetchRequests = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const result = await api.requests.list(currentPage, 10, statusFilter || undefined);
      let filtered = result.data;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        filtered = filtered.filter(
          (r) =>
            r.title.toLowerCase().includes(q) ||
            r.request_no.toLowerCase().includes(q)
        );
      }
      setRequests(filtered);
      setPagination(result.pagination);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load requests");
    } finally {
      setLoading(false);
    }
  }, [currentPage, statusFilter, searchQuery]);

  useEffect(() => {
    fetchRequests();
  }, [fetchRequests]);

  const handleSubmit = async (id: string) => {
    setSubmittingId(id);
    try {
      await api.requests.submit(id);
      fetchRequests();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit request.");
    } finally {
      setSubmittingId(null);
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">My Requests</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Manage and track your submitted requests
          </p>
        </div>
        <Link
          href="/dashboard/requests/new"
          className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-hover transition-colors"
        >
          <PlusCircle className="h-4 w-4" />
          New Request
        </Link>
      </div>

      {/* Filters */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            placeholder="Search by title or request number..."
            className="h-10 w-full rounded-lg border border-border bg-surface pl-10 pr-4 text-sm text-text-primary placeholder-text-muted focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          />
        </div>
        <div className="relative">
          <Filter className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
          <select
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="h-10 appearance-none rounded-lg border border-border bg-surface pl-10 pr-10 text-sm text-text-primary focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <div className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2">
            <svg className="h-4 w-4 text-text-muted" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clipRule="evenodd" />
            </svg>
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-danger/20 bg-danger/5 px-4 py-3 text-sm text-danger">
          {error}
          <button onClick={fetchRequests} className="ml-2 font-medium underline">
            Retry
          </button>
        </div>
      )}

      {/* Loading */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      ) : requests.length === 0 ? (
        /* Empty State */
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
            <FileText className="h-8 w-8 text-text-muted" />
          </div>
          <h3 className="mt-4 text-lg font-semibold text-text-primary">No requests found</h3>
          <p className="mt-1 max-w-sm text-sm text-text-secondary">
            {searchQuery || statusFilter
              ? "Try adjusting your search or filters."
              : "Create your first request to get started."}
          </p>
          {!searchQuery && !statusFilter && (
            <Link
              href="/dashboard/requests/new"
              className="mt-6 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover"
            >
              <PlusCircle className="h-4 w-4" />
              New Request
            </Link>
          )}
        </div>
      ) : (
        /* Table */
        <>
          <div className="overflow-x-auto rounded-xl border border-border bg-surface shadow-sm">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-border bg-muted/50">
                <tr>
                  <th className="px-5 py-3 font-medium text-text-secondary">Request</th>
                  <th className="hidden px-5 py-3 font-medium text-text-secondary sm:table-cell">Department</th>
                  <th className="hidden px-5 py-3 font-medium text-text-secondary md:table-cell">Priority</th>
                  <th className="px-5 py-3 font-medium text-text-secondary">Status</th>
                  <th className="hidden px-5 py-3 font-medium text-text-secondary lg:table-cell">Date</th>
                  <th className="px-5 py-3 font-medium text-text-secondary">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {requests.map((req) => (
                  <tr key={req.id} className="hover:bg-muted/30">
                    <td className="px-5 py-3">
                      <p className="font-medium text-text-primary truncate max-w-[200px]">{req.title}</p>
                      <p className="text-xs text-text-muted">{req.request_no}</p>
                    </td>
                    <td className="hidden px-5 py-3 text-text-secondary sm:table-cell">
                      {deptMap(req.department_id)}
                    </td>
                    <td className="hidden px-5 py-3 md:table-cell">
                      <span className={`text-xs font-medium capitalize ${PRIORITY_COLORS[req.priority] || ""}`}>
                        {req.priority}
                      </span>
                    </td>
                    <td className="px-5 py-3">
                      <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLORS[req.status] || "bg-gray-100 text-gray-700"}`}>
                        {req.status.replace("_", " ")}
                      </span>
                    </td>
                    <td className="hidden px-5 py-3 text-text-secondary lg:table-cell">
                      {formatDate(req.created_at)}
                    </td>
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-1">
                        {req.status === "draft" && (
                          <button
                            onClick={() => handleSubmit(req.id)}
                            disabled={submittingId === req.id}
                            className="flex h-8 w-8 items-center justify-center rounded-lg text-text-muted hover:bg-success/10 hover:text-success disabled:opacity-50"
                            title="Submit request"
                          >
                            {submittingId === req.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Send className="h-4 w-4" />
                            )}
                          </button>
                        )}
                        <Link
                          href={`/dashboard/requests/${req.id}`}
                          className="flex h-8 w-8 items-center justify-center rounded-lg text-text-muted hover:bg-muted hover:text-primary"
                          title="View details"
                        >
                          <Eye className="h-4 w-4" />
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {pagination && pagination.total_pages > 1 && (
            <div className="flex items-center justify-between">
              <p className="text-sm text-text-secondary">
                Showing {((pagination.page - 1) * pagination.limit) + 1} to{" "}
                {Math.min(pagination.page * pagination.limit, pagination.total)} of{" "}
                {pagination.total} requests
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="flex h-9 w-9 items-center justify-center rounded-lg border border-border text-text-secondary hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                {Array.from({ length: Math.min(pagination.total_pages, 5) }, (_, i) => {
                  const page = i + 1;
                  return (
                    <button
                      key={page}
                      onClick={() => setCurrentPage(page)}
                      className={`flex h-9 w-9 items-center justify-center rounded-lg text-sm font-medium ${
                        currentPage === page
                          ? "bg-primary text-white"
                          : "border border-border text-text-secondary hover:bg-muted"
                      }`}
                    >
                      {page}
                    </button>
                  );
                })}
                <button
                  onClick={() => setCurrentPage((p) => Math.min(pagination.total_pages, p + 1))}
                  disabled={currentPage === pagination.total_pages}
                  className="flex h-9 w-9 items-center justify-center rounded-lg border border-border text-text-secondary hover:bg-muted disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
