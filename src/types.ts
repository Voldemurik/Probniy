// Типы контракта данных v0.1 — зеркало backend/app/models.py (см. docs/contract.md).
// Меняются только вместе с контрактом.

export const CONTRACT_VERSION = "0.1";

export type Period = "weekly" | "monthly" | "quarterly" | "yearly";
export type Status = "active" | "inactive";
export type Flag =
  | "price_increase"
  | "price_decrease"
  | "trial_converted"
  | "duplicate"
  | "renewal_soon"
  | "gap"
  | "decoded"
  | "inactive";
export type Category =
  | "video"
  | "music"
  | "cloud"
  | "books"
  | "education"
  | "games"
  | "fitness"
  | "ecosystem"
  | "telecom"
  | "software"
  | "other";

export const CATEGORY_LABELS_RU: Record<Category, string> = {
  video: "Видео",
  music: "Музыка",
  cloud: "Облако",
  books: "Книги",
  education: "Образование",
  games: "Игры",
  fitness: "Фитнес",
  ecosystem: "Экосистема",
  telecom: "Связь",
  software: "Софт",
  other: "Другое",
};

export const PERIOD_LABELS_RU: Record<Period, string> = {
  weekly: "еженедельно",
  monthly: "ежемесячно",
  quarterly: "ежеквартально",
  yearly: "ежегодно",
};

export const FLAG_LABELS_RU: Record<Flag, string> = {
  price_increase: "цена выросла",
  price_decrease: "цена снизилась",
  trial_converted: "был пробный период",
  duplicate: "дубль",
  renewal_soon: "продление скоро",
  gap: "был пропуск",
  decoded: "расшифровано",
  inactive: "неактивна",
};

export interface Transaction {
  id: string; // t_000123 — номер строки в исходном файле
  date: string; // YYYY-MM-DD
  amount: number; // отрицательное — списание
  currency: string;
  description: string;
  category_bank: string | null;
  mcc: number | null;
}

export interface AmountPoint {
  date: string;
  amount: number;
}

export interface Decoded {
  guess: string | null;
  confidence: number | null;
  reason: string | null;
}

export interface Subscription {
  id: string;
  name: string;
  merchant_raw_variants: string[];
  category: Category;
  period: Period;
  amount_current: number;
  amount_history: AmountPoint[];
  charges: string[];
  first_charge: string;
  last_charge: string;
  next_charge_expected: string | null;
  status: Status;
  confidence: number; // 0–1: ≥0.8 зелёный, 0.5–0.8 жёлтый, <0.5 серый
  flags: Flag[];
  decoded: Decoded;
  monthly_cost: number;
  yearly_cost: number;
}

export interface Insight {
  type: Flag;
  subscription_ids: string[];
  text: string;
}

export interface Totals {
  count: number;
  monthly: number;
  yearly: number;
}

export interface ScanMeta {
  period_from: string;
  period_to: string;
  months: number;
  tx_count: number;
  debit_count: number;
  source_format: string;
  warnings: string[];
}

export interface ScanResult {
  contract_version: string;
  meta: ScanMeta;
  totals: Totals;
  subscriptions: Subscription[];
  insights: Insight[];
}

export interface SampleInfo {
  id: string;
  title: string;
  description: string;
  file: string;
}

export interface ErrorResponse {
  error: string;
  hint: string | null;
}

// --- Отписка (воскресенье) --------------------------------------------------------

export type CancelChannel = "app" | "site" | "support" | "store" | "unknown";

export interface CancelStep {
  order: number;
  text: string;
}

export interface CancelPlan {
  subscription_id: string;
  service_name: string;
  channel: CancelChannel;
  steps: CancelStep[];
  letter: string;
  yearly_savings: number;
}

export interface BulkCancelPlan {
  plans: CancelPlan[];
  total_yearly_savings: number;
  summary: string;
}

// --- Утилиты для интерфейса --------------------------------------------------------

/** 8279 → "8 279 ₽" (неразрывный пробел между разрядами) */
export function formatRub(amount: number): string {
  const rounded = Math.round(amount * 100) / 100;
  const s = Number.isInteger(rounded)
    ? rounded.toLocaleString("ru-RU")
    : rounded.toLocaleString("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return `${s.replace(/\s/g, " ")} ₽`;
}

export function confidenceTone(c: number): "high" | "medium" | "low" {
  return c >= 0.8 ? "high" : c >= 0.5 ? "medium" : "low";
}

/** Пересчёт итогов на клиенте после «Это не подписка» */
export function recomputeTotals(subs: Subscription[]): Totals {
  const active = subs.filter((s) => s.status === "active");
  const round = (x: number) => Math.round(x * 100) / 100;
  return {
    count: active.length,
    monthly: round(active.reduce((a, s) => a + s.monthly_cost, 0)),
    yearly: round(active.reduce((a, s) => a + s.yearly_cost, 0)),
  };
}
