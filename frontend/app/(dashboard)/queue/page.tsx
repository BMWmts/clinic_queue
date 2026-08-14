import type { Metadata } from "next";

import { QueueBoard } from "@/components/queue/QueueBoard";

export const metadata: Metadata = {
  title: "คิววันนี้ | ระบบจองคิวคลินิก",
};

/** หน้าจอคิวหน้างาน (ตัวหน้าจอเป็น Client Component เพราะต้องอัปเดตแบบเรียลไทม์) */
export default function QueuePage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold text-slate-900">คิวหน้างาน</h1>
      <QueueBoard />
    </div>
  );
}
