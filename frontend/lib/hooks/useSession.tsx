"use client";

/**
 * เซสชันของผู้ใช้ที่ล็อกอินอยู่
 *
 * ดึงข้อมูลจาก /auth/me ครั้งเดียวตอนเปิด dashboard แล้วแชร์ให้ทุก component
 * ผ่าน context — ใช้ตัดสินใจว่าจะแสดงเมนู/ปุ่มไหนตาม role
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { authApi } from "@/lib/api";
import type { User } from "@/types/api";

interface SessionContextValue {
  user: User | null;
  isLoading: boolean;
  logout: () => Promise<void>;
  /** สิทธิ์ที่ใช้บ่อยบนหน้าจอ — คำนวณจาก role ที่เดียว ไม่ต้องเช็คซ้ำในแต่ละหน้า */
  canManageBranch: boolean;
  canViewReports: boolean;
  canOperateQueue: boolean;
  isSuperAdmin: boolean;
}

const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    authApi
      .me()
      .then((currentUser) => {
        if (isMounted) setUser(currentUser);
      })
      .catch(() => {
        // เซสชันหมดอายุระหว่างใช้งาน — กลับไปหน้าเข้าสู่ระบบ
        router.replace("/login");
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [router]);

  const logout = useCallback(async () => {
    await authApi.logout();
    setUser(null);
    router.replace("/login");
    router.refresh();
  }, [router]);

  const value = useMemo<SessionContextValue>(() => {
    const role = user?.role;
    return {
      user,
      isLoading,
      logout,
      isSuperAdmin: role === "super_admin",
      canManageBranch: role === "super_admin" || role === "admin",
      canViewReports: role === "super_admin" || role === "admin",
      canOperateQueue: role === "super_admin" || role === "admin" || role === "staff",
    };
  }, [user, isLoading, logout]);

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const context = useContext(SessionContext);
  if (context === null) {
    throw new Error("useSession ต้องถูกเรียกภายใน <SessionProvider> เท่านั้น");
  }
  return context;
}
