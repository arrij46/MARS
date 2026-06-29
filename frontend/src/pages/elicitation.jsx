import "../style/elicitation.css";
import { SiPlanetscale } from "react-icons/si";
import { IoIosSend } from "react-icons/io";
import { useState, useEffect, useRef } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import { FaRegUser } from "react-icons/fa";
import { GoDependabot } from "react-icons/go"; // Removed GoPaperclip
import { CiCircleList } from "react-icons/ci";
import { useAutoScroll } from "../components/elicitation-page/autoscroll-hook";
import ModelAnimation from "../components/modelAnnimation";
import ReactMarkdown from "react-markdown";
// Removed Popup import

const API_BASE_URL = "http://localhost:8000/api";

export default function Elicitation() {
  const navigate = useNavigate();
  const { projectId } = useParams();
  const location = useLocation();
  const convId = projectId;

  // New state for left sidebar toggle
  const [isSidebarOpen, setIsSidebarOpen] = useState(true); 
  
  const [sessionStarting, setSessionStarting] = useState(false);
  const [sessionReady, setSessionReady] = useState(false);
  const [baselineCollected, setBaselineCollected] = useState(false);
  const [isOpen, setIsOpen] = useState(false); // Controls right sidebar
  
  const [messages, setMessages] = useState([
    {
      text: "Hello! I'm your Requirements Assistant. Please provide a description of your software system to get started.",
      sender: "bot",
    },
  ]);
  const [requirements, setRequirements] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [editingIndex, setEditingIndex] = useState(null);
  const [editingText, setEditingText] = useState("");

  const requirementRef = useAutoScroll(requirements);
  const messagesRef = useAutoScroll(messages);
  const socketRef = useRef(null);

  const getAuthToken = () => localStorage.getItem("token");
  const projectDraft = location.state?.projectDraft;

  useEffect(() => {
    const autoSubmitDraftAsBaseline = async () => {
      if (
        !sessionReady ||
        !convId ||
        !location.state?.projectDraft ||
        baselineCollected
      )
        return;

      const { title, description } = location.state.projectDraft;
      const baselineText = `Project Title: ${title}\n\nDescription: ${description}`;

      setMessages((prev) => [
        ...prev,
        {
          text: `Here is the initial context for my project:\n\n${baselineText}`,
          sender: "user",
        },
      ]);

      try {
        const response = await fetch(
          `${API_BASE_URL}/elicitation/baseline?conv_id=${convId}`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${getAuthToken()}`,
            },
            body: JSON.stringify({ baseline_text: baselineText }),
          },
        );

        if (!response.ok) throw new Error("Failed to auto-collect baseline");

        const data = await response.json();

        setMessages((prev) => [...prev, { text: data.response, sender: "bot" }]);
        if (Array.isArray(data.requirements) && data.requirements.length) {
          setRequirements(data.requirements);
        }
        setBaselineCollected(true);
        window.history.replaceState({}, document.title);
      } catch (err) {
        console.error("❌ Auto-Baseline error:", err);
        setMessages((prev) => [
          ...prev,
          {
            text: `Error setting initial context: ${err.message}`,
            sender: "bot",
          },
        ]);
      }
    };

    autoSubmitDraftAsBaseline();
  }, [sessionReady, convId, location.state, baselineCollected]);

  useEffect(() => {
    if (!projectDraft) {
      alert("Project data missing. Please start from dashboard.");
      navigate("/dashboard");
    }
  }, [projectDraft, navigate]);

  useEffect(() => {
    if (!convId || !projectDraft?.title || !projectDraft?.description) return;

    let cancelled = false;

    const initializeSession = async () => {
      try {
        setSessionStarting(true);
        const formData = new FormData();
        formData.append("conv_id", convId);
        formData.append("title", projectDraft.title);
        formData.append("description", projectDraft.description);

        const response = await fetch(`${API_BASE_URL}/elicitation/start`, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${getAuthToken()}`,
          },
          body: formData,
        });

        if (!response.ok) throw new Error("Failed to start elicitation session");

        const data = await response.json();
        console.log("✅ Elicitation session started:", data);

        if (cancelled) return;
        setSessionReady(true);

        const wsUrl = `ws://localhost:8000/api/ws/${convId}`;
        if (socketRef.current) socketRef.current.close();
        socketRef.current = new WebSocket(wsUrl);

        socketRef.current.onopen = () =>
          console.log("✅ WebSocket connected for elicitation");

        socketRef.current.onmessage = (event) => {
          const msg = JSON.parse(event.data);
          if (msg.type === "elicitation_update" && msg.data) {
            const result = msg.data;
            if (result.response) {
              setMessages((prev) => [
                ...prev,
                { text: result.response, sender: "bot" },
              ]);
            }
            if (result.requirements) {
              setRequirements(result.requirements);
            }
          }
        };

        socketRef.current.onerror = (error) =>
          console.error(" WebSocket error:", error);
        socketRef.current.onclose = () => console.log("WebSocket disconnected");
      } catch (err) {
        console.error("Initialization error:", err);
        setMessages((prev) => [
          ...prev,
          { text: `Error: ${err.message}`, sender: "bot" },
        ]);
      } finally {
        if (!cancelled) setSessionStarting(false);
      }
    };

    initializeSession();

    return () => {
      cancelled = true;
      if (socketRef.current) socketRef.current.close();
    };
  }, [convId, projectDraft?.title, projectDraft?.description]);

  const handleBaselineSubmit = async (e) => {
    e.preventDefault();
    if (!inputValue.trim() || !convId) return;

    const baselineText = inputValue;
    setMessages((prev) => [...prev, { text: baselineText, sender: "user" }]);
    setInputValue("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/elicitation/baseline?conv_id=${convId}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${getAuthToken()}`,
          },
          body: JSON.stringify({ baseline_text: baselineText }),
        },
      );

      if (!response.ok) throw new Error("Failed to collect baseline");

      const data = await response.json();
      setMessages((prev) => [...prev, { text: data.response, sender: "bot" }]);
      if (Array.isArray(data.requirements) && data.requirements.length) {
        setRequirements(data.requirements);
      }
      if (data.aspects) console.log("📋 Aspects identified:", data.aspects);

      setBaselineCollected(true);
    } catch (err) {
      console.error("❌ Baseline error:", err);
      setMessages((prev) => [
        ...prev,
        { text: `Error: ${err.message}`, sender: "bot" },
      ]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!inputValue.trim() || !convId || !baselineCollected) return;

    const userMessage = inputValue;
    setMessages((prev) => [...prev, { text: userMessage, sender: "user" }]);
    setInputValue("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/elicitation/chat?conv_id=${convId}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${getAuthToken()}`,
          },
          body: JSON.stringify({ message: userMessage }),
        },
      );

      if (!response.ok) throw new Error("Failed to send message");

      const data = await response.json();
      if (data.response) {
        setMessages((prev) => [
          ...prev,
          { text: data.response, sender: "bot" },
        ]);
      }
      if (data.requirements) {
        setRequirements(data.requirements);
      }
    } catch (err) {
      console.error("❌ Chat error:", err);
      setMessages((prev) => [
        ...prev,
        { text: `Error: ${err.message}`, sender: "bot" },
      ]);
    }
  };

  const handleDeleteRequirement = async (index) => {
    if (!convId) return;

    try {
      const response = await fetch(`${API_BASE_URL}/elicitation/requirement?conv_id=${convId}&index=${index}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${getAuthToken()}`,
        },
      });

      if (!response.ok) throw new Error("Failed to delete requirement on server");

      // Update local state only if backend delete was successful
      setRequirements((prev) => prev.filter((_, i) => i !== index));
      if (editingIndex === index) {
        setEditingIndex(null);
        setEditingText("");
      }
    } catch (err) {
      console.error("❌ Delete error:", err);
      alert(`Could not delete: ${err.message}`);
    }
  };

  const handleSaveEdit = async (index) => {
    if (!editingText.trim() || !convId) return;

    try {
      const response = await fetch(`${API_BASE_URL}/elicitation/requirement?conv_id=${convId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${getAuthToken()}`,
        },
        body: JSON.stringify({ index: index, new_text: editingText.trim() }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to update requirement on server");
      }

      // Update local state only if backend edit was successful
      const updatedRequirements = [...requirements];
      updatedRequirements[index] = editingText.trim();
      setRequirements(updatedRequirements);
      setEditingIndex(null);
      setEditingText("");
    } catch (err) {
      console.error("❌ Edit error:", err);
      alert(`Could not update: ${err.message}`);
    }
  };

  const handleStartEdit = (index) => {
    setEditingIndex(index);
    setEditingText(requirements[index]);
  };

  const endElicitation = async () => {
    if (requirements.length === 0) {
      alert("Please collect at least one requirement before ending elicitation.");
      return;
    }

    if (!convId) return;

    try {
      const response = await fetch(
        `${API_BASE_URL}/elicitation/end?conv_id=${convId}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${getAuthToken()}`,
          },
        },
      );

      if (!response.ok) throw new Error("Failed to end elicitation");

      const data = await response.json();
      console.log("📄 Elicitation ended, workflow started:", data);
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
      navigate(`/project/${convId}/refined-animation`);
    } catch (err) {
      console.error("❌ End elicitation error:", err);
      alert(`Error: ${err.message}`);
    }
  };

  if (sessionStarting) return <ModelAnimation />;

  return (
    <div
      className="elicitation-container"
      style={{
        // Dynamically update grid columns based on both left and right sidebar states
        gridTemplateColumns: `${isSidebarOpen ? "250px" : "0px"} 1fr ${
          isOpen ? "25%" : "0%"
        }`,
      }}
    >
      <div className="navbar">
        {/* Toggle Button for Left Sidebar */}
        <button 
          className="sidebar-toggle-btn"
          onClick={() => setIsSidebarOpen(!isSidebarOpen)}
        >
          {isSidebarOpen ? "Hide Requirements" : "Show Requirements"}
        </button>

        <button
          type="button"
          className="end-elicitation"
          onClick={endElicitation}
        >
          End Elicitation
        </button>
      </div>

      {/* Left sidebar with requirements list */}
      <div 
        className="left-sidebar" 
        style={{ borderRight: isSidebarOpen ? "1.5px solid #eef1f8" : "none" }}
      >
        <div className="sidebar-header">
          <h3>Requirements</h3>
          <span className="req-count">{requirements.length}</span>
        </div>

        {requirements.length === 0 ? (
          <div className="empty-sidebar">
            <CiCircleList className="empty-sidebar-icon" />
            <p>No requirements yet</p>
          </div>
        ) : (
          <ul className="left-requirements-list">
            {requirements.map((req, i) => (
              <li key={i} className="req-item">
                {editingIndex === i ? (
                  <div className="req-edit-mode">
                    <input
                      type="text"
                      value={editingText}
                      onChange={(e) => setEditingText(e.target.value)}
                      className="req-edit-input"
                      autoFocus
                    />
                    <div className="req-edit-buttons">
                      <button onClick={() => handleSaveEdit(i)} className="req-btn save-btn">
                        ✓
                      </button>
                      <button
                        onClick={() => {
                          setEditingIndex(null);
                          setEditingText("");
                        }}
                        className="req-btn cancel-btn"
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="req-view-mode">
                    <div className="req-text" style={{color:'black'}}>{req}</div>
                    <div className="req-actions">
                      <button onClick={() => handleStartEdit(i)} className="req-btn edit-btn" title="Edit">
                        ✎
                      </button>
                      <button onClick={() => handleDeleteRequirement(i)} className="req-btn delete-btn" title="Delete">
                        🗑
                      </button>
                    </div>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Chat Section */}
      <div className="chat-section">
        <div className="top-bar">
          <SiPlanetscale className="icon-logo" />
          <div>
            <h3>{projectDraft?.title || "Requirements Assistant"}</h3>
            <p>Let's gather your software requirements!</p>
          </div>
        </div>

        <div ref={messagesRef} className="conversation-container">
          {messages.length === 0 ? (
            <div className="empty-conversation">
              <CiCircleList className="empty-conversation-icon" />
              <p>No messages yet. Start the conversation!</p>
            </div>
          ) : (
            messages.map((msg, i) => (
              <div key={i} className={`message ${msg.sender}`}>
                {msg.sender === "user" ? (
                  <FaRegUser className={`icon-${msg.sender}`} />
                ) : (
                  <GoDependabot className={`icon-${msg.sender}`} />
                )}
                {msg.sender === "user" ? (
                  <p className={`text-${msg.sender}`}>{msg.text}</p>
                ) : (
                  <div className={`text-${msg.sender} markdown-body`}>
                    <ReactMarkdown>{msg.text}</ReactMarkdown>
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        <div className="input-container">
          <div className="send-message">
            <form onSubmit={baselineCollected ? handleSubmit : handleBaselineSubmit}>
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder={
                  baselineCollected
                    ? "Describe your software requirements..."
                    : "Describe your software system..."
                }
              />
            </form>

            {/* Removed the Attachment Button completely from here */}
            
            <button
              type="button"
              onClick={baselineCollected ? handleSubmit : handleBaselineSubmit}
              className="icon-button"
            >
              <IoIosSend className="icon-send" />
            </button>
          </div>
          <p>Press Enter to send</p>
        </div>
      </div>

      {/* Right requirements panel */}
      {isOpen ? (
        <div className="right-list-section">
          <div
            className="toggle-header"
            onClick={() => setIsOpen(!isOpen)}
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              cursor: "pointer",
            }}
          >
            <h3>Requirements Collector</h3>
            <button
              className="requirement-toggle"
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                fontSize: "1.5rem",
              }}
            >
              −
            </button>
          </div>

          {requirements.length === 0 ? (
            <div className="empty-list">
              <CiCircleList className="empty-list-icon" />
              <p>No Requirements Yet</p>
            </div>
          ) : (
            <ul ref={requirementRef} className="requirements-list">
              {requirements.map((r, i) => (
                <li key={i}>
                  {r}
                  <p>{i + 1}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : (
        <div
          className="right-list-section"
          style={{ width: 0, padding: 0, overflow: "visible" }}
        >
          <div
            className="toggle-header"
            onClick={() => setIsOpen(true)}
            style={{
              position: "absolute",
              right: "10px",
              top: "6rem",
              zIndex: "1",
              cursor: "pointer",
              background: "var(--grey-light)",
              borderRadius: "8px",
              padding: "6px 10px",
              boxShadow: "0 2px 5px rgba(0,0,0,0.1)",
            }}
          >
            <button className="toggle-requirement-collector">+</button>
          </div>
        </div>
      )}
    </div>
  );
}