import { useEffect, useRef, useState } from "react";

const STORAGE_KEY = "chat_messages";
const THEME_KEY = "theme";

interface ChatMessage {
  text: string;
  type: "user" | "bot";
  timestamp: string;
}

function now() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

const DARK = {
  // backgrounds
  bg: "#0b0b0b",
  bgSub: "#0e0e10",
  bgInput: "#0b0b0c",
  // surfaces
  surface: "#141416",
  surfaceHover: "#1c1c1f",
  surfaceBorder: "#242428",
  // borders
  border: "#1e1e22",
  borderSubtle: "#242426",
  // text
  textPrimary: "#f0f0f0",
  textSecondary: "#a0a0ac",
  textMuted: "#585860",
  // amber accent
  amber: "#d97706",
  amberLight: "#f59e0b",
  amberSubtle: "#1c1408",
  amberBorder: "#3d2800",
  amberText: "#fbbf24",
  // user bubble
  userBg: "#151210",
  userBorder: "#2e2318",
  // loading
  lsBg: "#000",
  lsBorder: "#2a2a2a",
  lsSurface: "#0d0d0d",
  lsIconFill: "#786040",
  lsBar: "#1e1e1e",
  lsBarFill: "#d97706",
};

const LIGHT = {
  bg: "#fafaf8",
  bgSub: "#f5f4f0",
  bgInput: "#f0efe9",
  surface: "#ffffff",
  surfaceHover: "#f5f4f0",
  surfaceBorder: "#e2e0d8",
  border: "#e8e6de",
  borderSubtle: "#dddbd2",
  textPrimary: "#1a1814",
  textSecondary: "#6b6658",
  textMuted: "#a8a498",
  amber: "#b45309",
  amberLight: "#d97706",
  amberSubtle: "#fef3c7",
  amberBorder: "#fde68a",
  amberText: "#92400e",
  userBg: "#fffbeb",
  userBorder: "#fde68a",
  lsBg: "#fafaf8",
  lsBorder: "#e2e0d8",
  lsSurface: "#ffffff",
  lsIconFill: "#d97706",
  lsBar: "#e8e6de",
  lsBarFill: "#d97706",
};

