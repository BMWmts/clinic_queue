import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { DoctorDetail } from "@/components/doctors/DoctorDetail";

export const metadata: Metadata = {
  title: "ตารางแพทย์ | ระบบจองคิวคลินิก",
};

export default async function DoctorDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const doctorId = Number(id);

  if (!Number.isInteger(doctorId) || doctorId <= 0) {
    notFound();
  }

  return (
    <div className="space-y-4">
      <Link href="/doctors" className="text-sm text-brand-600">
        ← กลับไปหน้ารายชื่อแพทย์
      </Link>
      <DoctorDetail doctorId={doctorId} />
    </div>
  );
}
