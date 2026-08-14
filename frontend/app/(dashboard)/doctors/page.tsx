import type { Metadata } from "next";

import { DoctorDirectory } from "@/components/doctors/DoctorDirectory";

export const metadata: Metadata = {
  title: "จัดการแพทย์ | ระบบจองคิวคลินิก",
};

export default function DoctorsPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold text-slate-900">จัดการแพทย์</h1>
      <DoctorDirectory />
    </div>
  );
}
