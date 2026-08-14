"use client";

/**
 * รายงานเชิงบริหาร — ยอดจอง, ช่วงเวลาที่คนแน่น (heatmap), อัตราผิดนัด
 *
 * วาดกราฟด้วย CSS ล้วน เพื่อไม่ต้องพึ่งไลบรารีกราฟภายนอกและโหลดเร็วบนเครื่องหน้าร้าน
 */
import { useCallback, useEffect, useState } from "react";

import { ApiError, reportApi } from "@/lib/api";
import { ISO_WEEKDAY_LABELS, formatBaht, formatPercent, shiftIsoDate, todayIsoDate } from "@/lib/format";
import { Alert, Button, Card, EmptyState, LoadingRow, Select, StatCard, TextInput } from "@/components/ui";
import type { NoShowReport, ReportSummary } from "@/types/api";

export function ReportDashboard() {
  const [dateFrom, setDateFrom] = useState(shiftIsoDate(todayIsoDate(), -30));
  const [dateTo, setDateTo] = useState(todayIsoDate());
  const [groupBy, setGroupBy] = useState<"daily" | "monthly">("daily");

  const [summary, setSummary] = useState<ReportSummary | null>(null);
  const [noShow, setNoShow] = useState<NoShowReport | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadReports = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const [summaryData, noShowData] = await Promise.all([
        reportApi.summary({ period: groupBy, date_from: dateFrom, date_to: dateTo }),
        reportApi.noShowRate({ date_from: dateFrom, date_to: dateTo }),
      ]);
      setSummary(summaryData);
      setNoShow(noShowData);
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : "โหลดรายงานไม่สำเร็จ");
    } finally {
      setIsLoading(false);
    }
  }, [dateFrom, dateTo, groupBy]);

  useEffect(() => {
    void loadReports();
  }, [loadReports]);

  const maxSeriesValue = Math.max(1, ...(summary?.series.map((point) => point.total) ?? [1]));

  return (
    <div className="space-y-4">
      <Card title="ช่วงเวลาที่ต้องการดู">
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">ตั้งแต่วันที่</label>
            <TextInput
              type="date"
              value={dateFrom}
              onChange={(event) => setDateFrom(event.target.value)}
              className="w-44"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">ถึงวันที่</label>
            <TextInput
              type="date"
              value={dateTo}
              onChange={(event) => setDateTo(event.target.value)}
              className="w-44"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">แบ่งกลุ่มตาม</label>
            <Select
              value={groupBy}
              onChange={(event) => setGroupBy(event.target.value as "daily" | "monthly")}
              className="w-36"
            >
              <option value="daily">รายวัน</option>
              <option value="monthly">รายเดือน</option>
            </Select>
          </div>
          <Button onClick={() => void loadReports()}>ดูรายงาน</Button>
        </div>
      </Card>

      {errorMessage && <Alert>{errorMessage}</Alert>}
      {isLoading && <LoadingRow label="กำลังประมวลผลรายงาน..." />}

      {!isLoading && summary && noShow && (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <StatCard label="คิวทั้งหมด" value={summary.totals.total} />
            <StatCard label="เสร็จสิ้น" value={summary.totals.completed} />
            <StatCard
              label="อัตราผิดนัด"
              value={formatPercent(noShow.no_show_rate)}
              hint={`${noShow.no_show_count} จาก ${noShow.total_appointments} คิว`}
            />
            <StatCard
              label="เวลารอเฉลี่ย"
              value={
                summary.average_waiting_minutes === null
                  ? "-"
                  : `${summary.average_waiting_minutes} นาที`
              }
              hint="ตั้งแต่เช็คอินจนได้เริ่มรักษา"
            />
          </div>

          <Card title="ยอดจองตามช่วงเวลา">
            {summary.series.length === 0 ? (
              <EmptyState message="ไม่มีข้อมูลในช่วงที่เลือก" />
            ) : (
              <div className="flex h-48 items-end gap-1 overflow-x-auto">
                {summary.series.map((point) => (
                  <div key={point.bucket} className="flex min-w-8 flex-1 flex-col items-center gap-1">
                    <div
                      className="w-full rounded-t bg-brand-500"
                      style={{ height: `${(point.total / maxSeriesValue) * 100}%` }}
                      title={`${point.bucket}: ${point.total} คิว (เสร็จสิ้น ${point.completed})`}
                    />
                    <span className="text-[10px] text-slate-400">
                      {point.bucket?.slice(5) ?? "-"}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </Card>

          <PeakHourHeatmap peakHours={summary.peak_hours} />

          <div className="grid gap-4 lg:grid-cols-2">
            <Card title="แยกตามบริการ">
              {summary.by_service.length === 0 ? (
                <EmptyState message="ไม่มีข้อมูล" />
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs uppercase text-slate-500">
                      <th className="py-2">บริการ</th>
                      <th className="py-2 text-right">จำนวนคิว</th>
                      <th className="py-2 text-right">รายได้ (เสร็จสิ้น)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary.by_service.map((row) => (
                      <tr key={row.service_id} className="border-t border-slate-50">
                        <td className="py-2 text-slate-700">{row.service_name}</td>
                        <td className="py-2 text-right">{row.total}</td>
                        <td className="py-2 text-right">{formatBaht(row.completed_revenue)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Card>

            <Card title="อัตราผิดนัดรายแพทย์">
              {noShow.by_doctor.length === 0 ? (
                <EmptyState message="ไม่มีข้อมูล" />
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs uppercase text-slate-500">
                      <th className="py-2">แพทย์</th>
                      <th className="py-2 text-right">คิวทั้งหมด</th>
                      <th className="py-2 text-right">ไม่มา</th>
                      <th className="py-2 text-right">อัตรา</th>
                    </tr>
                  </thead>
                  <tbody>
                    {noShow.by_doctor.map((row) => (
                      <tr key={row.doctor_id ?? "none"} className="border-t border-slate-50">
                        <td className="py-2 text-slate-700">{row.doctor_name ?? "ไม่ระบุแพทย์"}</td>
                        <td className="py-2 text-right">{row.total}</td>
                        <td className="py-2 text-right">{row.no_show}</td>
                        <td className="py-2 text-right">{formatPercent(row.no_show_rate)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

function PeakHourHeatmap({ peakHours }: { peakHours: ReportSummary["peak_hours"] }) {
  if (peakHours.length === 0) {
    return (
      <Card title="ช่วงเวลาที่คนแน่น">
        <EmptyState message="ไม่มีข้อมูลในช่วงที่เลือก" />
      </Card>
    );
  }

  const hours = Array.from(
    new Set(peakHours.map((cell) => cell.hour)),
  ).sort((a, b) => a - b);
  const maxTotal = Math.max(...peakHours.map((cell) => cell.total));

  const lookup = new Map(peakHours.map((cell) => [`${cell.weekday}-${cell.hour}`, cell.total]));

  return (
    <Card title="ช่วงเวลาที่คนแน่น" description="สีเข้ม = คิวเยอะ (แกนตั้ง = วัน, แกนนอน = ชั่วโมง)">
      <div className="table-scroll">
        <table className="min-w-max border-collapse text-xs">
          <thead>
            <tr>
              <th className="px-2 py-1" />
              {hours.map((hour) => (
                <th key={hour} className="px-1 py-1 text-slate-500">
                  {String(hour).padStart(2, "0")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[1, 2, 3, 4, 5, 6, 7].map((weekday) => (
              <tr key={weekday}>
                <th className="px-2 py-1 text-left font-medium text-slate-500">
                  {ISO_WEEKDAY_LABELS[weekday]}
                </th>
                {hours.map((hour) => {
                  const total = lookup.get(`${weekday}-${hour}`) ?? 0;
                  const intensity = total / maxTotal;
                  return (
                    <td key={hour} className="p-0.5">
                      <div
                        className="h-6 w-8 rounded"
                        style={{
                          backgroundColor:
                            total === 0 ? "#f1f5f9" : `rgba(37, 99, 235, ${0.15 + intensity * 0.85})`,
                        }}
                        title={`${ISO_WEEKDAY_LABELS[weekday]} ${hour}:00 — ${total} คิว`}
                      />
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
