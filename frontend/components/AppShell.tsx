"use client";

/**
 * โครงหน้าจอของระบบหลังบ้าน — แถบเมนูด้านข้าง + แถบบนที่แสดงผู้ใช้และสาขา
 *
 * เมนูถูกกรองตาม role ของผู้ใช้ (เช่น เมนูสาขา/รายงานเห็นเฉพาะผู้จัดการขึ้นไป)
 * แต่การตรวจสิทธิ์จริงยังอยู่ที่ backend เสมอ — ที่นี่แค่ไม่แสดงสิ่งที่กดไปก็ไม่ได้ใช้
 */
import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { clinicApi } from "@/lib/api";
import { Button, Select } from "@/components/ui";
import { useSession } from "@/lib/hooks/useSession";
import type { Clinic } from "@/types/api";

interface NavigationItem {
  href: string;
  label: string;
  icon: string;
  requiresBranchManager?: boolean;
}

const NAVIGATION_ITEMS: NavigationItem[] = [
  { href: "/queue", label: "คิววันนี้", icon: "🩺" },
  { href: "/calendar", label: "ตารางแพทย์", icon: "🗓️" },
  { href: "/patients", label: "คนไข้", icon: "👥" },
  { href: "/doctors", label: "จัดการแพทย์", icon: "🧑‍⚕️", requiresBranchManager: true },
  { href: "/reports", label: "รายงาน", icon: "📊", requiresBranchManager: true },
  { href: "/branches", label: "สาขา", icon: "🏥", requiresBranchManager: true },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, isLoading, logout, canManageBranch, isSuperAdmin, activeClinicId, setActiveClinicId } =
    useSession();

  const visibleItems = NAVIGATION_ITEMS.filter(
    (item) => !item.requiresBranchManager || canManageBranch,
  );

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-56 shrink-0 border-r border-slate-200 bg-white md:block">
        <div className="px-4 py-5">
          <p className="text-sm font-semibold text-brand-600">
            {process.env.NEXT_PUBLIC_APP_NAME ?? "ระบบจองคิวคลินิก"}
          </p>
          <p className="text-xs text-slate-400">ระบบหลังบ้าน</p>
        </div>
        <nav className="space-y-1 px-2 pb-4">
          {visibleItems.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition ${
                  isActive
                    ? "bg-brand-50 font-medium text-brand-700"
                    : "text-slate-600 hover:bg-slate-50"
                }`}
              >
                <span aria-hidden>{item.icon}</span>
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-4 border-b border-slate-200 bg-white px-4 py-3">
          <nav className="flex gap-1 overflow-x-auto md:hidden">
            {visibleItems.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-lg px-2.5 py-1.5 text-sm text-slate-600 hover:bg-slate-100"
              >
                {item.label}
              </Link>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-3">
            {isSuperAdmin && (
              <BranchSelector
                activeClinicId={activeClinicId}
                onChange={setActiveClinicId}
              />
            )}

            {isLoading ? (
              <span className="text-sm text-slate-400">กำลังโหลด...</span>
            ) : (
              user && (
                <div className="text-right">
                  <p className="text-sm font-medium text-slate-800">{user.full_name}</p>
                  <p className="text-xs text-slate-500">
                    {user.role_display}
                    {user.clinic_name ? ` · ${user.clinic_name}` : " · ดูแลทุกสาขา"}
                  </p>
                </div>
              )
            )}
            <Button variant="secondary" onClick={() => void logout()}>
              ออกจากระบบ
            </Button>
          </div>
        </header>

        <main className="flex-1 p-4">{children}</main>
      </div>
    </div>
  );
}

/**
 * ตัวเลือกสาขาสำหรับ Super Admin
 *
 * Super Admin ไม่ได้สังกัดสาขาใด จึงต้องบอกระบบทุกครั้งว่ากำลังทำงานกับสาขาไหน
 * ค่าที่เลือกถูกเก็บใน session context แล้วส่งเป็น `clinic_id` ไปกับทุก API ที่ผูกกับสาขา
 */
function BranchSelector({
  activeClinicId,
  onChange,
}: {
  activeClinicId: number | null;
  onChange: (clinicId: number | null) => void;
}) {
  const [clinics, setClinics] = useState<Clinic[]>([]);

  useEffect(() => {
    clinicApi
      .list()
      .then((page) => setClinics(page.results))
      .catch(() => setClinics([]));
  }, []);

  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="hidden text-slate-500 sm:inline">สาขาที่ดูแลอยู่</span>
      <Select
        value={activeClinicId ?? ""}
        onChange={(event) => onChange(event.target.value ? Number(event.target.value) : null)}
        className={`w-48 ${activeClinicId === null ? "border-amber-400 bg-amber-50" : ""}`}
        aria-label="เลือกสาขาที่ต้องการทำงานด้วย"
      >
        <option value="">— เลือกสาขา —</option>
        {clinics.map((clinic) => (
          <option key={clinic.id} value={clinic.id}>
            {clinic.name} ({clinic.code})
          </option>
        ))}
      </Select>
    </label>
  );
}
