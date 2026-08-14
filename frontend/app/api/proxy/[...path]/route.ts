/**
 * Proxy ระหว่างเบราว์เซอร์กับ Django API
 *
 * เบราว์เซอร์เรียก `/api/proxy/<path ของ backend>` แล้ว route handler นี้จะ
 * แนบ access token จาก httpOnly cookie ให้เอง และถ้า token หมดอายุ (401)
 * จะขอ token ใหม่ด้วย refresh token แล้วลองซ้ำอีกครั้งแบบผู้ใช้ไม่รู้สึก
 *
 * ผลลัพธ์: token ไม่เคยถูกส่งไปให้ JavaScript ในหน้าเว็บเลย
 */
import { NextRequest, NextResponse } from "next/server";

import { callBackend } from "@/lib/api/backend";
import {
  ACCESS_TOKEN_COOKIE,
  REFRESH_TOKEN_COOKIE,
  clearSessionCookies,
  setSessionCookies,
} from "@/lib/auth/cookies";

type RouteContext = { params: Promise<{ path: string[] }> };

const METHODS_WITH_BODY = new Set(["POST", "PUT", "PATCH"]);

/** แปลง path ที่รับมาเป็น path ของ backend (ปิดท้ายด้วย / ตามแบบของ Django) */
function buildBackendPath(segments: string[]): string {
  return `/api/${segments.join("/")}/`;
}

async function readRequestBody(request: NextRequest): Promise<unknown> {
  if (!METHODS_WITH_BODY.has(request.method)) {
    return undefined;
  }
  const rawBody = await request.text();
  if (!rawBody) {
    return undefined;
  }
  try {
    return JSON.parse(rawBody);
  } catch {
    return undefined;
  }
}

/** ขอ access token ใบใหม่ — คืน null ถ้า refresh token ใช้ไม่ได้แล้ว */
async function refreshAccessToken(
  refreshToken: string,
): Promise<{ access: string; refresh?: string } | null> {
  const response = await callBackend("/api/auth/refresh/", {
    method: "POST",
    body: { refresh: refreshToken },
  });

  if (!response.ok) {
    return null;
  }
  return response.json();
}

async function handleProxyRequest(
  request: NextRequest,
  context: RouteContext,
): Promise<NextResponse> {
  const { path } = await context.params;
  const backendPath = buildBackendPath(path);
  const searchParams = request.nextUrl.searchParams.toString();
  const body = await readRequestBody(request);

  const accessToken = request.cookies.get(ACCESS_TOKEN_COOKIE)?.value;
  const refreshToken = request.cookies.get(REFRESH_TOKEN_COOKIE)?.value;

  let backendResponse = await callBackend(backendPath, {
    method: request.method,
    accessToken,
    body,
    searchParams,
  });

  let refreshedTokens: { access: string; refresh?: string } | null = null;

  if (backendResponse.status === 401 && refreshToken) {
    refreshedTokens = await refreshAccessToken(refreshToken);

    if (refreshedTokens) {
      backendResponse = await callBackend(backendPath, {
        method: request.method,
        accessToken: refreshedTokens.access,
        body,
        searchParams,
      });
    } else {
      // refresh token หมดอายุ/ถูกยกเลิก → บังคับให้ผู้ใช้เข้าสู่ระบบใหม่
      const expiredResponse = NextResponse.json(
        { error: { code: "session_expired", message: "เซสชันหมดอายุ กรุณาเข้าสู่ระบบใหม่" } },
        { status: 401 },
      );
      clearSessionCookies(expiredResponse);
      return expiredResponse;
    }
  }

  const responseBody = await backendResponse.text();
  const proxiedResponse = new NextResponse(responseBody || null, {
    status: backendResponse.status,
    headers: { "Content-Type": backendResponse.headers.get("Content-Type") ?? "application/json" },
  });

  if (refreshedTokens) {
    setSessionCookies(proxiedResponse, refreshedTokens);
  }
  return proxiedResponse;
}

export const GET = handleProxyRequest;
export const POST = handleProxyRequest;
export const PATCH = handleProxyRequest;
export const PUT = handleProxyRequest;
export const DELETE = handleProxyRequest;
