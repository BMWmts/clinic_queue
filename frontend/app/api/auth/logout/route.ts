/**
 * POST /api/auth/logout
 *
 * แจ้ง backend ให้ยกเลิก refresh token (blacklist) แล้วล้าง cookie ของเบราว์เซอร์
 */
import { NextResponse } from "next/server";
import { cookies } from "next/headers";

import { callBackend } from "@/lib/api/backend";
import {
  ACCESS_TOKEN_COOKIE,
  REFRESH_TOKEN_COOKIE,
  clearSessionCookies,
} from "@/lib/auth/cookies";

export async function POST(): Promise<NextResponse> {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get(ACCESS_TOKEN_COOKIE)?.value;
  const refreshToken = cookieStore.get(REFRESH_TOKEN_COOKIE)?.value;

  if (accessToken && refreshToken) {
    // ถ้า backend ล้มเหลวก็ยังต้องล้าง cookie ฝั่งเราให้ผู้ใช้ออกจากระบบได้
    await callBackend("/api/auth/logout/", {
      method: "POST",
      accessToken,
      body: { refresh: refreshToken },
    }).catch(() => undefined);
  }

  const response = new NextResponse(null, { status: 204 });
  clearSessionCookies(response);
  return response;
}
