import React, { useState, useEffect, useRef } from "react";
import {
  FaCog,
  FaQuestionCircle,
  FaSignOutAlt,
  FaPlus,
  FaSearch,
  FaPlay,
  FaUpload,
  FaArrowRight,
  FaChevronRight,
  FaChevronLeft,
} from "react-icons/fa";
import { useNavigate } from "react-router-dom";
import { authFetch } from "../utils/api";
import { connectWebSocket, closeWebSocket } from "../utils/websocket";
import Popup from "../components/Popup";
import {Report, SRSSection} from "../components/Report";
import ModelAnimation from "../components/modelAnnimation";
import TemplatePopup from "../components/editor-page/templatePopup"; //ADDED
import "../style/Dashboard.css";
import { useParams } from "react-router-dom";
import { useLocation } from "react-router-dom";


export default function Dashboard() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [projects, setProjects] = useState([]);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [createProjectDraft, setCreateProjectDraft] = useState({
    title: "",
    description: "",
  });
  const location = useLocation();
  const [selectedProject, setSelectedProject] = useState(null);
  const [rightPanelVisible, setRightPanelVisible] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [showPopup, setShowPopup] = useState(false);
  const [convId, setConvId] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [showTemplatePopup, setShowTemplatePopup] = useState(false); //ADDED
  const wsConnected = useRef(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [reportdata, setReportData] = useState(null);
  const [showUserStorySection, setShowUserStorySection] = useState(true);
  const [showQualityAssessment, setShowQualityAssessment] = useState(true);
  
  // ✅ OPTIMIZATION: State for refresh tracking
  const [lastRefresh, setLastRefresh] = useState(Date.now());
  const [reportLoading, setReportLoading] = useState(false);

  const userName = localStorage.getItem("user_name") || "User";

  const CollapsibleSection = ({ title, show, setShow, children }) => (
    <div className="collapsible-section">
      <div className="section-header">
        <h3>{title}</h3>
        <button
          className="toggle-btn"
          onClick={() => setShow(!show)}
          title={show ? "Hide" : "Show"}
        >
          {show ? "−" : "+"}
        </button>
      </div>
      {show && <div className="section-content">{children}</div>}
    </div>
  );
  
  // ✅ OPTIMIZATION: Refetch projects from backend
  const refreshProjects = React.useCallback(async () => {
    try {
      const res = await authFetch("/api/fetch_projects");
      const data = await res.json();
      setProjects(data.projects);
      console.log("[Dashboard] Projects refreshed:", data.projects.length);
      setLastRefresh(Date.now());
    } catch (err) {
      console.error("[Dashboard] Failed to refresh projects:", err);
    }
  }, []);
  
  // ✅ OPTIMIZATION: Detect when Dashboard comes into focus (tab visibility)
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        console.log("[Dashboard] Became visible, refreshing projects...");
        refreshProjects();
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, [refreshProjects]);

  // ✅ OPTIMIZATION: Update WebSocket listener to handle report_ready signal
  useEffect(() => {
    if (!convId || wsConnected.current) return;
    console.log("[Dashboard] Connecting WS for project:", convId);

    connectWebSocket(convId, (message) => {
      console.log("[WebSocket] Message received:", message);

      // ✅ NEW: Listen for report completion signal
      if (message.step === "report_ready") {
        console.log("[Dashboard] Report is ready! Refreshing projects...");
        setReportLoading(false);
        refreshProjects();
      }

      if (message.step === "workflow_complete") {
        alert("Workflow completed!");
        refreshProjects();
      }
      console.log("URL projectId:", projectId);
    });

    wsConnected.current = true;

    return () => {
      closeWebSocket();
      wsConnected.current = false;
    };
  }, [convId, navigate, projectId, refreshProjects]);

  // ✅ OPTIMIZATION: Initial projects fetch on mount
  useEffect(() => {
    const fetchProjects = async () => {
      try {
        const res = await authFetch("/api/fetch_projects");
        const data = await res.json();
        setProjects(data.projects);
        console.log("Projects fetched:", data.projects);
      } catch (err) {
        console.error("Failed to fetch projects:", err);
      }
    };

    fetchProjects();
  }, []);

  // ✅ OPTIMIZATION: Periodic polling fallback (every 5 seconds when tab is visible)
  useEffect(() => {
    const pollInterval = setInterval(() => {
      if (!document.hidden) {
        const timeSinceLastRefresh = Date.now() - lastRefresh;
        if (timeSinceLastRefresh > 5000) { // Only refresh if 5+ seconds have passed
          console.log("[Dashboard] Polling projects (fallback)...");
          refreshProjects();
        }
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  }, [lastRefresh, refreshProjects]);


  // RESTORE PROJECT FROM URL
  useEffect(() => {
    if (!projects || projects.length === 0) return;
    if (!projectId) return;

    console.log("URL projectId:", projectId);
    console.log("Projects list:", projects);

    const restoredProject = projects.find(
      p =>
        String(p.conv_id).trim() ===
        String(projectId).trim()
    );

    console.log(
      "Project restored:",
      restoredProject,
      "conv_id:",
      projectId
    );

    if (restoredProject) {
      setSelectedProject(restoredProject);
      setRightPanelVisible(true);
      setReportData(restoredProject.report);
    }
  }, [projects, projectId]);

  useEffect(() => {
    if (location.state?.openSRS) {
      const convId = location.state.convId;
      const skipTemplate = location.state.showTemplateSelection === false;

      navigate(location.pathname, { replace: true, state: {} });

      if (skipTemplate) {
        navigate(`/project/${convId}/editor`);
      } else {
        setShowTemplatePopup(true);
      }
    }
  }, [location.state]);
  useEffect(() => {
    if (location.state?.triggerUpload) {
      navigate(location.pathname, { replace: true, state: {} });
      setShowPopup(true);
    }
  }, [location.state]);

  const handleFileSelect = async (file) => {
    if (!file) return;

    setUploadedFile(file);
    setShowPopup(false);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("title", createProjectDraft.title);
      formData.append("description", createProjectDraft.description);

      const response = await authFetch("/api/upload", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ detail: "Upload failed" }));
        throw new Error(
          errorData.detail || `HTTP error! status: ${response.status}`,
        );
      }

      const data = await response.json();
      console.log("Server response:", data);

      if (data.status === "success") {
        console.log("[Dashboard] Workflow started for project:", data.conv_id);
        // Navigate immediately to refined-animation page
        navigate(`/project/${data.conv_id}/refined-animation`);
      } else {
        alert(data.message || "File uploaded successfully");
      }
    } catch (err) {
      console.error(" Upload error:", err);
      alert("Upload failed. Check backend logs or file format.");
    }
  };

  const handleCreateProject = (mode) => {
    if (
      !createProjectDraft.title.trim() ||
      !createProjectDraft.description.trim()
    ) {
      alert("Please enter both title and description");
      return;
    }

    if (mode === "elicit") {
      const convId = `conv-${crypto.randomUUID()}`;
      navigate(`/project/${convId}/elicit`, {
        state: { projectDraft: createProjectDraft },
      });
    } else if (mode === "upload") {
      setShowPopup(true);
    }
  };

  const handleNewProject = () => {
    setRightPanelVisible(true);
    setSelectedProject(null);
    setReportData(null);
    navigate(`/dashboard`);
  };

  const filteredProjects = projects.filter(
    (p) =>
      p.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.description.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  return (
    <div
      className={`dashboard-container${!rightPanelVisible ? " panels-full" : ""}`}
    >
      <div className="left-panel">
        <div className="left-panel-inner">
          <div className="greeting-block">
            <h1 className="greeting-name">Hi, {userName}</h1>
            <p className="greeting-sub">
              Welcome back. Manage projects, analyze requirements, or start a
              new one.
            </p>
          </div>

          <div className="search-create-container">
            <div className="search-bar">
              <FaSearch className="search-icon" />
              <input
                type="text"
                placeholder="Search projects..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <button className="create-btn" onClick={handleNewProject}>
              <FaPlus /> New Project
            </button>
          </div>

          <div className="project-scroll-wrapper">
            <div className="project-grid">
              {(() => {
                // REMOVE DUPLICATES
                const uniqueProjects = Array.from(
                  new Map(
                    filteredProjects.map(project => [project.conv_id, project])
                  ).values()
                );
                console.log("Unique Projects:", uniqueProjects);

                // RENDER
                return uniqueProjects.map((project, index) => (
                  <div className="project-card" key={`${project.conv_id}-${index}`}>
                    <div className="project-card-body">
                      <span className="project-date">{project.date}</span>
                      <h3 className="project-title">{project.title}</h3>
                      <p className="project-desc">{project.description}</p>
                    </div>
                    <button
                      className="expand-btn"
                      onClick={() => {
                        setSelectedProject(project);
                        setRightPanelVisible(true);
                        setReportData(project.report);
                        console.log("project.report:", project.conv_id);
                        navigate(`/dashboard/${project.conv_id}`);
                      }}
                    >
                      Open Project <FaArrowRight className="expand-arrow" />
                    </button>
                  </div>
                ));
              })()}
            </div>
          </div>
        </div>

        <button
          className="user-menu-btn"
          onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
          title="Menu"
        >
          ☰
        </button>

        {isUserMenuOpen && (
          <div className="user-dropdown-panel open">
            <button className="dropdown-item">
              <FaCog className="dropdown-icon-left" />
              <span>Settings</span>
            </button>
            <button className="dropdown-item">
              <FaQuestionCircle className="dropdown-icon-left" />
              <span>Help</span>
            </button>
            <div className="dropdown-divider"></div>
            <button
              className="dropdown-item logout"
              onClick={() => {
                localStorage.removeItem("token");
                localStorage.removeItem("user");
                navigate("/auth");
              }}
            >
              <FaSignOutAlt className="dropdown-icon-left" />
              <span>Logout</span>
            </button>
          </div>
        )}
      </div>

      {rightPanelVisible && (
        <div
          className="right-card"
          style={{
            flex: isExpanded ? "0 0 calc(100% - 40px)" : "1",
            margin: isExpanded ? "0 20px" : "0 20px 0 0",
            borderRadius: "26px",
            overflow: "hidden",
            transition: "all 0.3s ease",
          }}
        >
          <div className="right-card-header">
            {/* Toggle expand/collapse */}
            <button
              className="open-panel-btn"
              onClick={() => setIsExpanded((prev) => !prev)} // toggle
              title={isExpanded ? "Shrink" : "Expand"}
            >
              {isExpanded ? <FaChevronRight /> : <FaChevronLeft />}
            </button>

            <h2 className="right-card-title">MARS System</h2>

            {/* Collapse panel (unchanged) */}
            <button
              className="close-panel-btn"
              onClick={() => setRightPanelVisible(false)}
              title="Collapse"
            >
              ✕
            </button>
          </div>
          <main className="chat-main-panel">
            {selectedProject ? (
              <div className="creation-workspace">
                <div className="workspace-header">
                  <h3 className="workspace-title">{selectedProject.title}</h3>
                  <h4 className="workspace-id">
                    Project ID: {selectedProject.conv_id}
                  </h4>
                  <p className="workspace-subtitle">
                    {selectedProject.description}
                  </p>
                </div>
              </div>
            ) : (
              <div className="creation-workspace">
                <div className="workspace-header">
                  <h3 className="workspace-title">Start New Project</h3>
                  <p className="workspace-subtitle">
                    Initialize a requirements engineering workflow
                  </p>
                </div>

                <div className="creation-panel">
                  <div className="input-group">
                    <label className="input-label">Project Title</label>
                    <input
                      type="text"
                      className="creation-input"
                      placeholder="e.g., Healthcare Management System"
                      value={createProjectDraft.title}
                      onChange={(e) =>
                        setCreateProjectDraft({
                          ...createProjectDraft,
                          title: e.target.value,
                        })
                      }
                    />
                  </div>

                  <div className="input-group">
                    <label className="input-label">Description</label>
                    <textarea
                      className="creation-textarea"
                      placeholder="Brief project context..."
                      rows={3}
                      value={createProjectDraft.description}
                      onChange={(e) =>
                        setCreateProjectDraft({
                          ...createProjectDraft,
                          description: e.target.value,
                        })
                      }
                    />
                  </div>

                  <div className="creation-actions">
                    <button
                      className="action-btn elicit-btn"
                      onClick={() => handleCreateProject("elicit")}
                    >
                      <FaPlay className="btn-icon" />
                      Start Elicitation
                    </button>
                    <button
                      className="action-btn secondary"
                      onClick={() => handleCreateProject("upload")}
                    >
                      <FaUpload className="btn-icon" />
                      Upload Requirements
                    </button>
                  </div>

                  <div className="creation-hint">
                    <p>
                      <strong>Elicitation:</strong> Guided workflow to gather
                      requirements interactively
                    </p>
                    <p>
                      <strong>Upload:</strong> AI agents extract and analyze
                      requirements from documents
                    </p>
                  </div>
                </div>
              </div>
            )}
            {selectedProject && (
              <SRSSection convId={projectId} navigate={navigate} />
            )}

            <div className="report">
              {reportdata ? (
                <Report report={reportdata} isLoading={reportLoading} />
              ) : reportLoading ? (
                <Report report={null} isLoading={true} />
              ) : null}
              {/* {selectedProject && (
                <div className="rr-section-wrapper">
                  <div className="rr-header">
                    <h4 className="rr-header-title">
                      Evolve Your Requirements
                    </h4>
                  </div>
                  <div className="rr-section">
                    <div className="rr-card">
                      <p className="rr-card-description">
                        Expand this project by adding new requirements, elicit
                        them interactively or upload a document to generate an
                        updated SRS.
                      </p>
                      <div className="rr-actions">
                        <div className="rr-action">
                          <p className="rr-action-text">
                            Gather requirements through a guided conversation
                            with the AI.
                          </p>
                          <button
                            className="evolve-section-btn"
                            onClick={() => handleCreateProject("elicit")}
                          >
                            Start Elicitation
                          </button>
                        </div>
                        <div className="rr-action">
                          <p className="rr-action-text">
                            Upload a requirements document and let the AI
                            extract and analyze it.
                          </p>
                          <button
                            className="evolve-section-btn"
                            onClick={() => setShowPopup(true)}
                          >
                            Upload Requirements
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}*/}
            </div>
          </main>
        </div>
      )}

      {showPopup && (
        <Popup
          onFileSelect={handleFileSelect}
          onClose={() => setShowPopup(false)}
        />
      )}

      {/*TEMPLATE POPUP (SAME AS REFINED PAGE) */}
      {showTemplatePopup && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
          <TemplatePopup onClose={() => setShowTemplatePopup(false)} />
        </div>
      )}
    </div>
  );
}
