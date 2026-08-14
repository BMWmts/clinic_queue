/**
 * POST /api/auth/login
 *
 * รับอีเมล/รหัสผ่านจากหน้า login → ส่งต่อให้ Django → เก็บ token ลง httpOnly cookie
 * แล้วคืนเฉพาะข้อมูลผู้ใช้ให้ frontend (ไม่ส่ง token กลับไปให้ JavaScript)
 */
import { NextRequest, NextResponse } from "next/server";

import { callBackend } from "@/lib/api/backend";
import { setSessionCookies } from "@/lib/auth/cookies";

export async function POST(request: NextRequest): Promise<NextResponse> {
  const credentials = await request.json();

  const backendResponse = await callBackend("/api/auth/login/", {
    method: "POST",
    body: { email: credentials.email, password: credentials.password },
  });

  const payload = await backendResponse.json().catch(() => ({}));

  if (!backendResponse.ok) {
    return NextResponse.json(payload, { status: backendResponse.status });
  }

  const response = NextResponse.json({ user: payload.user });
  setSessionCookies(response, { access: payload.access, refresh: payload.refresh });
  return response;
}
