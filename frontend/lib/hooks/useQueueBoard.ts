"use client";

/**
 * ข้อมูลคิวของหน้าจอหน้างาน พร้อมการอัปเดตแบบเรียลไทม์

 * ใช้ WebSocket ถ้าตั้งค่า NEXT_PUBLIC_WS_URL ไว้ และถอยไปใช้ polling ทุก 10 วินาที
 * โดยอัตโนมัติเมื่อเชื่อมต่อไม่ได้ (ตามข้อกำหนดข้อ 5.2)
 *
 * หมายเหตุ: WebSocket ต่อจากเบราว์เซอร์ไปที่ backend โดยตรง จึงต้องใช้ token
 * ระยะสั้นที่ขอผ่าน route handler ของ Next (ไม่ได้เก็บ token ไว้ใน JS ถาวร)
 */
import { useCallback, useEffect, useRef, useState } from "react";

import { queueApi } from "@/lib/api";
import type { Appointment, QueueSummary, QueueTodayResponse } from "@/types/api";

const POLLING_INTERVAL_MS = 10_000;

interface UseQueueBoardOptions {
  date: string;
  doctorId?: number;
  clinicId?: number;
}

interface UseQueueBoardResult {
  appointments: Appointment[];
  summary: QueueSummary | null;
  clinicId: number | null;
  isLoading: boolean;
  errorMessage: string | null;
  isLive: boolean;
  refresh: () => Promise<void>;
  applyUpdatedAppointment: (appointment: Appointment) => void;
}

export function useQueueBoard({ date, doctorId, clinicId }: UseQueueBoardOptions): UseQueueBoardResult {
  const [queueData, setQueueData] = useState<QueueTodayResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLive, setIsLive] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await queueApi.today({ date, doctor_id: doctorId, clinic_id: clinicId });
      setQueueData(data);
      setErrorMessage(null);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "โหลดข้อมูลคิวไม่สำเร็จ");
    } finally {
      setIsLoading(false);
    }
  }, [date, doctorId, clinicId]);

  // โหลดครั้งแรก + polling สำรอง (ทำงานเสมอ ต่อให้ WebSocket ใช้ได้ เพื่อกันข้อมูลค้าง)
  useEffect(() => {
    setIsLoading(true);
    void refresh();

    const intervalId = window.setInterval(() => {
      void refresh();
    }, POLLING_INTERVAL_MS);

    return () => window.clearInterval(intervalId);
  }, [refresh]);

  // เชื่อม WebSocket ของสาขาที่กำลังดูอยู่
  useEffect(() => {
    const websocketBaseUrl = process.env.NEXT_PUBLIC_WS_URL;
    const currentClinicId = queueData?.clinic_id;
    if (!websocketBaseUrl || !currentClinicId) {
      return;
    }

    let isCancelled = false;

    const connect = async () => {
      const tokenResponse = await fetch("/api/auth/ws-token");
      if (!tokenResponse.ok || isCancelled) {
        return;
      }
      const { token } = (await tokenResponse.json()) as { token: string };

      const socket = new WebSocket(
        `${websocketBaseUrl}/ws/queue/${currentClinicId}/?token=${encodeURIComponent(token)}`,
      );
      socketRef.current = socket;

      socket.onopen = () => setIsLive(true);
      socket.onclose = () => setIsLive(false);
      socket.onerror = () => setIsLive(false);
      socket.onmessage = (event) => {
        const message = JSON.parse(event.data) as { event: string; payload: Appointment };
        if (message.event === "connected" || message.event === "pong") {
          return;
        }
        applyUpdatedAppointment(message.payload);
      };
    };

    void connect().catch(() => setIsLive(false));

    return () => {
      isCancelled = true;
      socketRef.current?.close();
      socketRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [queueData?.clinic_id]);

  /** แทนที่คิวเดิมด้วยข้อมูลล่าสุด (ใช้ทั้งจาก WebSocket และหลังกดปุ่มบนหน้าจอ) */
  const applyUpdatedAppointment = useCallback((updated: Appointment) => {
    setQueueData((current) => {
      if (!current) return current;

      const existingIndex = current.appointments.findIndex((item) => item.id === updated.id);
      const appointments =
        existingIndex >= 0
          ? current.appointments.map((item) => (item.id === updated.id ? updated : item))
          : [...current.appointments, updated].sort((a, b) =>
              a.scheduled_start.localeCompare(b.scheduled_start),
            );

      return { ...current, appointments };
    });
  }, []);

  return {
    appointments: queueData?.appointments ?? [],
    summary: queueData?.summary ?? null,
    clinicId: queueData?.clinic_id ?? null,
    isLoading,
    errorMessage,
    isLive,
    refresh,
    applyUpdatedAppointment,
  };
}
