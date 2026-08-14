/**
 * HTTP client ฝั่งเบราว์เซอร์

 * ทุกคำขอวิ่งผ่าน `/api/proxy/...` ของ Next.js ซึ่งเป็นผู้แนบ token ให้เอง
 * component จึงไม่ต้องรู้เรื่อง token หรือการต่ออายุเซสชันเลย
 */
import type { ApiErrorPayload } from "@/types/api";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "ApiError";
  }

  /** true เมื่อเป็นกรณี "จองไม่ได้เพราะไม่มีเวลาว่าง/คิวชน" ซึ่งหน้าจอต้องแจ้งผู้ใช้เป็นพิเศษ */
  get isSlotConflict(): boolean {
    return this.code === "slot_unavailable" || this.code === "booking_conflict";
  }

  get isSessionExpired(): boolean {
    return this.status === 401;
  }
}

export type QueryParams = Record<string, string | number | boolean | null | undefined>;

function buildQueryString(params?: QueryParams): string {
  if (!params) return "";
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      searchParams.set(key, String(value));
    }
  }
  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : "";
}

/** แปลง response ที่ผิดพลาดให้เป็น ApiError ที่มีข้อความภาษาไทยพร้อมแสดงผล */
async function toApiError(response: Response): Promise<ApiError> {
  let payload: Partial<ApiErrorPayload> & Record<string, unknown> = {};
  try {
    payload = await response.json();
  } catch {
    // response ไม่ใช่ JSON (เช่น 502 จาก reverse proxy)
  }

  if (payload.error) {
    return new ApiError(
      response.status,
      payload.error.code,
      payload.error.message,
      payload.error.details,
    );
  }

  // ข้อผิดพลาดระดับ validation ของ DRF มาเป็น {field: [ข้อความ]}
  const fieldErrors = Object.entries(payload)
    .filter(([, value]) => Array.isArray(value) || typeof value === "string")
    .map(([field, value]) => `${field}: ${Array.isArray(value) ? value.join(", ") : value}`);

  const message = fieldErrors.length
    ? fieldErrors.join("\n")
    : `เกิดข้อผิดพลาด (${response.status})`;

  return new ApiError(response.status, "http_error", message, payload as Record<string, unknown>);
}

export class HttpClient {
  constructor(private readonly basePath: string = "/api/proxy") {}

  async request<T>(
    path: string,
    options: { method?: string; body?: unknown; params?: QueryParams } = {},
  ): Promise<T> {
    const { method = "GET", body, params } = options;

    const response = await fetch(`${this.basePath}${path}${buildQueryString(params)}`, {
      method,
      headers: body === undefined ? {} : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });

    if (!response.ok) {
      throw await toApiError(response);
    }

    if (response.status === 204) {
      return undefined as T;
    }
    return (await response.json()) as T;
  }

  get<T>(path: string, params?: QueryParams): Promise<T> {
    return this.request<T>(path, { params });
  }

  post<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>(path, { method: "POST", body });
  }

  patch<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>(path, { method: "PATCH", body });
  }

  delete<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: "DELETE" });
  }
}

/** instance กลางที่ api client ทุกโดเมนใช้ร่วมกัน */
export const httpClient = new HttpClient();
