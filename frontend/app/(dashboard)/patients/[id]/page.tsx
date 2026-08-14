import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { PatientDetail } from "@/components/patients/PatientDetail";

export const metadata: Metadata = {
  title: "ประวัติคนไข้ | ระบบจองคิวคลินิก",
};

export default async function PatientDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const patientId = Number(id);

  if (!Number.isInteger(patientId) || patientId <= 0) {
    notFound();
  }

  return (
    <div className="space-y-4">
      <Link href="/patients" className="text-sm text-brand-600">
        ← กลับไปหน้าค้นหาคนไข้
      </Link>
      <PatientDetail patientId={patientId} />
    </div>
  );
}
