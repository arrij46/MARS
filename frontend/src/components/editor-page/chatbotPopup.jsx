import React, { useState } from "react";
import { authFetch } from "../../utils/api";
import "../../style/ChatbotPopup.css";
import { IoIosSend } from "react-icons/io";
import { FiMessageCircle } from "react-icons/fi";

async function sendToGroq(messages) {
  const lastMessage = messages[messages.length - 1].text;

  const response = await authFetch("/api/chatbot/chat", {
    method: "POST",
    body: JSON.stringify({ message: lastMessage }),
  });

  if (!response.ok) throw new Error("Chatbot API error");

  const data = await response.json();
  return data.reply;
}

export default function ChatbotPopup({ input = "", setInput, open = false, setOpen }) {
  // const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([
    { from: "bot", text: "Hey there! 👋 How can we help you today?" },
  ]);
  // const [input, setInput] = useState("");

  const sendMessage = () => {
    if (!input.trim()) return;
    setMessages([...messages, { from: "user", text: input }]);
    setInput("");
    // call an actual API here and update messages with the response
    sendToGroq([...messages, { from: "user", text: input }])
      .then((reply) => setMessages((prev) => [...prev, { from: "bot", text: reply }]))
      .catch(() => setMessages((prev) => [...prev, { from: "bot", text: "Sorry, something went wrong." }]));
  };

  return (
    <>
      {/* Chat Box */}
      {open && (
        <div className="chat-widget shadow">
          {/* Header */}
          <div className="chat-header d-flex justify-content-between align-items-center">
            <div className="title">
            Chat with us
            </div>
            <button
              className="btn btn-sm cross-btn"
              onClick={() => setOpen(false)}
            >
              ✕
            </button>
          </div>

          {/* Messages */}
          <div className="chat-body">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`chat-message ${msg.from === "user" ? "user" : "bot"}`}
              >
                {msg.text}
              </div>
            ))}
          </div>

          {/* Input */}
          <div className="chat-footer">
            <input
              type="text"
              className="form-control input-box"
              placeholder="Type your message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            />
            <button className="btn ms-2 input-btn" onClick={sendMessage}>
                    <IoIosSend className="send-icon"/>
              
            </button>
          </div>
        </div>
      )}

      {/* Floating Button */}
      <button className="chat-toggle-btn" onClick={() => setOpen(!open)}>
        <FiMessageCircle className="chat-icon"/>
      </button>
    </>
  );
}
