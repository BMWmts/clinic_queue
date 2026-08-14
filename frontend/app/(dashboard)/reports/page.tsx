import type { Metadata } from "next";

import { ReportDashboard } from "@/components/reports/ReportDashboard";

export const metadata: Metadata = {
  title: "รายงาน | ระบบจองคิวคลินิก",
};

export default function ReportsPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold text-slate-900">รายงานเชิงบริหาร</h1>
      <ReportDashboard />
    </div>
  );
}
