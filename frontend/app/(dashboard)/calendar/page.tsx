import type { Metadata } from "next";

import { CalendarBoard } from "@/components/calendar/CalendarBoard";

export const metadata: Metadata = {
  title: "ตารางแพทย์ | ระบบจองคิวคลินิก",
};

export default function CalendarPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold text-slate-900">ตารางแพทย์และการจองล่วงหน้า</h1>
      <CalendarBoard />
    </div>
  );
}
