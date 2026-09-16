import { useState, useRef } from "react";

type Subscription = {
  id: string;
  name: string;
  amount: number;
  currency: string;
  frequency: string;
  lastCharged: string;
  category: string;
};

const MOCK_SUBSCRIPTIONS: Subscription[] = [
  { id: "1", name: "Netflix", amount: 799, currency: "₽", frequency: "ежемесячно", lastCharged: "01.09.2026", category: "Развлечения" },
  { id: "2", name: "Spotify", amount: 299, currency: "₽", frequency: "ежемесячно", lastCharged: "03.09.2026", category: "Музыка" },
  { id: "3", name: "ChatGPT Plus", amount: 1800, currency: "₽", frequency: "ежемесячно", lastCharged: "28.08.2026", category: "Продуктивность" },
  { id: "4", name: "Adobe Creative Cloud", amount: 3490, currency: "₽", frequency: "ежемесячно", lastCharged: "15.08.2026", category: "Дизайн" },
  { id: "5", name: "iCloud 200 GB", amount: 149, currency: "₽", frequency: "ежемесячно", lastCharged: "02.09.2026", category: "Хранилище" },
  { id: "6", name: "Яндекс Плюс", amount: 399, currency: "₽", frequency: "ежемесячно", lastCharged: "04.09.2026", category: "Сервисы" },
];

type Phase = "landing" | "loading" | "results";

