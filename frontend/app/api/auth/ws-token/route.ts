/**
 * GET /api/auth/ws-token
 *
 * คืน access token อายุสั้นให้เบราว์เซอร์ใช้เฉพาะตอน handshake ของ WebSocket
 * (เบราว์เซอร์แนบ Authorization header ใน WebSocket ไม่ได้ จึงต้องส่งผ่าน query string)
 *
 * ข้อแลกเปลี่ยนที่ยอมรับ: token ใบนี้มีอายุสั้น (ตาม JWT_ACCESS_TOKEN_MINUTES)
 * ส่วน refresh token ยังอยู่ใน httpOnly cookie และไม่เคยหลุดออกไปให้ JavaScript
 * ถ้าไม่ต้องการเปิดช่องนี้เลย ให้ลบ NEXT_PUBLIC_WS_URL ออก แล้วระบบจะใช้ polling แทน
 */
import { NextResponse } from "next/server";
import { cookies } from "next/headers";

import { callBackend } from "@/lib/api/backend";
import { ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE, setSessionCookies } from "@/lib/auth/cookies";

export async function GET(): Promise<NextResponse> {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get(ACCESS_TOKEN_COOKIE)?.value;

  if (accessToken) {
    return NextResponse.json({ token: accessToken });
  }

  // access token หมดอายุแล้ว — ขอใบใหม่ด้วย refresh token ที่อยู่ใน cookie
  const refreshToken = cookieStore.get(REFRESH_TOKEN_COOKIE)?.value;
  if (!refreshToken) {
    return NextResponse.json(
      { error: { code: "session_expired", message: "เซสชันหมดอายุ" } },
      { status: 401 },
    );
  }

  const refreshResponse = await callBackend("/api/auth/refresh/", {
    method: "POST",
    body: { refresh: refreshToken },
  });

  if (!refreshResponse.ok) {
    return NextResponse.json(
      { error: { code: "session_expired", message: "เซสชันหมดอายุ" } },
      { status: 401 },
    );
  }

  const tokens = (await refreshResponse.json()) as { access: string; refresh?: string };
  const response = NextResponse.json({ token: tokens.access });
  setSessionCookies(response, tokens);
  return response;
}
