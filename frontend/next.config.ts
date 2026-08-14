import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // ปิด header ที่บอกว่าใช้ Next.js (ลดข้อมูลที่เปิดเผยต่อภายนอก)
  poweredByHeader: false,
};

export default nextConfig;
