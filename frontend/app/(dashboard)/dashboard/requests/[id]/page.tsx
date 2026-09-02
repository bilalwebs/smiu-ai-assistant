"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api, ApiError } from "@/lib/api";
import type { RequestRead, DepartmentRead } from "@/types/api";
import {
  ArrowLeft,
  Loader2,
  FileText,
  Calendar,
  Building2,
  Tag,
  AlertCircle,
  Clock,
  CheckCircle2,
  XCircle,
} from "lucide-react";

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: React.ElementType }> = {
  draft: { label: "Draft", color: "bg-gray-100 text-gray-700", icon: FileText },
  submitted: { label: "Submitted", color: "bg-blue-100 text-blue-700", icon: Clock },
  in_review: { label: "In Review", color: "bg-yellow-100 text-yellow-700", icon: Clock },
  assigned: { label: "Assigned", color: "bg-purple-100 text-purple-700", icon: Clock },
  processing: { label: "Processing", color: "bg-indigo-100 text-indigo-700", icon: Clock },
  resolved: { label: "Resolved", color: "bg-green-100 text-green-700", icon: CheckCircle2 },
  closed: { label: "Closed", color: "bg-gray-100 text-gray-500", icon: XCircle },
  rejected: { label: "Rejected", color: "bg-red-100 text-red-700", icon: XCircle },
};

