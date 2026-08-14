import type { Metadata } from "next";

import { PatientDirectory } from "@/components/patients/PatientDirectory";

export const metadata: Metadata = {
  title: "คนไข้ | ระบบจองคิวคลินิก",
};

export default function PatientsPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold text-slate-900">ฐานข้อมูลคนไข้</h1>
      <PatientDirectory />
    </div>
  );
}
