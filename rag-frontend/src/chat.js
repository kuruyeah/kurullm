import React, { useState } from "react";
import "./Chat.css";

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    if (!input) return;

    const userMessage = { role: "user", text: input };
    setMessages((prev) => [...prev, userMessage]);

    setLoading(true);

    const res = await fetch("http://127.0.0.1:8000/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ message: input })
    });

    const data = await res.json();

    const botMessage = {
      role: "bot",
      text: data.answer
    };

    setMessages((prev) => [...prev, botMessage]);
    setInput("");
    setLoading(false);
  };

  return (
    <div className="chat-container">
      <div className="chat-box">
        {messages.map((msg, i) => (
          <div key={i} className={msg.role}>
            {msg.text}
          </div>
        ))}
        {loading && <div className="bot">Typing...</div>}
      </div>

      <div className="input-box">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Tanya sesuatu..."
        />
        <button onClick={sendMessage}>Kirim</button>
      </div>
    </div>
  );
}