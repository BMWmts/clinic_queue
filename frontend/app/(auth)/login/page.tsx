import type { Metadata } from "next";
import { Suspense } from "react";

import { LoginForm } from "./LoginForm";

export const metadata: Metadata = {
  title: "เข้าสู่ระบบ | ระบบจองคิวคลินิก",
};

/** หน้าเข้าสู่ระบบ — เป็น Server Component ที่ห่อฟอร์ม (ส่วนที่ต้องมี state) ไว้ข้างใน */
export default function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-semibold text-slate-900">
            {process.env.NEXT_PUBLIC_APP_NAME ?? "ระบบจองคิวคลินิก"}
          </h1>
          <p className="mt-1 text-sm text-slate-500">สำหรับเจ้าหน้าที่และแพทย์เท่านั้น</p>
        </div>
        <Suspense fallback={null}>
          <LoginForm />
        </Suspense>
      </div>
    </main>
  );
}
