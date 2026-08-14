"use client";

/**
 * โครงหน้าจอของระบบหลังบ้าน — แถบเมนูด้านข้าง + แถบบนที่แสดงผู้ใช้และสาขา
 *
 * เมนูถูกกรองตาม role ของผู้ใช้ (เช่น เมนูสาขา/รายงานเห็นเฉพาะผู้จัดการขึ้นไป)
 * แต่การตรวจสิทธิ์จริงยังอยู่ที่ backend เสมอ — ที่นี่แค่ไม่แสดงสิ่งที่กดไปก็ไม่ได้ใช้
 */
import Link from "next/link";
import { usePathname } from "next/navigation";

import { Button } from "@/components/ui";
import { useSession } from "@/lib/hooks/useSession";

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
  { href: "/reports", label: "รายงาน", icon: "📊", requiresBranchManager: true },
  { href: "/branches", label: "สาขา", icon: "🏥", requiresBranchManager: true },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, isLoading, logout, canManageBranch } = useSession();

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
            {isLoading ? (
              <span className="text-sm text-slate-400">กำลังโหลด...</span>
            ) : (
              user && (
                <div className="text-right">
                  <p className="text-sm font-medium text-slate-800">{user.full_name}</p>
                  <p className="text-xs text-slate-500">
                    {user.role_display}
                    {user.clinic_name ? ` · ${user.clinic_name}` : " · ทุกสาขา"}
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
