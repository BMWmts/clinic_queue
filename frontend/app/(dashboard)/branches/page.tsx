import type { Metadata } from "next";

import { BranchManager } from "@/components/branches/BranchManager";

export const metadata: Metadata = {
  title: "สาขา | ระบบจองคิวคลินิก",
};

export default function BranchesPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold text-slate-900">จัดการสาขา</h1>
      <BranchManager />
    </div>
  );
}
