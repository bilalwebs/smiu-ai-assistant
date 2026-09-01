"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import type { DepartmentRead } from "@/types/api";
import {
  ArrowLeft,
  Loader2,
  Upload,
  X,
  FileText,
  Send,
  RotateCcw,
} from "lucide-react";

const REQUEST_TYPES = [
  { value: "general", label: "General" },
  { value: "admission", label: "Admission" },
  { value: "examination", label: "Examination" },
  { value: "other", label: "Other" },
];

const CATEGORIES = [
  "Academic",
  "Administrative",
  "Financial",
  "Technical",
  "Student Affairs",
  "Other",
];

const PRIORITY_OPTIONS = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "critical", label: "Critical" },
];

const MAX_DESCRIPTION = 2000;

export default function NewRequestPage() {
  const router = useRouter();
  const [departments, setDepartments] = useState<DepartmentRead[]>([]);
  const [departmentsLoading, setDepartmentsLoading] = useState(true);

  const [requestType, setRequestType] = useState("general");
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState("medium");
  const [files, setFiles] = useState<File[]>([]);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    const fetchDepartments = async () => {
      try {
        const data = await api.departments.list();
        setDepartments(data);
      } catch {
        // departments optional
      } finally {
        setDepartmentsLoading(false);
      }
    };
    fetchDepartments();
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files || []);
    setFiles((prev) => [...prev, ...selected].slice(0, 5));
    e.target.value = "";
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleReset = () => {
    setRequestType("general");
    setTitle("");
    setCategory("");
    setDepartmentId("");
    setDescription("");
    setPriority("medium");
    setFiles([]);
    setError("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!title.trim()) {
      setError("Title is required.");
      return;
    }

    setIsSubmitting(true);
    try {
      const request = await api.requests.create({
        request_type: requestType as "general" | "admission" | "examination" | "other",
        title: title.trim(),
        category: category || undefined,
        department_id: departmentId || undefined,
        description: description.trim() || undefined,
        priority: priority as "low" | "medium" | "high" | "critical",
      });

      // Upload files if any
      if (files.length > 0) {
        for (const file of files) {
          try {
            await api.documents.uploadStandalone(file);
          } catch {
            // file upload is optional
          }
        }
      }

      setSuccess(true);
      setTimeout(() => {
        router.push("/dashboard/requests");
      }, 1500);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError(err instanceof Error ? err.message : "Failed to create request");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  if (success) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
          <Send className="h-8 w-8 text-green-600" />
        </div>
        <h2 className="mt-4 text-xl font-bold text-text-primary">Request Submitted!</h2>
        <p className="mt-2 text-sm text-text-secondary">
          Your request has been created successfully.
        </p>
        <p className="mt-1 text-xs text-text-muted">Redirecting to My Requests...</p>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => router.back()}
          className="flex h-9 w-9 items-center justify-center rounded-lg border border-border text-text-secondary hover:bg-muted"
        >
          <ArrowLeft className="h-4 w-4" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-text-primary">New Request</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Submit a new request to the university administration
          </p>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-danger/20 bg-danger/5 px-4 py-3 text-sm text-danger">
          {error}
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-5 rounded-xl border border-border bg-surface p-6 shadow-sm">
        {/* Request Type */}
        <div>
          <label className="mb-1.5 block text-sm font-medium text-text-primary">
            Request Type
          </label>
          <div className="flex flex-wrap gap-2">
            {REQUEST_TYPES.map((type) => (
              <button
                key={type.value}
                type="button"
                onClick={() => setRequestType(type.value)}
                className={`rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${
                  requestType === type.value
                    ? "border-primary bg-primary-soft text-primary"
                    : "border-border bg-surface text-text-secondary hover:bg-muted"
                }`}
              >
                {type.label}
              </button>
            ))}
          </div>
        </div>

        {/* Title */}
        <div>
          <label htmlFor="title" className="mb-1.5 block text-sm font-medium text-text-primary">
            Subject <span className="text-danger">*</span>
          </label>
          <input
            id="title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            maxLength={200}
            className="h-11 w-full rounded-lg border border-border bg-surface px-4 text-sm text-text-primary placeholder-text-muted transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            placeholder="Enter request subject"
          />
          <p className="mt-1 text-xs text-text-muted">{title.length}/200</p>
        </div>

        {/* Category & Priority */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="category" className="mb-1.5 block text-sm font-medium text-text-primary">
              Category
            </label>
            <select
              id="category"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="h-11 w-full appearance-none rounded-lg border border-border bg-surface px-4 text-sm text-text-primary transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            >
              <option value="">Select category</option>
              {CATEGORIES.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="priority" className="mb-1.5 block text-sm font-medium text-text-primary">
              Priority
            </label>
            <select
              id="priority"
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className="h-11 w-full appearance-none rounded-lg border border-border bg-surface px-4 text-sm text-text-primary transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20"
            >
              {PRIORITY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Department */}
        <div>
          <label htmlFor="department" className="mb-1.5 block text-sm font-medium text-text-primary">
            Department
          </label>
          <select
            id="department"
            value={departmentId}
            onChange={(e) => setDepartmentId(e.target.value)}
            disabled={departmentsLoading}
            className="h-11 w-full appearance-none rounded-lg border border-border bg-surface px-4 text-sm text-text-primary transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-50"
          >
            <option value="">
              {departmentsLoading ? "Loading..." : "Select department (optional)"}
            </option>
            {departments.map((dept) => (
              <option key={dept.id} value={dept.id}>
                {dept.name}
              </option>
            ))}
          </select>
        </div>

        {/* Description */}
        <div>
          <label htmlFor="description" className="mb-1.5 block text-sm font-medium text-text-primary">
            Description
          </label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value.slice(0, MAX_DESCRIPTION))}
            rows={5}
            className="w-full rounded-lg border border-border bg-surface px-4 py-3 text-sm text-text-primary placeholder-text-muted transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 resize-none"
            placeholder="Describe your request in detail..."
          />
          <p className="mt-1 text-xs text-text-muted">
            {description.length}/{MAX_DESCRIPTION}
          </p>
        </div>

        {/* File Upload */}
        <div>
          <label className="mb-1.5 block text-sm font-medium text-text-primary">
            Attachments
          </label>
          <div className="rounded-lg border-2 border-dashed border-border p-6 text-center hover:border-primary/50 transition-colors">
            <Upload className="mx-auto h-8 w-8 text-text-muted" />
            <p className="mt-2 text-sm text-text-secondary">
              Drag & drop files here, or{" "}
              <label className="cursor-pointer font-medium text-primary hover:text-primary-hover">
                browse
                <input
                  type="file"
                  multiple
                  accept=".pdf,.doc,.docx,.txt,.png,.jpg"
                  onChange={handleFileChange}
                  className="hidden"
                />
              </label>
            </p>
            <p className="mt-1 text-xs text-text-muted">PDF, DOC, TXT, PNG, JPG (max 5 files)</p>
          </div>
          {files.length > 0 && (
            <div className="mt-3 space-y-2">
              {files.map((file, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 rounded-lg border border-border bg-muted/50 px-3 py-2"
                >
                  <FileText className="h-4 w-4 flex-shrink-0 text-text-muted" />
                  <span className="flex-1 truncate text-sm text-text-primary">{file.name}</span>
                  <span className="text-xs text-text-muted">
                    {(file.size / 1024).toFixed(1)} KB
                  </span>
                  <button
                    type="button"
                    onClick={() => removeFile(i)}
                    className="flex h-6 w-6 items-center justify-center rounded text-text-muted hover:text-danger"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={handleReset}
            className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2.5 text-sm font-medium text-text-secondary hover:bg-muted transition-colors"
          >
            <RotateCcw className="h-4 w-4" />
            Reset
          </button>
          <button
            type="submit"
            disabled={isSubmitting || !title.trim()}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-white hover:bg-primary-hover disabled:opacity-50 transition-colors"
          >
            {isSubmitting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            Submit Request
          </button>
        </div>
      </form>
    </div>
  );
}
