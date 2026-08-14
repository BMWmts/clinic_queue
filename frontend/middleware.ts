/**
 * ตรวจเซสชันก่อนเข้าหน้า dashboard
 *
 * ตรวจแค่ว่ามี refresh token cookie อยู่หรือไม่ (ตัวตรวจสิทธิ์จริงคือ backend เสมอ)
 * เพื่อไม่ให้ผู้ใช้ที่ยังไม่ล็อกอินเห็นโครงหน้าจอแล้วค่อยเด้งออก
 */
import { NextRequest, NextResponse } from "next/server";

import { REFRESH_TOKEN_COOKIE } from "@/lib/auth/cookies";

const DASHBOARD_PREFIXES = [
  "/queue",
  "/calendar",
  "/patients",
  "/doctors",
  "/branches",
  "/reports",
];

export function middleware(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;
  const hasSession = Boolean(request.cookies.get(REFRESH_TOKEN_COOKIE)?.value);

  const isDashboardRoute = DASHBOARD_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  );

  if (isDashboardRoute && !hasSession) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  if (pathname === "/login" && hasSession) {
    return NextResponse.redirect(new URL("/queue", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/login",
    "/queue/:path*",
    "/calendar/:path*",
    "/patients/:path*",
    "/doctors/:path*",
    "/branches/:path*",
    "/reports/:path*",
  ],
};