export default function App() {
  const [phase, setPhase] = useState<Phase>("landing");
  const [fileName, setFileName] = useState<string>("");
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileName(file.name);
    setPhase("loading");
    setTimeout(() => setPhase("results"), 2200);
  };

  const handleReset = () => {
    setPhase("landing");
    setFileName("");
    if (fileRef.current) fileRef.current.value = "";
  };

  const total = MOCK_SUBSCRIPTIONS.reduce((sum, s) => sum + s.amount, 0);

  return (
    <div className="min-h-full flex flex-col" style={{ backgroundColor: "#0c0c0d", color: "#f0eeeb" }}>
      {/* Header */}
      <header className="flex items-center justify-between px-8 py-6 border-b" style={{ borderColor: "#1e1e20" }}>
        <div className="flex items-center gap-3">
          <span style={{ fontFamily: "'DM Serif Display', serif", fontSize: "1.1rem", letterSpacing: "-0.01em" }}>
            подписки
          </span>
          <span style={{ width: 1, height: 16, backgroundColor: "#262626", display: "inline-block" }} />
          <span style={{ fontSize: "0.7rem", color: "#7a7875", letterSpacing: "0.12em", textTransform: "uppercase" }}>
            трекер
          </span>
        </div>
        {phase === "results" && (
          <button
            onClick={handleReset}
            style={{ fontSize: "0.75rem", color: "#7a7875", letterSpacing: "0.06em", cursor: "pointer" }}
            className="hover:text-[#f0eeeb] transition-colors duration-200"
          >
            сбросить
          </button>
        )}
      </header>

      {/* Main */}
      <main className="flex-1 flex flex-col">
        {phase === "landing" && (
          <div className="flex-1 flex flex-col items-center justify-center gap-10 px-6">
            <div className="text-center" style={{ maxWidth: 480 }}>
              <h1
                style={{
                  fontFamily: "'DM Serif Display', serif",
                  fontSize: "clamp(2rem, 5vw, 3.2rem)",
                  lineHeight: 1.1,
                  letterSpacing: "-0.02em",
                  marginBottom: "1rem",
                }}
              >
                Найдите все<br />ваши подписки
              </h1>
              <p style={{ fontSize: "0.875rem", color: "#7a7875", lineHeight: 1.7, fontWeight: 300 }}>
                Загрузите выписку из банка — мы найдём все регулярные списания и покажем, сколько вы тратите каждый месяц.
              </p>
            </div>

            <div
              className="relative group"
              onClick={() => fileRef.current?.click()}
              style={{ cursor: "pointer" }}
            >
              <div
                style={{
                  border: "1px solid #262626",
                  borderRadius: 2,
                  padding: "14px 48px",
                  fontSize: "0.875rem",
                  fontWeight: 500,
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  transition: "all 0.2s ease",
                  backgroundColor: "transparent",
                  color: "#f0eeeb",
                }}
                className="group-hover:border-[#7a7875] group-hover:bg-[#141415]"
              >
                Загрузить
              </div>
              <input
                ref={fileRef}
                type="file"
                accept=".csv,.xlsx,.xls,.pdf,.txt"
                onChange={handleFileChange}
                style={{ display: "none" }}
              />
            </div>

            <p style={{ fontSize: "0.7rem", color: "#3a3a3a", letterSpacing: "0.06em" }}>
              CSV · XLSX · PDF · TXT
            </p>
          </div>
        )}

        {phase === "loading" && (
          <div className="flex-1 flex flex-col items-center justify-center gap-6 px-6">
            <div style={{ position: "relative", width: 40, height: 40 }}>
              <svg viewBox="0 0 40 40" fill="none" style={{ width: 40, height: 40, animation: "spin 1.2s linear infinite" }}>
                <circle cx="20" cy="20" r="16" stroke="#1e1e20" strokeWidth="2" />
                <path d="M20 4 A16 16 0 0 1 36 20" stroke="#d4af6e" strokeWidth="2" strokeLinecap="round" />
              </svg>
              <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
            </div>
            <div className="text-center">
              <p style={{ fontSize: "0.875rem", fontWeight: 500 }}>Анализируем транзакции</p>
              <p style={{ fontSize: "0.75rem", color: "#7a7875", marginTop: 4 }}>{fileName}</p>
            </div>
          </div>
        )}

        {phase === "results" && (
          <div style={{ maxWidth: 720, margin: "0 auto", width: "100%", padding: "48px 24px" }}>
            {/* Summary row */}
            <div
              className="flex items-end justify-between mb-10 pb-6"
              style={{ borderBottom: "1px solid #1e1e20" }}
            >
              <div>
                <p style={{ fontSize: "0.7rem", color: "#7a7875", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 6 }}>
                  Найдено подписок
                </p>
                <p style={{ fontFamily: "'DM Serif Display', serif", fontSize: "2.5rem", lineHeight: 1, letterSpacing: "-0.02em" }}>
                  {MOCK_SUBSCRIPTIONS.length}
                </p>
              </div>
              <div className="text-right">
                <p style={{ fontSize: "0.7rem", color: "#7a7875", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 6 }}>
                  Итого в месяц
                </p>
                <p style={{ fontFamily: "'DM Serif Display', serif", fontSize: "2.5rem", lineHeight: 1, letterSpacing: "-0.02em", color: "#d4af6e" }}>
                  {total.toLocaleString("ru-RU")} ₽
                </p>
              </div>
            </div>

            {/* List */}
            <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
              {MOCK_SUBSCRIPTIONS.map((sub, i) => (
                <li
                  key={sub.id}
                  className="group flex items-center justify-between py-4 transition-colors duration-150 hover:bg-[#141415]"
                  style={{
                    borderBottom: i < MOCK_SUBSCRIPTIONS.length - 1 ? "1px solid #1a1a1a" : "none",
                    padding: "16px 12px",
                    margin: "0 -12px",
                    borderRadius: 2,
                  }}
                >
                  <div className="flex items-center gap-5">
                    <span style={{ fontSize: "0.65rem", color: "#3a3a3a", fontVariantNumeric: "tabular-nums", width: 18, textAlign: "right" }}>
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <div>
                      <p style={{ fontSize: "0.9rem", fontWeight: 500 }}>{sub.name}</p>
                      <p style={{ fontSize: "0.72rem", color: "#7a7875", marginTop: 2 }}>
                        {sub.category} · {sub.frequency} · последнее списание {sub.lastCharged}
                      </p>
                    </div>
                  </div>
                  <span style={{ fontSize: "0.9rem", fontWeight: 500, fontVariantNumeric: "tabular-nums", whiteSpace: "nowrap" }}>
                    {sub.amount.toLocaleString("ru-RU")} {sub.currency}
                  </span>
                </li>
              ))}
            </ul>

            {/* Footer note */}
            <p style={{ fontSize: "0.7rem", color: "#3a3a3a", textAlign: "center", marginTop: 48, letterSpacing: "0.05em" }}>
              Данные обрабатываются локально и не передаются третьим лицам
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
