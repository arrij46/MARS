import React, { useState, useEffect } from "react";
import { authFetch } from "../utils/api";
import { useNavigate, useLocation, useParams } from "react-router-dom";
import "../style/refinedRequirementsList.css";
import {
  RequirementCard,
  NFRSection,
} from "../components/refined-requirements-page/RequirementCard";
import TemplatePopup from "../components/editor-page/templatePopup";

export default function RefinedRequirementsList() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const results = location.state?.results; // results sent from animation page
  const [functionalReqs, setFunctionalReqs] = useState([]);
  const [securityNFR, setSecurityNFR] = useState([]);
  const [reliabilityNFR, setReliabilityNFR] = useState([]);
  const [performanceNFR, setPerformanceNFR] = useState([]);
  const [usabilityNFR, setUsabilityNFR] = useState([]);
  const [otherNFR, setOtherNFR] = useState([]);
  const [showTemplatePopup, setShowTemplatePopup] = useState(false);

  // toggle states for collapsible sections
  const [functionalOpen, setFunctionalOpen] = useState(true);
  const [nfrOpen, setNfrOpen] = useState(true);

  // clusters for advanced view
  const [advancedView, setAdvancedView] = useState(false);
  const [clusters, setClusters] = useState([]);
  const [clustersOpen, setClustersOpen] = useState(() =>
    Object.fromEntries(clusters.map((_, i) => [i, true])),
  );

  const toggleCluster = (index) => {
    setClustersOpen((prev) => ({ ...prev, [index]: !prev[index] }));
  };
  useEffect(() => {
    const loadRequirements = async () => {
      try {
        const res = await authFetch(
          `/api/requirements_file?conv_id=${encodeURIComponent(projectId)}`,
        );
        const data = await res.json();
        console.log("[Refinement UI] results freched from file", data);
        const requirements = data.requirements?.requirements || [];
        const functional = requirements
          .filter((r) => r.type === "Functional")
          .map((r) => ({ id: r.id, text: r.text }));
        setFunctionalReqs(functional);

        const nfrs = requirements.filter((r) => r.type === "Non-Functional");

        setSecurityNFR(nfrs.filter((r) => r.subtype === "security"));
        setReliabilityNFR(nfrs.filter((r) => r.subtype === "reliability"));
        setPerformanceNFR(nfrs.filter((r) => r.subtype === "performance"));
        setUsabilityNFR(nfrs.filter((r) => r.subtype === "usability"));
        setOtherNFR(nfrs.filter((r) => r.subtype === "other"));

        // get clusters for advanced
        const cluster = data.clusters || [];
        setClusters(cluster);

        console.log("[Refinement UI] clusters freched from file", cluster);
      } catch (err) {
        console.error("Error loading requirements file:", err);
      }
    };

    if (projectId) loadRequirements();
  }, [projectId]);
  useEffect(() => {
    if (!results) return;

    const requirements = results?.requirements || [];

    const functional = requirements
      .filter((r) => r.type === "Functional")
      .map((r) => ({ id: r.id, text: r.text }));
    setFunctionalReqs(functional);

    const nfrs = requirements.filter((r) => r.type === "Non-Functional");
    setSecurityNFR(nfrs.filter((r) => r.subtype === "security"));
    setReliabilityNFR(nfrs.filter((r) => r.subtype === "reliability"));
    setPerformanceNFR(nfrs.filter((r) => r.subtype === "performance"));
    setUsabilityNFR(nfrs.filter((r) => r.subtype === "usability"));
    setOtherNFR(nfrs.filter((r) => r.subtype === "other"));
  }, [results]);

  const nfrSections = [
    { title: "Security", items: securityNFR, setItems: setSecurityNFR },
    {
      title: "Reliability",
      items: reliabilityNFR,
      setItems: setReliabilityNFR,
    },
    {
      title: "Performance",
      items: performanceNFR,
      setItems: setPerformanceNFR,
    },
    { title: "Usability", items: usabilityNFR, setItems: setUsabilityNFR },
    { title: "Other", items: otherNFR, setItems: setOtherNFR },
  ];

  return (
    <div className="page-wrapper">
      <div className="refined-header-clean">
        <button
          className="dashboard-btn"
          onClick={() => navigate(`/dashboard/${projectId}`)}
        >
          Dashboard
        </button>

        <div className="header-center-block">
          <h2 className="main-heading">Refined and Corrected Requirements</h2>
          <p className="sub-text">
            Review your requirements as needed
            <label className="advanced-toggle">
              <input
                type="checkbox"
                checked={advancedView}
                onChange={() => setAdvancedView(!advancedView)}
              />
              <span>Advanced View</span>
            </label>
          </p>
        </div>
      </div>
      {/* Template Popup */}
      {showTemplatePopup && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
          <TemplatePopup onClose={() => setShowTemplatePopup(false)} />
        </div>
      )}

      <div className="requirement-container">
        {advancedView ? (
          <div className="clusters-view">
            <h4 className="fw-semibold mb-3 section-heading">
              Requirement Clusters
            </h4>
            {clusters.map((cluster, index) => (
              <div key={index} className="nfr-section">
                <div
                  className="nfr-section-header"
                  onClick={() => toggleCluster(index)}
                >
                  <span className="nfr-section-title">Feature {index + 1}</span>
                  <div className="nfr-section-meta">
                    <span className="count-pill">{cluster.length}</span>
                    <span className="nfr-chevron">
                      {clustersOpen[index] ? "▾" : "▸"}
                    </span>
                  </div>
                </div>
                {clustersOpen[index] && (
                  <div className="nfr-section-body">
                    <RequirementCard items={cluster} />
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <>
            {/* Functional Requirements */}
            <div className="Functional_requirements">
              <h4
                className="fw-semibold mb-3 section-heading mt-5"
                onClick={() => setFunctionalOpen(!functionalOpen)}
                style={{ cursor: "pointer" }}
              >
                Functional Requirements
                <div className="nfr-section-meta">
                  <span className="count-pill">{functionalReqs.length}</span>
                  <span className="nfr-chevron">
                    {functionalOpen ? "▾" : "▸"}
                  </span>
                </div>
              </h4>

              {functionalOpen && (
                <>
                  <RequirementCard
                    items={functionalReqs.map(
                      (req) => `REQ-${req.id}:  ${req.text}`,
                    )}
                    onUpdate={(updatedTexts) => {
                      setFunctionalReqs((prev) =>
                        prev.map((req, idx) => ({
                          ...req,
                          text: updatedTexts[idx],
                        })),
                      );
                    }}
                  />
                </>
              )}
            </div>

            {/* Non-Functional Requirements */}
            <h4
              className="fw-semibold mb-3 section-heading mt-5"
              onClick={() => setNfrOpen(!nfrOpen)}
              style={{ cursor: "pointer" }}
            >
              Non-Functional Requirements
              <div className="nfr-section-meta">
                <span className="count-pill">
                  {nfrSections.reduce(
                    (acc, section) => acc + section.items.length,
                    0,
                  )}
                </span>
                <span className="nfr-chevron">{nfrOpen ? "▾" : "▸"}</span>
              </div>
            </h4>

            {nfrOpen && (
              <div className="non-func-req-grid">
                {nfrSections.map((section, index) => (
                  <div key={index}>
                    <NFRSection
                      title={section.title}
                      items={section.items.map(
                        (req) => `REQ-${req.id}:  ${req.text}`,
                      )}
                      setItems={(updatedTexts) => {
                        section.setItems((prev) =>
                          prev.map((req, idx) => ({
                            ...req,
                            text: updatedTexts[idx],
                          })),
                        );
                      }}
                    />
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