export default function App() {
  const [loading, setLoading] = useState(true);
  const [loadingHide, setLoadingHide] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileSent, setFileSent] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [dark, setDark] = useState(() => localStorage.getItem(THEME_KEY) !== "light");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const t = dark ? DARK : LIGHT;

  useEffect(() => {
    localStorage.setItem(THEME_KEY, dark ? "dark" : "light");
  }, [dark]);

  useEffect(() => {
    const t1 = setTimeout(() => setLoadingHide(true), 1400);
    const t2 = setTimeout(() => setLoading(false), 2200);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, []);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        setMessages(JSON.parse(stored));
        return;
      } catch {}
    }
    const welcome: ChatMessage = {
      text: "Привет! Я твой ИИ-помощник. Помогу проанализировать твои траты и увеличить доходы. Загрузите файл!",
      type: "bot",
      timestamp: now(),
    };
    setMessages([welcome]);
    localStorage.setItem(STORAGE_KEY, JSON.stringify([welcome]));
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function addMessage(msg: ChatMessage, list: ChatMessage[]) {
    const next = [...list, msg];
    setMessages(next);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    return next;
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    setSelectedFile(e.target.files?.[0] ?? null);
    setFileSent(false);
  }

  function clearFile() {
    setSelectedFile(null);
    setFileSent(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  function handleSend() {
    if (!selectedFile || fileSent) return;
    let list = addMessage({ text: `Файл "${selectedFile.name}" загружен.`, type: "user", timestamp: now() }, messages);
    list = addMessage({ text: "Выберите опцию из списка ниже", type: "bot", timestamp: now() }, list);
    setFileSent(true);
    setShowSuggestions(true);
  }

  function handleSuggestion(text: string) {
    addMessage({ text, type: "user", timestamp: now() }, messages);
  }

  function clearHistory() {
    if (!confirm("Удалить всю историю сообщений?")) return;
    const welcome: ChatMessage = {
      text: "Привет! Я твой ИИ-помощник. Помогу проанализировать твои траты и увеличить доходы. Загрузите файл!",
      type: "bot",
      timestamp: now(),
    };
    setMessages([welcome]);
    localStorage.removeItem(STORAGE_KEY);
    setShowSuggestions(false);
    clearFile();
  }

  const suggestions = [
    "Активные подписки",
    "Расходы за 1 месяц",
    "Расходы за 3 месяца",
    "Расходы за 6 месяцев",
    "Расходы за 12 месяцев",
    "Рекомендации",
    "Инвестиции",
  ];

  const d = dark;

  // ── Colour tokens ──────────────────────────────────────────────────────
  const T = d ? {
    pageBg:        "#0c0a07",
    headerBg:      "#0f0d09",
    headerBorder:  "#231e14",
    headerText:    "#e0d0b0",
    avatarBg:      "#1a1408",
    avatarBorder:  "#2e2416",
    msgUserBg:     "#161008",
    msgUserBorder: "#2e2416",
    msgUserText:   "#dfd0a8",
    msgBotText:    "#9a8a6a",
    msgTime:       "#4a3c28",
    sugBorder:     "#2e2416",
    sugText:       "#7a6a48",
    sugHoverBg:    "#1a1408",
    sugHoverBorder:"#b45309",
    sugHoverText:  "#e8c870",
    inputBg:       "#0f0d09",
    inputBorder:   "#1e1912",
    sendBg:        "#1a1408",
    sendBorder:    "#2e2416",
    sendText:      "#c8a850",
    sendHoverBg:   "#221a0c",
    chipBg:        "#131008",
    chipBorder:    "#2a2010",
    chipText:      "#8a7a58",
    chipClear:     "#4a3c28",
    clearBtn:      "#4a4030",
    clearHover:    "#b45309",
    themeIcon:     "#7a6a50",
    lsBg:          "#080808",
    lsMarkBg:      "#111",
    lsMarkBorder:  "#2a2520",
    lsSubtext:     "#a09070",
    lsBarBg:       "#1e1a14",
  } : {
    pageBg:        "#f7f3eb",
    headerBg:      "#f0eadd",
    headerBorder:  "#ddd4be",
    headerText:    "#2a1e0e",
    avatarBg:      "#e8dfca",
    avatarBorder:  "#ccc0a0",
    msgUserBg:     "#ede4cc",
    msgUserBorder: "#d4c8a8",
    msgUserText:   "#2a1f0f",
    msgBotText:    "#6a5030",
    msgTime:       "#b8a880",
    sugBorder:     "#c8bc98",
    sugText:       "#7a6030",
    sugHoverBg:    "#e8dfca",
    sugHoverBorder:"#b45309",
    sugHoverText:  "#7a3800",
    inputBg:       "#f0eadd",
    inputBorder:   "#ddd4be",
    sendBg:        "#e8dfca",
    sendBorder:    "#c4b48a",
    sendText:      "#7a4a10",
    sendHoverBg:   "#ddd0aa",
    chipBg:        "#e8dfca",
    chipBorder:    "#ccc2a0",
    chipText:      "#7a6840",
    chipClear:     "#b8a880",
    clearBtn:      "#a09070",
    clearHover:    "#7a3800",
    themeIcon:     "#8a7050",
    lsBg:          "#f5f0e8",
    lsMarkBg:      "#ede8dc",
    lsMarkBorder:  "#d6cebb",
    lsSubtext:     "#78614a",
    lsBarBg:       "#ddd5c0",
  };

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body, html, #root {
          height: 100%; overflow: hidden;
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        }
        @keyframes barSlide { to { left: 100%; } }

        /* LOADING */
        .ls {
          position: fixed; inset: 0; z-index: 9999;
          display: flex; flex-direction: column;
          align-items: center; justify-content: center; gap: 28px;
          transition: transform 0.9s cubic-bezier(0.76, 0, 0.24, 1);
        }
        .ls.hide { transform: translateY(-100%); }
        .ls-mark {
          width: 52px; height: 52px;
          border-radius: 13px;
          display: flex; align-items: center; justify-content: center;
        }
        .ls-text {
          font-size: 13px; font-weight: 600;
          letter-spacing: 0.12em; text-transform: uppercase;
        }
        .ls-bar {
          width: 140px; height: 1.5px;
          position: relative; overflow: hidden; border-radius: 2px;
        }
        .ls-bar-fill {
          position: absolute; top: 0; left: -100%;
          width: 100%; height: 100%; border-radius: 2px;
          animation: barSlide 1.3s cubic-bezier(0.4,0,0.2,1) forwards;
        }
        @keyframes barSlide { to { left: 0%; } }

        /* LAYOUT */
        .chat {
          width: 100%; height: 100%;
          display: flex; flex-direction: column; overflow: hidden;
          transition: background 0.25s;
        }

        /* HEADER */
        .chat-header {
          padding: 20px 32px;
          font-size: 17px; font-weight: 600;
          display: flex; align-items: center; gap: 14px;
          flex-shrink: 0;
          letter-spacing: 0.01em;
          transition: background 0.25s, border-color 0.25s, color 0.25s;
        }
        .avatar {
          width: 36px; height: 36px;
          border-radius: 9px;
          display: flex; align-items: center; justify-content: center;
          flex-shrink: 0;
          transition: background 0.25s, border-color 0.25s;
        }
        .header-actions { margin-left: auto; display: flex; align-items: center; gap: 6px; }

        /* THEME TOGGLE */
        .theme-btn {
          background: transparent; border: none;
          width: 34px; height: 34px;
          border-radius: 8px;
          display: flex; align-items: center; justify-content: center;
          cursor: pointer;
          transition: background 0.18s;
        }

        /* CLEAR BTN */
        .clear-btn {
          background: transparent; border: none;
          font-size: 13px; cursor: pointer;
          transition: color 0.2s; letter-spacing: 0.02em;
          font-family: inherit; border-radius: 7px;
          padding: 6px 12px;
          transition: background 0.18s, color 0.18s;
        }

        /* MESSAGES */
        .messages {
          flex: 1; padding: 32px 44px;
          overflow-y: auto; display: flex; flex-direction: column;
          gap: 14px; scrollbar-width: none;
          transition: background 0.25s;
        }
        .messages::-webkit-scrollbar { display: none; }

        .message {
          max-width: 64%; padding: 13px 17px;
          border-radius: 16px; font-size: 15px;
          line-height: 1.55; word-wrap: break-word;
          animation: fadeUp 0.22s ease both;
          transition: background 0.25s, border-color 0.25s, color 0.25s;
        }
        .message.user { align-self: flex-end; border-bottom-right-radius: 4px; }
        .message.bot  { align-self: flex-start; border-bottom-left-radius: 4px; }
        .msg-time {
          font-size: 11px; margin-top: 5px; text-align: right;
          transition: color 0.25s;
        }
        @keyframes fadeUp {
          from { opacity: 0; transform: translateY(5px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        .message.user { align-self: flex-end; border-bottom-right-radius: 4px; }
        .message.bot  { align-self: flex-start; background: transparent; border-bottom-left-radius: 4px; }
        .msg-time { font-size: 11px; margin-top: 5px; text-align: right; }

        /* SUGGESTIONS */
        .suggestions {
          display: flex; gap: 8px; padding: 11px 44px 10px;
          overflow-x: auto; flex-shrink: 0; scrollbar-width: none;
          transition: background 0.25s, border-color 0.25s;
        }
        .suggestions::-webkit-scrollbar { display: none; }
        .sug-btn {
          flex-shrink: 0; padding: 8px 16px;
          border-radius: 20px; font-size: 13px; font-weight: 500;
          cursor: pointer; font-family: inherit; letter-spacing: 0.01em;
          transition: background 0.18s, border-color 0.18s, color 0.18s, transform 0.1s;
        }
        .sug-btn:active { transform: scale(0.97); }

        /* INPUT */
        .input-area {
          display: flex; align-items: center;
          padding: 16px 44px 26px; gap: 10px; flex-shrink: 0;
          transition: background 0.25s, border-color 0.25s;
        }
        .upload-btn {
          padding: 11px 22px; border-radius: 10px;
          font-size: 14px; font-weight: 500;
          cursor: pointer; white-space: nowrap;
          font-family: inherit; letter-spacing: 0.01em;
          transition: background 0.18s, border-color 0.18s, color 0.18s, transform 0.1s;
        }
        .upload-btn:active { transform: scale(0.97); }

        .send-btn {
          padding: 11px 22px; border-radius: 10px;
          font-size: 14px; font-weight: 600;
          cursor: pointer; white-space: nowrap;
          font-family: inherit; letter-spacing: 0.01em;
          transition: background 0.18s, opacity 0.18s, transform 0.1s;
        }
        .send-btn:disabled { opacity: 0.35; cursor: default; }
        .send-btn:not(:disabled):active { transform: scale(0.97); }

        .file-chip {
          display: flex; align-items: center; gap: 8px;
          border-radius: 9px; padding: 8px 12px;
          min-width: 0; flex-shrink: 1; overflow: hidden;
          transition: background 0.25s, border-color 0.25s;
        }
        .file-chip-name {
          font-size: 13px; overflow: hidden;
          text-overflow: ellipsis; white-space: nowrap;
          transition: color 0.25s;
        }
        .file-clear-btn {
          background: transparent; border: none;
          font-size: 14px; cursor: pointer; line-height: 1;
          flex-shrink: 0; padding: 0; font-family: inherit;
          transition: color 0.15s;
        }

        @media (max-width: 600px) {
          .suggestions { padding-left: 12px; padding-right: 12px; }
          .input-area { padding: 10px 12px 16px; flex-wrap: wrap; }
          .messages { padding: 20px 16px; }
          .chat-header { padding: 16px 20px; }
        }
      `}</style>

      {/* ── Loading screen ── */}
      {loading && (
        <div className={`ls${loadingHide ? " hide" : ""}`} style={{ background: t.lsBg }}>
          <div className="ls-mark" style={{ background: t.lsSurface, border: `1.5px solid ${t.lsBorder}` }}>
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
              <rect x="3" y="5" width="16" height="1.6" rx="0.8" fill={t.lsIconFill}/>
              <rect x="3" y="9.2" width="10" height="1.6" rx="0.8" fill={t.lsIconFill}/>
              <rect x="3" y="13.4" width="13" height="1.6" rx="0.8" fill={t.lsIconFill}/>
            </svg>
          </div>
          <span className="ls-text" style={{ color: t.amber }}>Найдите все ваши подписки</span>
          <div className="ls-bar" style={{ background: t.lsBar }}>
            <div className="ls-bar-fill" style={{ background: t.lsBarFill }} />
          </div>
        </div>
      )}

      {/* Chat */}
      <div className="chat" style={{ background: t.bg }}>

        {/* Header */}
        <div className="chat-header" style={{
          background: t.bg,
          color: t.textPrimary,
          borderBottom: `1px solid ${t.borderSubtle}`,
        }}>
          <div className="avatar" style={{ background: t.amberSubtle, border: `1px solid ${t.amberBorder}` }}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M2 3.5C2 2.67 2.67 2 3.5 2h9C13.33 2 14 2.67 14 3.5v7c0 .83-.67 1.5-1.5 1.5H9l-3 2v-2H3.5C2.67 14 2 13.33 2 12.5v-9Z"
                stroke={t.amber} strokeWidth="1.2" fill="none"/>
            </svg>
          </div>

          <span>ИИ-ассистент</span>

          <div className="header-actions">
            {/* Theme toggle */}
            <button
              className="theme-btn"
              title={dark ? "Светлая тема" : "Тёмная тема"}
              onClick={() => setDark(d => !d)}
              style={{ color: t.textMuted }}
              onMouseEnter={e => (e.currentTarget.style.background = t.surface)}
              onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
            >
              {dark ? (
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <circle cx="8" cy="8" r="3.2" stroke={t.amberLight} strokeWidth="1.3"/>
                  <line x1="8" y1="1" x2="8" y2="2.5" stroke={t.amberLight} strokeWidth="1.3" strokeLinecap="round"/>
                  <line x1="8" y1="13.5" x2="8" y2="15" stroke={t.amberLight} strokeWidth="1.3" strokeLinecap="round"/>
                  <line x1="1" y1="8" x2="2.5" y2="8" stroke={t.amberLight} strokeWidth="1.3" strokeLinecap="round"/>
                  <line x1="13.5" y1="8" x2="15" y2="8" stroke={t.amberLight} strokeWidth="1.3" strokeLinecap="round"/>
                  <line x1="3.05" y1="3.05" x2="4.1" y2="4.1" stroke={t.amberLight} strokeWidth="1.3" strokeLinecap="round"/>
                  <line x1="11.9" y1="11.9" x2="12.95" y2="12.95" stroke={t.amberLight} strokeWidth="1.3" strokeLinecap="round"/>
                  <line x1="12.95" y1="3.05" x2="11.9" y2="4.1" stroke={t.amberLight} strokeWidth="1.3" strokeLinecap="round"/>
                  <line x1="4.1" y1="11.9" x2="3.05" y2="12.95" stroke={t.amberLight} strokeWidth="1.3" strokeLinecap="round"/>
                </svg>
              ) : (
                <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
                  <path d="M13 8.5A5.5 5.5 0 0 1 6.5 2c-.3 0-.6.02-.88.06A5.5 5.5 0 1 0 13 8.5Z"
                    stroke={t.amber} strokeWidth="1.3" fill="none"/>
                </svg>
              )}
            </button>

            <button
              className="clear-btn"
              onClick={clearHistory}
              style={{ color: t.textMuted }}
              onMouseEnter={e => {
                e.currentTarget.style.background = t.surface;
                e.currentTarget.style.color = t.textPrimary;
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = "transparent";
                e.currentTarget.style.color = t.textMuted;
              }}
            >
              ✕ очистить
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="messages" style={{ background: t.bg }}>
          {messages.map((msg, i) => (
            <div key={i} className={`message ${msg.type}`} style={
              msg.type === "user"
                ? { background: t.userBg, border: `1px solid ${t.userBorder}`, color: t.textPrimary }
                : { background: "transparent", color: t.textSecondary }
            }>
              <div>{msg.text}</div>
              <div className="msg-time" style={{ color: t.textMuted }}>{msg.timestamp}</div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Suggestions */}
        {showSuggestions && (
          <div className="suggestions" style={{
            background: t.bgSub,
            borderTop: `1px solid ${t.border}`,
          }}>
            {suggestions.map((s) => (
              <button
                key={s}
                className="sug-btn"
                onClick={() => handleSuggestion(s)}
                style={{
                  background: t.surface,
                  border: `1px solid ${t.surfaceBorder}`,
                  color: t.textSecondary,
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.background = t.amberSubtle;
                  e.currentTarget.style.borderColor = t.amberBorder;
                  e.currentTarget.style.color = t.amberText;
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.background = t.surface;
                  e.currentTarget.style.borderColor = t.surfaceBorder;
                  e.currentTarget.style.color = t.textSecondary;
                }}
              >{s}</button>
            ))}
          </div>
        )}

        {/* Input area */}
        <div className="input-area" style={{
          background: t.bgInput,
          borderTop: `1px solid ${t.border}`,
        }}>
          <input type="file" ref={fileInputRef} hidden onChange={handleFileChange} />

          <button
            className="upload-btn"
            onClick={() => fileInputRef.current?.click()}
            style={{
              background: t.surface,
              color: t.textPrimary,
              border: `1px solid ${t.surfaceBorder}`,
            }}
            onMouseEnter={e => e.currentTarget.style.background = t.surfaceHover}
            onMouseLeave={e => e.currentTarget.style.background = t.surface}
          >
            Загрузить файл
          </button>

          {selectedFile && (
            <>
              <div className="file-chip" style={{ background: t.amberSubtle, border: `1px solid ${t.amberBorder}` }}>
                <svg width="13" height="13" viewBox="0 0 13 13" fill="none" style={{ flexShrink: 0 }}>
                  <path d="M2 1.5A.5.5 0 0 1 2.5 1h5.793L11 3.707V11.5a.5.5 0 0 1-.5.5h-8a.5.5 0 0 1-.5-.5v-10Z"
                    stroke={t.amber} strokeWidth="1" fill="none"/>
                  <path d="M7.5 1v3h3" stroke={t.amber} strokeWidth="1" fill="none"/>
                </svg>
                <span className="file-chip-name" style={{ color: t.amberText }}>{selectedFile.name}</span>
                <button
                  className="file-clear-btn"
                  title="Удалить файл"
                  onClick={clearFile}
                  style={{ color: t.amber }}
                  onMouseEnter={e => e.currentTarget.style.color = t.amberLight}
                  onMouseLeave={e => e.currentTarget.style.color = t.amber}
                >✕</button>
              </div>
              <button
                className="send-btn"
                disabled={fileSent}
                onClick={handleSend}
                style={{
                  background: fileSent ? t.surface : t.amber,
                  color: fileSent ? t.textMuted : "#fff",
                  border: `1px solid ${fileSent ? t.surfaceBorder : t.amber}`,
                }}
                onMouseEnter={e => { if (!fileSent) e.currentTarget.style.background = t.amberLight; }}
                onMouseLeave={e => { if (!fileSent) e.currentTarget.style.background = t.amber; }}
              >
                Отправить
              </button>
            </>
          )}
        </div>
      </div>
    </>
  );
}
