/**
 * การจัดการ cookie ของเซสชัน (ใช้ได้เฉพาะฝั่ง server ของ Next.js)
 *
 * เก็บ token ไว้ใน httpOnly cookie เท่านั้น — JavaScript ในเบราว์เซอร์อ่านไม่ได้
 * จึงลดความเสี่ยงจาก XSS ที่จะขโมย token ไปใช้
 */
import type { NextResponse } from "next/server";

export const ACCESS_TOKEN_COOKIE = "clinic_access";
export const REFRESH_TOKEN_COOKIE = "clinic_refresh";

/** อายุ cookie ให้ยาวเท่ากับอายุ token ฝั่ง backend (นาที/วัน) */
const ACCESS_TOKEN_MAX_AGE_SECONDS = 60 * 15;
const REFRESH_TOKEN_MAX_AGE_SECONDS = 60 * 60 * 24 * 7;

const isProduction = process.env.NODE_ENV === "production";

interface SessionTokens {
  access: string;
  refresh?: string;
}

/** ตั้ง cookie ของเซสชันลงใน response */
export function setSessionCookies(response: NextResponse, tokens: SessionTokens): void {
  response.cookies.set({
    name: ACCESS_TOKEN_COOKIE,
    value: tokens.access,
    httpOnly: true,
    secure: isProduction,
    sameSite: "lax",
    path: "/",
    maxAge: ACCESS_TOKEN_MAX_AGE_SECONDS,
  });

  if (tokens.refresh) {
    response.cookies.set({
      name: REFRESH_TOKEN_COOKIE,
      value: tokens.refresh,
      httpOnly: true,
      secure: isProduction,
      sameSite: "lax",
      path: "/",
      maxAge: REFRESH_TOKEN_MAX_AGE_SECONDS,
    });
  }
}

/** ล้าง cookie ของเซสชัน (ใช้ตอน logout หรือเมื่อ refresh token หมดอายุ) */
export function clearSessionCookies(response: NextResponse): void {
  for (const cookieName of [ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE]) {
    response.cookies.set({
      name: cookieName,
      value: "",
      httpOnly: true,
      secure: isProduction,
      sameSite: "lax",
      path: "/",
      maxAge: 0,
    });
  }
}
