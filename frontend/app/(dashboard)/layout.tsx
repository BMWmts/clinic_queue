import { AppShell } from "@/components/AppShell";
import { SessionProvider } from "@/lib/hooks/useSession";

/**
 * Layout ของทุกหน้าในระบบหลังบ้าน
 *
 * middleware กันคนที่ยังไม่ล็อกอินไว้ก่อนหน้านี้แล้ว ส่วน SessionProvider
 * ทำหน้าที่โหลดข้อมูลผู้ใช้ปัจจุบันมาใช้ร่วมกันทุกหน้า
 */
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider>
      <AppShell>{children}</AppShell>
    </SessionProvider>
  );
}
