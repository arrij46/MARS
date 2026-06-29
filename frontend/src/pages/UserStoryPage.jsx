import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { FaArrowLeft, FaDownload, FaFileDownload } from "react-icons/fa";
import "../style/UserStoryPage.css";
import jsPDF from "jspdf";
import html2canvas from "html2canvas";
import { FaChevronDown } from "react-icons/fa";
import { downloadUserStoryPDF } from "../utils/downloadUserStory";


export default function UserStoryPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [userStories, setUserStories] = useState([]);
  const [projectTitle, setProjectTitle] = useState("User Stories");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isExporting, setIsExporting] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState(null);
  const [evaluations, setEvaluations] = useState([]);
  const [expandedIndex, setExpandedIndex] = useState(null);
  const [convId, setConvId] = useState(null);
  const [showAQUSA, setShowAQUSA] = useState(true);
  const [showURQ, setShowURQ] = useState(true);

  useEffect(() => {
    if (projectId) {
      loadUserStories();
    }
  }, [projectId]);

  useEffect(() => {
    if (convId) {
      loadEvaluations(convId);
    }
  }, [convId]);

  const loadEvaluations = async (convIdParam) => {
    try {
      const response = await fetch(
        `http://localhost:8000/api/evaluation_results/${convIdParam}`,
      );
      if (response.ok) {
        const data = await response.json();
        setEvaluations(data.evaluations || []);
      }
    } catch (err) {
      setEvaluations([]);
    }
  };

  const loadUserStories = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(
        `http://localhost:8000/api/user_stories_file/${projectId}`,
      );
      if (!response.ok) {
        throw new Error("Failed to load user stories");
      }

      const data = await response.json();

      const title =
        data.metadata?.project_name ||
        data.project_title ||
        "User Stories Report";

      setProjectTitle(title);
      setUserStories(data.user_stories || []);

      if (data.conv_id) {
        setConvId(data.conv_id);
      }
    } catch (err) {
      console.error("Error loading user stories:", err);
      setError(err.message || "Failed to load user stories");
    } finally {
      setLoading(false);
    }
  };

  const exportPDF = async () => {
    try {
      setIsExporting(true);

      const contentElement = document.getElementById("user-stories-content");

      if (!contentElement) {
        throw new Error("Could not find content to export");
      }

      const canvas = await html2canvas(contentElement, {
        allowTaint: true,
        useCORS: true,
        backgroundColor: "#ffffff",
      });

      const imgData = canvas.toDataURL("image/png");
      const pdf = new jsPDF({
        orientation: "portrait",
        unit: "mm",
        format: "a4",
      });

      const pageWidth = pdf.internal.pageSize.getWidth();
      const pageHeight = pdf.internal.pageSize.getHeight();
      const margin = 15;
      const contentWidth = pageWidth - 2 * margin;

      const imgWidth = contentWidth;
      const imgHeight = (canvas.height * imgWidth) / canvas.width;

      let heightLeft = imgHeight;
      let position = 0;

      pdf.addImage(
        imgData,
        "PNG",
        margin,
        position + margin,
        imgWidth,
        imgHeight,
      );
      heightLeft -= pageHeight - 2 * margin;

      while (heightLeft > 0) {
        position = heightLeft - imgHeight;
        pdf.addPage();
        pdf.addImage(
          imgData,
          "PNG",
          margin,
          position + margin,
          imgWidth,
          imgHeight,
        );
        heightLeft -= pageHeight - 2 * margin;
      }

      const filename = `${projectTitle.replace(/\s+/g, "_")}_UserStories.pdf`;
      pdf.save(filename);

      console.log("[UI] User stories exported to PDF successfully");
    } catch (err) {
      console.error("[UI] Error exporting PDF:", err);
      setError(err.message || "Failed to export PDF");
    } finally {
      setIsExporting(false);
    }
  };

  const handleDownloadUserStoryPDF = async () => {
    try {
      setIsDownloading(true);
      setDownloadError(null);

      if (!convId) {
        throw new Error("Conversation ID not available. Please reload the page.");
      }

      await downloadUserStoryPDF(
        convId,
        null,
        () => {
          console.log("[UI] User story PDF downloaded successfully");
        },
        (err) => {
          throw err;
        }
      );
    } catch (err) {
      console.error("[UI] Error downloading user story PDF:", err);
      setDownloadError(err.message || "Failed to download PDF");
    } finally {
      setIsDownloading(false);
    }
  };

  if (loading) {
    return (
      <div className="user-story-page-container">
        <div className="loading-container">
          <div className="spinner-border text-primary" role="status">
            <span className="visually-hidden">Loading...</span>
          </div>
          <p className="mt-3">Loading user stories...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="user-story-page-container">
       
      <div className="user-story-header">
        <button
          className="dashboard-btn"
          onClick={() => navigate(`/dashboard/${projectId}`)}
        >
        Dashboard
        </button>
        <h1 className="page-title">{projectTitle}</h1>

        <div className="button-group">
          <button
            className="btn btn-success export-button"
            onClick={exportPDF}
            disabled={isExporting || userStories.length === 0}
            title="Export user stories as PDF (rendering current page)"
          >
            {isExporting ? (
              <>
                <span
                  className="spinner-border spinner-border-sm me-2"
                  role="status"
                  aria-hidden="true"
                ></span>
                Exporting...
              </>
            ) : (
              <>
                <FaDownload className="me-2" />
                Export Report
              </>
            )}
          </button>

          <button
            className="btn btn-primary download-user-story-button"
            onClick={handleDownloadUserStoryPDF}
            disabled={isDownloading || !convId}
            title="Download generated user stories PDF from backend"
          >
            {isDownloading ? (
              <>
                <span
                  className="spinner-border spinner-border-sm me-2"
                  role="status"
                  aria-hidden="true"
                ></span>
                Downloading...
              </>
            ) : (
              <>
                <FaFileDownload className="me-2" />
                Download User Stories PDF
              </>
            )}
          </button>
        </div>
      </div>

      {downloadError && (
        <div className="alert alert-warning alert-container" role="alert">
          <strong>Download Notice:</strong> {downloadError}
        </div>
      )}

      {error && (
        <div className="alert alert-danger alert-container" role="alert">
          <strong>Error:</strong> {error}
        </div>
      )}

      <div id="user-stories-content" className="user-stories-content">
        <div className="content-wrapper">
          <h2 className="content-title">{projectTitle}</h2>

          {userStories.length === 0 ? (
            <div className="empty-state">
              <p>No user stories found. Please generate them first.</p>
            </div>
          ) : (
            <>
              <div className="eval-filters-global">
                <label className="eval-checkbox" htmlFor="aqusaCheckbox">
                  <input
                    id="aqusaCheckbox"
                    type="checkbox"
                    checked={showAQUSA}
                    onChange={(e) => setShowAQUSA(e.target.checked)}
                  />
                  <span>AQUSA</span>
                </label>
                <label className="eval-checkbox" htmlFor="urqCheckbox">
                  <input
                    id="urqCheckbox"
                    type="checkbox"
                    checked={showURQ}
                    onChange={(e) => setShowURQ(e.target.checked)}
                  />
                  <span>URQ</span>
                </label>
              </div>
              <div className="user-stories-list">
                <p className="total-count">
                  Total User Stories: {userStories.length}
                </p>
              {userStories.map((story, index) => {
                const evalData = evaluations.find(
                  (e) =>
                    String(e.requirement_id) === String(story.requirement_id),
                );

                const verdict = evalData?.final_verdict?.toUpperCase() || "LOW_QUALITY";

                const displayRating =
                  verdict === "HIGH_QUALITY"
                    ? "High Quality"
                    : verdict === "MODERATE_QUALITY"
                    ? "Medium Quality"
                    : "Low Quality";
                return (
                  <div key={index} className="user-story-card-wrapper">
                    <div className="user-story-card">
                      <div className="story-header">
                        <div>
                          <span className="story-number">
                            Story {index + 1}
                          </span>
                        </div>

                        <span
                          className={`story-badge ${
                            displayRating === "High Quality"
                              ? "badge-high"
                              : displayRating === "Medium Quality"
                                ? "badge-med"
                                : displayRating === "Low Quality"
                                  ? "badge-low"
                                  : ""
                          }`}
                          onClick={() =>
                            setExpandedIndex(
                              expandedIndex === index ? null : index,
                            )
                          }
                        >
                          {displayRating}

                          <FaChevronDown
                            className={`arrow ${expandedIndex === index ? "rotate" : ""}`}
                          />
                        </span>
                      </div>

                      <div className="story-content">
                        {story.title && (
                          <h4 className="story-title">{story.title}</h4>
                        )}

                        {story.text && (
                          <p className="story-text">{story.text}</p>
                        )}

                        {story.acceptance_criteria && (
                          <div className="story-section">
                            <h5 className="section-label">
                              Acceptance Criteria:
                            </h5>
                            <p className="section-content">
                              {story.acceptance_criteria}
                            </p>
                          </div>
                        )}

                        {story.priority && (
                          <div className="story-metadata">
                            <span
                              className={`priority-badge priority-${story.priority.toLowerCase()}`}
                            >
                              {story.priority}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>

                    {expandedIndex === index && evalData && (
                      <div className="evaluation-dropdown">
                        {showAQUSA && (
                          <div className="eval-section">
                            <strong>AQUSA:</strong>
                            <span className="eval-item">
                              Well Formed: {evalData.well_formed ? "Yes" : "No"}
                            </span>
                            <span className="eval-item">
                              Atomic: {evalData.atomic ? "Yes" : "No"}
                            </span>
                            <span className="eval-item">
                              Minimal: {evalData.minimal ? "Yes" : "No"}
                            </span>
                            <span className="eval-item">
                              Full Sentence:{" "}
                              {evalData.full_sentence ? "Yes" : "No"}
                            </span>
                            <span className="eval-item">
                              Estimatable: {evalData.estimatable ? "Yes" : "No"}
                            </span>
                            <span className="eval-item">
                              Uniform: {evalData.uniform ? "Yes" : "No"}
                            </span>
                            <span className="eval-item">
                              Unique: {evalData.unique ? "Yes" : "No"}
                            </span>
                            <span className="eval-item">
                              Complete Dependency: {evalData.complete_dependency ? "Yes" : "No"}
                            </span>
                          </div>
                        )}

                        {showURQ && (
                          <div className="eval-section">
                            <strong>URQ:</strong>
                            <span className="eval-item">
                              Complete: {evalData.urq_complete ? "Yes" : "No"}
                            </span>
                            <span className="eval-item">
                              Simple: {evalData.urq_simple ? "Yes" : "No"}
                            </span>
                            <span className="eval-item">
                              Accurate: {evalData.urq_accurate ? "Yes" : "No"}
                            </span>
                            <span className="eval-item">
                              Consistent: {evalData.urq_consistent ? "Yes" : "No"}
                            </span>
                            <span className="eval-item">
                              Unique Semantic:{" "}
                              {evalData.urq_unique_semantic ? "Yes" : "No"}
                            </span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