const PRIORITY_CONFIG: Record<string, { label: string; color: string }> = {
  critical: { label: "Critical", color: "text-red-600 bg-red-50" },
  high: { label: "High", color: "text-orange-600 bg-orange-50" },
  medium: { label: "Medium", color: "text-blue-600 bg-blue-50" },
  low: { label: "Low", color: "text-gray-500 bg-gray-50" },
};

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function RequestDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [request, setRequest] = useState<RequestRead | null>(null);
  const [departmentName, setDepartmentName] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;

    const fetchRequest = async () => {
      try {
        const data = await api.requests.get(id);
        setRequest(data);

        if (data.department_id) {
          try {
            const departments = await api.departments.list();
            const dept = departments.find((d) => d.id === data.department_id);
            setDepartmentName(dept?.name || null);
          } catch {
            // departments fetch is optional
          }
        }
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) {
          setError("You do not have permission to view this request.");
        } else if (err instanceof ApiError && err.status === 404) {
          setError("Request not found.");
        } else {
          setError(err instanceof Error ? err.message : "Failed to load request");
        }
      } finally {
        setLoading(false);
      }
    };

    fetchRequest();
  }, [id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 sm:p-6 lg:p-8 max-w-3xl mx-auto space-y-6">
        <Link
          href="/dashboard/requests"
          className="inline-flex items-center gap-2 text-sm font-medium text-text-secondary hover:text-text-primary"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to My Requests
        </Link>
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-danger/10">
            <AlertCircle className="h-8 w-8 text-danger" />
          </div>
          <h3 className="mt-4 text-lg font-semibold text-text-primary">Error</h3>
          <p className="mt-1 max-w-sm text-sm text-text-secondary">{error}</p>
          <Link
            href="/dashboard/requests"
            className="mt-6 inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary-hover"
          >
            Go to My Requests
          </Link>
        </div>
      </div>
    );
  }

  if (!request) return null;

  const statusConfig = STATUS_CONFIG[request.status] || STATUS_CONFIG.draft;
  const priorityConfig = PRIORITY_CONFIG[request.priority] || PRIORITY_CONFIG.medium;
  const StatusIcon = statusConfig.icon;

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-3xl mx-auto space-y-6">
      {/* Back link */}
      <Link
        href="/dashboard/requests"
        className="inline-flex items-center gap-2 text-sm font-medium text-text-secondary hover:text-text-primary"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to My Requests
      </Link>

      {/* Header card */}
      <div className="rounded-xl border border-border bg-surface shadow-sm overflow-hidden">
        <div className="border-b border-border px-6 py-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-xl font-bold text-text-primary">{request.title}</h1>
              <p className="mt-1 text-sm text-text-muted font-mono">{request.request_no}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${statusConfig.color}`}>
                <StatusIcon className="h-3.5 w-3.5" />
                {statusConfig.label}
              </span>
              <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${priorityConfig.color}`}>
                {priorityConfig.label}
              </span>
            </div>
          </div>
        </div>

        {/* Details grid */}
        <div className="px-6 py-5 space-y-5">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {/* Request Type */}
            <div className="flex items-start gap-3 rounded-lg border border-border p-3">
              <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-muted">
                <Tag className="h-4 w-4 text-text-muted" />
              </div>
              <div>
                <p className="text-xs text-text-muted">Request Type</p>
                <p className="text-sm font-medium text-text-primary capitalize">{request.request_type}</p>
              </div>
            </div>

            {/* Category */}
            <div className="flex items-start gap-3 rounded-lg border border-border p-3">
              <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-muted">
                <FileText className="h-4 w-4 text-text-muted" />
              </div>
              <div>
                <p className="text-xs text-text-muted">Category</p>
                <p className="text-sm font-medium text-text-primary">{request.category || "—"}</p>
              </div>
            </div>

            {/* Department */}
            <div className="flex items-start gap-3 rounded-lg border border-border p-3">
              <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-muted">
                <Building2 className="h-4 w-4 text-text-muted" />
              </div>
              <div>
                <p className="text-xs text-text-muted">Department</p>
                <p className="text-sm font-medium text-text-primary">{departmentName || "—"}</p>
              </div>
            </div>

            {/* Created */}
            <div className="flex items-start gap-3 rounded-lg border border-border p-3">
              <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-muted">
                <Calendar className="h-4 w-4 text-text-muted" />
              </div>
              <div>
                <p className="text-xs text-text-muted">Created</p>
                <p className="text-sm font-medium text-text-primary">{formatDate(request.created_at)}</p>
              </div>
            </div>
          </div>

          {/* Description */}
          {request.description && (
            <div>
              <h3 className="mb-2 text-sm font-medium text-text-secondary">Description</h3>
              <div className="rounded-lg border border-border bg-muted/50 p-4">
                <p className="text-sm text-text-primary whitespace-pre-wrap">{request.description}</p>
              </div>
            </div>
          )}

          {/* Timestamps */}
          <div className="border-t border-border pt-4">
            <h3 className="mb-3 text-sm font-medium text-text-secondary">Timeline</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-text-muted">Created</span>
                <span className="text-text-primary">{formatDate(request.created_at)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-text-muted">Last Updated</span>
                <span className="text-text-primary">{formatDate(request.updated_at)}</span>
              </div>
              {request.resolved_at && (
                <div className="flex justify-between">
                  <span className="text-text-muted">Resolved</span>
                  <span className="text-text-primary">{formatDate(request.resolved_at)}</span>
                </div>
              )}
              {request.closed_at && (
                <div className="flex justify-between">
                  <span className="text-text-muted">Closed</span>
                  <span className="text-text-primary">{formatDate(request.closed_at)}</span>
                </div>
              )}
              {request.rejected_at && (
                <div className="flex justify-between">
                  <span className="text-text-muted">Rejected</span>
                  <span className="text-text-primary">{formatDate(request.rejected_at)}</span>
                </div>
              )}
            </div>
          </div>

          {/* Rejection reason */}
          {request.rejection_reason && (
            <div className="border-t border-border pt-4">
              <h3 className="mb-2 text-sm font-medium text-danger">Rejection Reason</h3>
              <div className="rounded-lg border border-danger/20 bg-danger/5 p-4">
                <p className="text-sm text-text-primary">{request.rejection_reason}</p>
              </div>
            </div>
          )}

          {/* Resolution notes */}
          {request.resolution_notes && (
            <div className="border-t border-border pt-4">
              <h3 className="mb-2 text-sm font-medium text-success">Resolution Notes</h3>
              <div className="rounded-lg border border-success/20 bg-success/5 p-4">
                <p className="text-sm text-text-primary">{request.resolution_notes}</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
