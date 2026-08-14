/**
 * ตัวเชื่อมต่อ backend ฝั่ง server ของ Next.js
 *
 * เบราว์เซอร์ไม่เคยเรียก Django โดยตรง — ทุกคำขอผ่าน route handler ของ Next
 * เพื่อให้ token อยู่ใน httpOnly cookie ได้ตลอด
 */
export const BACKEND_URL = process.env.BACKEND_INTERNAL_URL ?? "http://127.0.0.1:8000";

/** ต่อ path ของ API เข้ากับ base URL ของ backend */
export function backendUrl(path: string): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${BACKEND_URL}${normalizedPath}`;
}

interface BackendRequestOptions {
  method?: string;
  accessToken?: string;
  body?: unknown;
  headers?: Record<string, string>;
  searchParams?: string;
}

/** เรียก backend หนึ่งครั้ง (ไม่มี logic ต่ออายุ token — ตัวเรียกเป็นผู้จัดการ) */
export async function callBackend(
  path: string,
  { method = "GET", accessToken, body, headers = {}, searchParams }: BackendRequestOptions = {},
): Promise<Response> {
  const url = searchParams ? `${backendUrl(path)}?${searchParams}` : backendUrl(path);

  const requestHeaders: Record<string, string> = {
    Accept: "application/json",
    ...headers,
  };
  if (accessToken) {
    requestHeaders.Authorization = `Bearer ${accessToken}`;
  }
  if (body !== undefined) {
    requestHeaders["Content-Type"] = "application/json";
  }

  return fetch(url, {
    method,
    headers: requestHeaders,
    body: body === undefined ? undefined : JSON.stringify(body),
    cache: "no-store",
  });
}
