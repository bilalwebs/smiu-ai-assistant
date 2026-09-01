"use client";

import { useEffect, useState } from "react";
import { useAuthStore } from "@/lib/store";
import { api } from "@/lib/api";
import type { StudentRead } from "@/types/api";
import {
  User,
  Mail,
  Phone,
  CreditCard,
  Building2,
  Calendar,
  BookOpen,
  GraduationCap,
  Loader2,
  Shield,
} from "lucide-react";

function formatDate(dateStr: string | null) {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

export default function ProfilePage() {
  const { user } = useAuthStore();
  const [student, setStudent] = useState<StudentRead | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchStudent = async () => {
      try {
        const data = await api.students.getMe();
        setStudent(data);
      } catch (err) {
        if (err instanceof Error && err.message.includes("404")) {
          // Student profile not found — that's ok
        } else {
          setError(err instanceof Error ? err.message : "Failed to load profile");
        }
      } finally {
        setLoading(false);
      }
    };
    fetchStudent();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  const infoItems = [
    { icon: Mail, label: "Email", value: user?.email },
    { icon: Phone, label: "Phone", value: user?.phone || student?.phone },
    { icon: CreditCard, label: "Enrollment No.", value: student?.enrollment_no },
    { icon: Building2, label: "Department", value: student?.department_id ? "—" : null },
    { icon: BookOpen, label: "Program", value: student?.program_name },
    { icon: GraduationCap, label: "Semester", value: student?.current_semester ? `Semester ${student.current_semester}` : null },
    { icon: Calendar, label: "Admission Year", value: student?.admission_year?.toString() },
    { icon: Shield, label: "Status", value: user?.status ? user.status.charAt(0).toUpperCase() + user.status.slice(1) : null },
  ].filter((item) => item.value);

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-3xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">My Profile</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Your account and academic information
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-danger/20 bg-danger/5 px-4 py-3 text-sm text-danger">
          {error}
        </div>
      )}

      {/* Profile Card */}
      <div className="rounded-xl border border-border bg-surface shadow-sm overflow-hidden">
        {/* Banner */}
        <div className="h-32 bg-gradient-to-r from-primary to-primary-hover" />

        {/* Avatar + Name */}
        <div className="relative px-6 pb-6">
          <div className="-mt-12 flex items-end gap-4">
            <div className="flex h-24 w-24 items-center justify-center rounded-2xl border-4 border-surface bg-primary-soft text-3xl font-bold text-primary shadow-sm">
              {user?.full_name?.charAt(0)?.toUpperCase() || "U"}
            </div>
            <div className="pb-1">
              <h2 className="text-xl font-bold text-text-primary">{user?.full_name || "User"}</h2>
              <p className="text-sm text-text-secondary capitalize">{user?.role || "Student"}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Information Grid */}
      <div className="rounded-xl border border-border bg-surface p-6 shadow-sm">
        <h3 className="mb-4 text-lg font-semibold text-text-primary">Account Information</h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {infoItems.map((item) => (
            <div key={item.label} className="flex items-start gap-3 rounded-lg border border-border p-3">
              <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-muted">
                <item.icon className="h-4 w-4 text-text-muted" />
              </div>
              <div>
                <p className="text-xs text-text-muted">{item.label}</p>
                <p className="text-sm font-medium text-text-primary">{item.value}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Academic Details */}
      {student && (
        <div className="rounded-xl border border-border bg-surface p-6 shadow-sm">
          <h3 className="mb-4 text-lg font-semibold text-text-primary">Academic Details</h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[
              { label: "CGPA", value: student.cgpa?.toFixed(2) || "—" },
              { label: "Credit Hours", value: student.credit_hours_completed?.toString() || "—" },
              { label: "Batch Year", value: student.batch_year?.toString() || "—" },
              { label: "Section", value: student.section || "—" },
              { label: "Program Level", value: student.program_level || "—" },
              { label: "Gender", value: student.gender || "—" },
            ].map((item) => (
              <div key={item.label} className="rounded-lg bg-muted/50 p-3 text-center">
                <p className="text-xs text-text-muted">{item.label}</p>
                <p className="mt-1 text-lg font-semibold text-text-primary">{item.value}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Account Meta */}
      <div className="rounded-xl border border-border bg-surface p-6 shadow-sm">
        <h3 className="mb-4 text-lg font-semibold text-text-primary">Account Details</h3>
        <div className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-text-secondary">Account Created</span>
            <span className="font-medium text-text-primary">{formatDate(user?.created_at || null)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">Last Login</span>
            <span className="font-medium text-text-primary">{formatDate(user?.last_login_at || null)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-text-secondary">User ID</span>
            <span className="font-mono text-xs text-text-muted">{user?.id}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
