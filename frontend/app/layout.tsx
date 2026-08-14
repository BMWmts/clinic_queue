import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: process.env.NEXT_PUBLIC_APP_NAME ?? "ระบบจองคิวคลินิก",
  description: "ระบบจัดการคิวและนัดหมายสำหรับเจ้าหน้าที่คลินิก (ระบบหลังบ้าน)",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="th">
      <body>{children}</body>
    </html>
  );
}
