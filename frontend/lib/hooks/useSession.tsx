"use client";

/**
 * เซสชันของผู้ใช้ที่ล็อกอินอยู่ + สาขาที่กำลังทำงานด้วย
 *
 * ดึงข้อมูลจาก /auth/me ครั้งเดียวตอนเปิด dashboard แล้วแชร์ให้ทุก component
 * ผ่าน context — ใช้ตัดสินใจว่าจะแสดงเมนู/ปุ่มไหนตาม role
 *
 * เรื่องสาขา: ผู้ใช้ทั่วไปถูกล็อกไว้ที่สาขาของตัวเอง ส่วน Super Admin ไม่ได้สังกัดสาขาใด
 * (`user.clinic` เป็น null) จึงต้องเลือกเองว่าจะทำงานกับสาขาไหน และ backend ต้องการ
 * `clinic_id` ทุกครั้งที่อ่าน/สร้างข้อมูลของสาขานั้น — ค่าที่เลือกจึงเก็บไว้ที่นี่ที่เดียว
 * เพื่อให้ทุกหน้าใช้ค่าเดียวกันและไม่ต้องเลือกใหม่เมื่อสลับหน้า
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { authApi } from "@/lib/api";
import type { User } from "@/types/api";

/** จำสาขาที่ Super Admin เลือกไว้ข้ามการรีเฟรชหน้า */
const ACTIVE_CLINIC_STORAGE_KEY = "clinic.activeClinicId";

interface SessionContextValue {
  user: User | null;
  isLoading: boolean;
  logout: () => Promise<void>;
  /** สิทธิ์ที่ใช้บ่อยบนหน้าจอ — คำนวณจาก role ที่เดียว ไม่ต้องเช็คซ้ำในแต่ละหน้า */
  canManageBranch: boolean;
  canViewReports: boolean;
  canOperateQueue: boolean;
  isSuperAdmin: boolean;
  /** สาขาที่กำลังทำงานด้วย (null = Super Admin ที่ยังไม่ได้เลือกสาขา) */
  activeClinicId: number | null;
  setActiveClinicId: (clinicId: number | null) => void;
  /** true เมื่อหน้าจอต้องให้ผู้ใช้เลือกสาขาก่อน จึงจะเรียก API ที่ผูกกับสาขาได้ */
  needsClinicSelection: boolean;
}

const SessionContext = createContext<SessionContextValue | null>(null);

function readStoredClinicId(): number | null {
  if (typeof window === "undefined") {
    return null;
  }
  const storedValue = window.localStorage.getItem(ACTIVE_CLINIC_STORAGE_KEY);
  const clinicId = Number(storedValue);
  return storedValue && Number.isInteger(clinicId) ? clinicId : null;
}

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeClinicId, setActiveClinicIdState] = useState<number | null>(null);

  useEffect(() => {
    let isMounted = true;

    authApi
      .me()
      .then((currentUser) => {
        if (!isMounted) return;
        setUser(currentUser);
        // ผู้ใช้ทั่วไปใช้สาขาของตัวเองเสมอ ส่วน Super Admin ใช้สาขาที่เคยเลือกไว้ล่าสุด
        setActiveClinicIdState(currentUser.clinic ?? readStoredClinicId());
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

  const setActiveClinicId = useCallback((clinicId: number | null) => {
    setActiveClinicIdState(clinicId);
    if (typeof window === "undefined") {
      return;
    }
    if (clinicId === null) {
      window.localStorage.removeItem(ACTIVE_CLINIC_STORAGE_KEY);
    } else {
      window.localStorage.setItem(ACTIVE_CLINIC_STORAGE_KEY, String(clinicId));
    }
  }, []);

  const logout = useCallback(async () => {
    await authApi.logout();
    setUser(null);
    setActiveClinicId(null);
    router.replace("/login");
    router.refresh();
  }, [router, setActiveClinicId]);

  const value = useMemo<SessionContextValue>(() => {
    const role = user?.role;
    const isSuperAdmin = role === "super_admin";

    return {
      user,
      isLoading,
      logout,
      isSuperAdmin,
      canManageBranch: isSuperAdmin || role === "admin",
      canViewReports: isSuperAdmin || role === "admin",
      canOperateQueue: isSuperAdmin || role === "admin" || role === "staff",
      activeClinicId,
      setActiveClinicId,
      needsClinicSelection: isSuperAdmin && activeClinicId === null,
    };
  }, [user, isLoading, logout, activeClinicId, setActiveClinicId]);

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const context = useContext(SessionContext);
  if (context === null) {
    throw new Error("useSession ต้องถูกเรียกภายใน <SessionProvider> เท่านั้น");
  }
  return context;
}
