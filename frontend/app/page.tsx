import { redirect } from "next/navigation";

/** หน้าแรกของระบบหลังบ้านคือหน้าจอคิววันนี้ (middleware จะพาไป /login ถ้ายังไม่ล็อกอิน) */
export default function HomePage() {
  redirect("/queue");
}
