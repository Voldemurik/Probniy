import { useState, useEffect, useRef } from "react";

const STORAGE_KEY = "chat_messages";

interface Message {
  text: string;
  type: "user" | "bot";
  timestamp: string;
}

const BOT_REPLIES = [
  "Привет! Как дела?",
  "Отлично, а у тебя?",
  "Расскажи подробнее.",
  "Я тебя понимаю.",
  "Здорово!",
  "Может, попьём чаю?",
  "Спасибо за сообщение!",
  "Это интересно...",
  "Хорошего дня!",
  "Понял, принято.",
];

function now() {
  return new Date().toLocaleTimeString("ru-RU", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function loadMessages(): Message[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) return JSON.parse(stored);
  } catch {}
  return [];
}

function saveMessages(messages: Message[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(messages));
}

export default function App() {
  const [dark, setDark] = useState(() => {
    const stored = localStorage.getItem("theme");
    if (stored) return stored === "dark";
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  });

  const [messages, setMessages] = useState<Message[]>(() => {
    const stored = loadMessages();
    if (stored.length > 0) return stored;
    return [{ text: "Привет! Я бот. Напиши что-нибудь.", type: "bot", timestamp: now() }];
  });

  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    localStorage.setItem("theme", dark ? "dark" : "light");
  }, [dark]);

  useEffect(() => {
    saveMessages(messages);
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  function handleSend() {
    const text = input.trim();
    if (!text) return;
    const userMsg: Message = { text, type: "user", timestamp: now() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");

    setTimeout(() => {
      const reply = BOT_REPLIES[Math.floor(Math.random() * BOT_REPLIES.length)];
      setMessages((prev) => [...prev, { text: reply, type: "bot", timestamp: now() }]);
    }, 400 + Math.random() * 600);
  }

  function handleClear() {
    if (window.confirm("Удалить всю историю сообщений?")) {
      const welcome: Message = {
        text: "Чат очищен. Начните общение!",
        type: "bot",
        timestamp: now(),
      };
      setMessages([welcome]);
    }
  }

  return (
    <div className="chat-app">
      {/* Header */}
      <header className="chat-header">
        <div className="header-icon">AI</div>
        <div>
          <div className="header-title">Финансовый ассистент</div>
          <div className="header-subtitle">Анализ подписок</div>
        </div>
        <div className="header-actions">
          <button
            className="icon-btn"
            onClick={() => setDark((d) => !d)}
            title={dark ? "Светлая тема" : "Тёмная тема"}
          >
            {dark ? "☀ Светлая" : "◑ Тёмная"}
          </button>
          <button className="icon-btn" onClick={handleClear}>
            ✕ Очистить
          </button>
        </div>
      </header>

      {/* Status bar */}
      <div className="status-bar">
        <span className="status-dot" />
        <span className="status-text">СИСТЕМА АКТИВНА · ЗАЩИЩЁННОЕ СОЕДИНЕНИЕ</span>
      </div>

      {/* Messages */}
      <div className="messages-area">
        {messages.map((msg, i) => (
          <div key={i} className={`message-row ${msg.type}`}>
            <div className="sender-label">
              {msg.type === "user" ? "Вы" : "Ассистент"}
            </div>
            <div className="message-bubble">{msg.text}</div>
            <div className="message-meta">{msg.timestamp}</div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="input-area">
        <input
          className="message-input"
          type="text"
          placeholder="Введите сообщение..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          autoFocus
        />
        <button className="send-btn" onClick={handleSend}>
          Отправить
        </button>
      </div>
    </div>
  );
}
