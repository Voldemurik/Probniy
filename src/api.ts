// Слой контракта между фронтендом и бэкендом (docs/contract.md, раздел «API»).
// Здесь — и только здесь — адреса ручек, формат ошибок и переключение на мок.
// Экраны и компоненты вызывают эти функции и ничего не знают про fetch.
//
// Режимы: VITE_USE_MOCK=1 → ответы из src/mock/*.json без сети;
//         иначе запросы идут на VITE_API_URL (по умолчанию http://localhost:8000).

import type { BulkCancelPlan, CancelPlan, ErrorResponse, SampleInfo, ScanResult, Subscription } from "./types";

const API_URL: string = (import.meta as any).env?.VITE_API_URL ?? "http://localhost:8000";
const USE_MOCK: boolean = (import.meta as any).env?.VITE_USE_MOCK === "1";

/** Ошибка API в формате контракта: error показываем как есть, hint — второй строкой. */
export class ApiError extends Error {
  hint: string | null;
  status: number;
  constructor(status: number, body: ErrorResponse) {
    super(body.error);
    this.status = status;
    this.hint = body.hint ?? null;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, init);
  if (!res.ok) {
    let body: ErrorResponse = { error: `Ошибка ${res.status}`, hint: null };
    try {
      body = (await res.json()) as ErrorResponse;
    } catch {
      /* тело не JSON — оставляем общее сообщение */
    }
    throw new ApiError(res.status, body);
  }
  return (await res.json()) as T;
}

async function mock<T>(loader: () => Promise<{ default: T }>, delayMs = 600): Promise<T> {
  const mod = await loader();
  await new Promise((r) => setTimeout(r, delayMs)); // чтобы состояние «загрузка» было видно
  return mod.default;
}

/** GET /api/samples — список демо-профилей для кнопок «Загрузить пример». */
export function getSamples(): Promise<SampleInfo[]> {
  if (USE_MOCK) return mock(() => import("./mock/samples.json"), 100);
  return request<SampleInfo[]>("/api/samples");
}

/** GET /api/samples/{id}/scan — результат по демо-профилю. */
export function scanSample(id: string): Promise<ScanResult> {
  if (USE_MOCK) return mock(() => import("./mock/result.json") as Promise<{ default: ScanResult }>);
  return request<ScanResult>(`/api/samples/${encodeURIComponent(id)}/scan`);
}

/** POST /api/scan — загрузка файла выписки (CSV; PDF — с воскресенья). */
export function scanFile(file: File): Promise<ScanResult> {
  if (USE_MOCK) return mock(() => import("./mock/result.json") as Promise<{ default: ScanResult }>, 1500);
  const form = new FormData();
  form.append("file", file);
  return request<ScanResult>("/api/scan", { method: "POST", body: form });
}

/** POST /api/subscriptions/cancel-plan — путь отмены и письмо (появится в воскресенье). */
export function cancelPlan(subscription: Subscription, tone: "neutral" | "polite" | "firm" = "polite"): Promise<CancelPlan> {
  return request<CancelPlan>("/api/subscriptions/cancel-plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ subscription, tone }),
  });
}

/** POST /api/subscriptions/cancel-plan/bulk — сводка по выбранным подпискам (воскресенье). */
export function cancelPlanBulk(subscriptions: Subscription[], tone: "neutral" | "polite" | "firm" = "polite"): Promise<BulkCancelPlan> {
  return request<BulkCancelPlan>("/api/subscriptions/cancel-plan/bulk", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ subscriptions, tone }),
  });
}
