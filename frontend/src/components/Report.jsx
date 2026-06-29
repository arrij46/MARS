import { useState, useMemo } from "react";
import "../style/Report.css";
import { useParams, useNavigate } from "react-router-dom";

/* ─────────────────────────────────────────────────────────────
   COLOUR MAPS  (extend as needed)
   ───────────────────────────────────────────────────────────── */
const NFR_COLORS = {
  Usability: { bg: "#e1f5ee", border: "#9fe1cb", text: "#085041" },
  Performance: { bg: "#e6f1fb", border: "#b5d4f4", text: "#0c447c" },
  Security: { bg: "#fcebeb", border: "#f7c1c1", text: "#501313" },
  Scalability: { bg: "#faeeda", border: "#fac775", text: "#412402" },
  Reliability: { bg: "#eeedfe", border: "#cecbf6", text: "#26215c" },
  Maintainability: { bg: "#f1efe8", border: "#d3d1c7", text: "#2c2c2a" },
  Portability: { bg: "#fbeaf0", border: "#f4c0d1", text: "#4b1528" },
};
const NFR_FALLBACK = {
  bg: "rgba(48,50,53,0.08)",
  border: "rgb(161,161,170)",
  text: "rgb(31,41,55)",
};
const TYPE_BADGE = {
  Functional: { bg: "#e1f5ee", text: "#085041" },
  "Non-Functional": { bg: "#e6f1fb", text: "#0c447c" },
};

function nfrColor(sub) {
  return NFR_COLORS[sub] ?? NFR_FALLBACK;
}
function typeBadge(type) {
  return TYPE_BADGE[type] ?? NFR_FALLBACK;
}

function metricBarColor(pct) {
  if (pct === 100) return "rgb(0,168,151)";
  if (pct >= 93) return "rgb(17,79,212)";
  return "rgb(13,68,145)";
}

function pct(rate) {
  return Math.round(rate * 100);
}
function avgPct(metrics) {
  return Math.round(
    (metrics.reduce((a, m) => a + m.rate, 0) / metrics.length) * 100,
  );
}

/* ─────────────────────────────────────────────────────────────
   LOADING SKELETON COMPONENT (OPTIMIZATION)
   ───────────────────────────────────────────────────────────── */
function ReportSkeleton() {
  return (
    <div className="report-skeleton">
      <div className="skeleton-header">
        <div className="skeleton-line skeleton-title" />
        <div className="skeleton-line skeleton-subtitle" />
      </div>
      <div className="skeleton-content">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="skeleton-section">
            <div className="skeleton-line skeleton-label" />
            <div className="skeleton-line skeleton-value" />
            <div className="skeleton-line skeleton-value short" />
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────
   DATA ADAPTER
   ───────────────────────────────────────────────────────────── */
function adaptReport(report) {
  const meta = report.metadata ?? {};

  const convId = meta.conv_id ?? "—";
  const projectId =
    report.project_id ?? `PRJ-${convId.slice(5, 13).toUpperCase()}`;

  const s = report.summary ?? {};

  const funcSubtypes = report.classification?.types?.Functional?.subtypes ?? {};

  const funcReqs = Object.entries(funcSubtypes).flatMap(
    ([subtype, { requirements = [] }]) =>
      requirements.map((r) => ({
        ...r,
        type: "Functional",
        subtype,
      })),
  );

  const nfSubtypes =
    report.classification?.types?.["Non-Functional"]?.subtypes ?? {};
  const nfReqs = Object.entries(nfSubtypes).flatMap(
    ([subtype, { requirements = [] }]) =>
      requirements.map((r) => ({ ...r, type: "Non-Functional", subtype })),
  );

  const requirements = [...funcReqs, ...nfReqs].sort((a, b) => a.id - b.id);

  const nfrSubtypeCounts = Object.entries(nfSubtypes)
    .map(([label, { requirements: reqs = [] }]) => ({
      label,
      count: reqs.length,
    }))
    .sort((a, b) => b.count - a.count);

  const usm = report.user_story_metadata ?? {};
  const userStoryQuality = [
    {
      label: "Well-formed",
      rate: usm.well_formed_rate ?? 0,
      desc: "User stories follow the 'As a / I want / So that' structure.",
    },
    {
      label: "Simple",
      rate: usm.urq_simple_rate ?? 0,
      desc: "Each story describes a single user interaction.",
    },
    {
      label: "Accuracy",
      rate: usm.urq_accuracy_rate ?? 0,
      desc: "Stories accurately reflect the underlying requirement intent.",
    },
    {
      label: "Complete",
      rate: usm.urq_complete_rate ?? 0,
      desc: "All requirements have a corresponding user story.",
    },
    {
      label: "Estimatable",
      rate: usm.estimatable_rate ?? 0,
      desc: "Each story contains enough detail to support estimation.",
    },
    {
      label: "Uniform",
      rate: usm.uniform_rate ?? 0,
      desc: "Stories follow a consistent template and abstraction level.",
    },
    {
      label: "Unique",
      rate: usm.unique_rate ?? 0,
      desc: "No duplicate user stories were found.",
    },
    {
      label: "Completeness",
      rate: usm.completeness_rate ?? 0,
      desc: "Full coverage of the requirement set.",
    },
    {
      label: "Semantic uniqueness",
      rate: usm.urq_semantic_uniqueness_rate ?? 0,
      desc: "Stories are free from semantic overlap.",
    },
    {
      label: "Minimality",
      rate: usm.minimal_rate ?? 0,
      desc: "Stories are appropriately minimal without being overly granular.",
    },
    {
      label: "Atomicity",
      rate: usm.atomic_rate ?? 0,
      desc: "Stories are atomic and do not contain multiple requirements.",
    },
  ];

  return {
    convId,
    projectId,
    summary: {
      total_original: s.total_original ?? 0,
      total_atomic: s.total_atomic ?? 0,
      total_functional: s.total_functional ?? 0,
      total_non_functional: s.total_non_functional ?? 0,
      total_duplicate_pairs: s.total_duplicate_pairs ?? 0,
      total_conflict_pairs: s.total_conflict_pairs ?? 0,
      total_neutral_pairs: s.total_neutral_pairs ?? 0,
      total_user_stories: s.total_user_stories ?? 0,
    },
    requirements,
    nfrSubtypeCounts,
    quality: { userStoryQuality },
  };
}

/* ─────────────────────────────────────────────────────────────
   SUB-COMPONENTS
   ───────────────────────────────────────────────────────────── */
function SectionLabel({ children }) {
  return <div className="rr-section-label">{children}</div>;
}

function QualityMetricRow({ label, rate, desc }) {
  const p = pct(rate);
  const color = metricBarColor(p);
  return (
    <div className="rr-qm-row" title={desc}>
      <span className="rr-qm-label">{label}</span>
      <div className="rr-qm-track">
        <div
          className="rr-qm-fill"
          style={{ width: `${p}%`, background: color }}
        />
      </div>
      <span className="rr-qm-pct" style={{ color }}>
        {p}%
      </span>
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────
   SRS SECTION COMPONENT (NEW — placed above the report)
   ───────────────────────────────────────────────────────────── */
export function SRSSection({ convId, navigate }) {
  const [collapsed, setCollapsed] = useState(false);
  const dummySRS = [
    { id: 1, date: "12 Mar 2026", type: "IEEE" },
    { id: 2, date: "10 Mar 2026", type: "Agile" },
  ];

  return (
    <div className="rr-section-wrapper">
      <div className="rr-header">
        <h3 className="rr-header-title">
          Software Requirements Specification Documents
        </h3>
        <button
          onClick={() =>
            navigate(`/dashboard/${convId}`, {
              state: { openSRS: true, convId },
            })
          }
          className="evolve-section-btn"
        >
          Generate SRS
          {/* {collapsed ? "Show" : "Hide"} */}
        </button>
      </div>

      {/* {!collapsed && (
        // <div className="rr-section">
        //    <div
        //         className="rr-card"
        //         style={{
        //           display: "flex",
        //           justifyContent: "space-between",
        //           alignItems: "center",
        //           marginBottom: "14px",
        //         }}
        //       >
        //         <p style={{ margin: 0 }}>
        //           Generate and edit the SRS document for this project
        //         </p>

        //         <button
        //           className="evolve-section-btn"
        //           onClick={() => navigate(`/dashboard/${convId}`, {
        //         state: { openSRS: true, convId },
        //       })}
        //         >
        //           Generate SRS 
        //         </button>
        //       </div>
        //   {/* <div className="srs-generate-row">
        //     <button
        //       type="button"
        //       className="srs-generate-btn"
        //       onClick={() => navigate(`/dashboard/${convId}`, {
        //         state: { openSRS: true, convId },
        //       })}
        //     >
        //       + Generate SRS
        //     </button>
        //   </div> /}

        //   {/* {dummySRS.map((srs) => (
        //     <div key={srs.id} className="rr-table-row">
        //       <span className="rr-td-id">{srs.date}</span>
        //       <span className="rr-td-text">{srs.type}</span>
        //       <button
        //         className="srs-view-btn"
        //         onClick={() => navigate(`/dashboard/${convId}`, {
        //           state: { openSRS: true, convId, showTemplateSelection: false },
        //         })}
        //       >
        //         View
        //       </button>
        //     </div>
        //   ))} /}
        // </div>
      )} */}
    </div>
  );
}

/* ─────────────────────────────────────────────────────────────
   MAIN COMPONENT
   ───────────────────────────────────────────────────────────── */
export function Report({ report, isLoading = false }) {
  const navigate = useNavigate();
  
  // ✅ OPTIMIZATION: Show skeleton while loading
  if (isLoading) {
    return <ReportSkeleton />;
  }
  
  if (!report) {
    return;
  }
  const data = useMemo(() => adaptReport(report), [report]);
  const {
    convId,
    projectId,
    summary,
    requirements,
    nfrSubtypeCounts,
    quality,
  } = data;

  const [showRequirements, setShowRequirements] = useState(true);
  const [filter, setFilter] = useState("All");
  const [search, setSearch] = useState("");
  const [showQuality, setShowQuality] = useState(true);
  // NEW: full report collapse state
  const [reportCollapsed, setReportCollapsed] = useState(false);

  const filteredReqs = useMemo(() => {
    const q = search.toLowerCase();
    return requirements.filter((r) => {
      const typeOk = filter === "All" || r.type === filter;
      const searchOk =
        !q || r.text.toLowerCase().includes(q) || String(r.id).includes(q);
      return typeOk && searchOk;
    });
  }, [requirements, filter, search]);

  const allMetrics = quality.userStoryQuality;
  const avgAll = avgPct(allMetrics);
  const avgUs = avgPct(allMetrics);
  const perfectCount = allMetrics.filter((m) => m.rate === 1).length;

  const fPct_n = Math.round(
    (summary.total_functional / summary.total_original) * 100,
  );
  const nfPct_n = Math.round(
    (summary.total_non_functional / summary.total_original) * 100,
  );
  const atomicRate = Math.round(
    (summary.total_atomic / summary.total_original) * 100,
  );
  const atomicDiff = summary.total_atomic - summary.total_original;

  const today = new Date().toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  return (
    <div className="rr">
      {/* ══ REQUIREMENT ANALYSIS REPORT — collapsible wrapper ══ */}
      <div className="rr-section-wrapper">
        <div className="rr-section-toggle">
          <h3 className="rr-header-title">Requirement Analysis Report</h3>
          <button
            className="rr-toggle-btn"
            onClick={() => setReportCollapsed((v) => !v)}
          >
            {reportCollapsed ? "Show" : "Hide"}
          </button>
        </div>
        <div
          className="rr-section-divider"
          style={{
            width: "100%",
            height: "1px",
            backgroundColor: "#e5e7eb", // same gray as in SRS section
            margin: "1.2rem 0",
          }}
        />

        {!reportCollapsed && (
          <>
            {/* ══ SUMMARY (includes Requirement Decomposition) ══ */}
            <section className="rr-section">
              <SectionLabel>Summary</SectionLabel>

              <div className="rr-kpi-row">
                <div className="rr-kpi">
                  <div className="rr-kpi-val">{summary.total_atomic}</div>
                  <div className="rr-kpi-label">Final requirement count</div>
                </div>
                <div className="rr-kpi">
                  <div
                    className="rr-kpi-val"
                    style={{ color: "rgb(0,168,151)" }}
                  >
                    {summary.total_functional}
                  </div>
                  <div className="rr-kpi-label">Functional</div>
                  <div className="rr-kpi-sub">{fPct_n}% of total</div>
                </div>
                <div className="rr-kpi">
                  <div
                    className="rr-kpi-val"
                    style={{ color: "rgb(17,79,212)" }}
                  >
                    {summary.total_non_functional}
                  </div>
                  <div className="rr-kpi-label">Non-functional</div>
                  <div className="rr-kpi-sub">{nfPct_n}% of total</div>
                </div>
                <div className="rr-kpi">
                  <div className="rr-kpi-val">{summary.total_user_stories}</div>
                  <div className="rr-kpi-label">User stories generated</div>
                  <div className="rr-kpi-sub">1:1 coverage</div>
                </div>
              </div>

              <div className="rr-two-col">
                {/* Classification card */}
                <div className="rr-card">
                  <p className="rr-card-title">Classification</p>

                  <div className="rr-bar-row">
                    <span className="rr-bar-label">Functional</span>
                    <div className="rr-bar-track">
                      <div
                        className="rr-bar-fill"
                        style={{
                          width: `${fPct_n}%`,
                          background: "rgb(0,168,151)",
                        }}
                      />
                    </div>
                    <span
                      className="rr-bar-val"
                      style={{ color: "rgb(0,168,151)" }}
                    >
                      {summary.total_functional}
                    </span>
                  </div>

                  <div className="rr-bar-row">
                    <span className="rr-bar-label">Non-functional</span>
                    <div className="rr-bar-track">
                      <div
                        className="rr-bar-fill"
                        style={{
                          width: `${nfPct_n}%`,
                          background: "rgb(17,79,212)",
                        }}
                      />
                    </div>
                    <span
                      className="rr-bar-val"
                      style={{ color: "rgb(17,79,212)" }}
                    >
                      {summary.total_non_functional}
                    </span>
                  </div>

                  {nfrSubtypeCounts.length > 0 && (
                    <>
                      <p className="rr-chips-label">NFR subtypes</p>
                      <div className="rr-chips">
                        {nfrSubtypeCounts.map(({ label, count }) => {
                          const c = nfrColor(label);
                          return (
                            <span
                              key={label}
                              className="rr-chip"
                              style={{
                                background: c.bg,
                                color: c.text,
                                borderColor: c.border,
                              }}
                            >
                              {label} · {count}
                            </span>
                          );
                        })}
                      </div>
                    </>
                  )}
                </div>

                {/* Pair analysis card */}
                <div className="rr-card">
                  <p className="rr-card-title">Pair analysis</p>
                  <div className="rr-pair-row">
                    <div
                      className="rr-pair-card"
                      style={{ background: "#e6f1fb", borderColor: "#b5d4f4" }}
                    >
                      <div className="rr-pair-val" style={{ color: "#0c447c" }}>
                        {summary.total_duplicate_pairs}
                      </div>
                      <div
                        className="rr-pair-label"
                        style={{ color: "#185fa5" }}
                      >
                        Duplicate pairs
                      </div>
                      <div className="rr-pair-note">overlap flagged</div>
                      <div className="view-pair-div">
                        <button
                          className="view-pair-btn"
                          onClick={() =>
                            navigate(`/project/${convId}/requirements`, {
                              state: { myString: "Duplicate" },
                            })
                          }
                        >
                          View
                        </button>
                      </div>
                    </div>
                    <div
                      className="rr-pair-card"
                      style={{ background: "#e1f5ee", borderColor: "#9fe1cb" }}
                    >
                      <div className="rr-pair-val" style={{ color: "#085041" }}>
                        {summary.total_conflict_pairs}
                      </div>
                      <div
                        className="rr-pair-label"
                        style={{ color: "#0f6e56" }}
                      >
                        Conflict Pairs
                      </div>
                      <div className="rr-pair-note">
                        {summary.total_conflict_pairs === 0
                          ? "none detected"
                          : "require review"}
                      </div>
                      <div className="view-pair-div">
                        <button
                          className="view-pair-btn"
                          onClick={() =>
                            navigate(`/project/${convId}/requirements`, {
                              state: { myString: "Conflict" },
                            })
                          }
                        >
                          View
                        </button>
                      </div>
                    </div>
                    <div
                      className="rr-pair-card"
                      style={{
                        background: "rgba(243,244,246,0.5)",
                        borderColor: "rgb(229,231,235)",
                      }}
                    >
                      <div className="rr-pair-val">
                        {summary.total_neutral_pairs}
                      </div>
                      <div
                        className="rr-pair-label"
                        style={{ color: "rgb(101,117,139)" }}
                      >
                        Neutral pairs
                      </div>
                      <div className="rr-pair-note">no action needed</div>
                      <button
                        className="view-pair-btn"
                        onClick={() =>
                          navigate(`/project/${convId}/requirements`, {
                            state: { myString: "Neutral" },
                          })
                        }
                      >
                        View
                      </button>
                    </div>
                  </div>
                </div>

                {/* CDN Requirements Comparison card */}
                <div className="rr-card">
                  <p className="rr-card-title">CDN Requirements Comparison</p>
                  <p
                    style={{
                      fontSize: "0.9rem",
                      color: "var(--grey-dark)",
                      margin: "0 0 1rem 0",
                      lineHeight: "1.5",
                    }}
                  >
                    Compare original CDN extracted requirements with refined requirements.
                    See which requirements were kept during refinement.
                  </p>
                  <button
                    className="evolve-section-btn"
                    onClick={() =>
                      navigate(`/project/${convId}/cdn-comparison`, {
                        state: { convId },
                      })
                    }
                    style={{ width: "100%" }}
                  >
                    View Comparison
                  </button>
                </div>
              </div>

              {/* ── Requirement Decomposition (moved from its own section) ── */}
              <h4
                style={{
                  margin: "1.25rem 0 0.75rem",
                  fontWeight: 600,
                  fontSize: "0.9rem",
                }}
              >
                Requirement Decomposition
              </h4>
              <div className="rr-atomic">
                <div className="rr-atomic-divider" />
                <div className="rr-atomic-body">
                  <p>
                    Requirements were decomposed into atomic statements — each
                    expressing exactly one capability or constraint.
                  </p>
                  <div className="rr-atomic-meta">
                    {[
                      { val: summary.total_original, label: "Original" },
                      { val: summary.total_atomic, label: "Atomic output" },
                      {
                        val: atomicDiff === 0 ? "None" : atomicDiff,
                        label: "Difference",
                      },
                    ].map((s) => (
                      <div key={s.label} className="rr-atomic-stat">
                        <span className="rr-atomic-stat-val">{s.val}</span>
                        <span className="rr-atomic-stat-label">{s.label}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </section>

            {/* ══ REQUIREMENTS LIST ══ */}
            <section className="rr-section">
              <div className="rr-section-toggle">
                <SectionLabel>Requirements</SectionLabel>

                <button
                  className="rr-toggle-btn"
                  onClick={() => setShowRequirements((v) => !v)}
                >
                  {showRequirements ? "Hide" : "Show"}
                </button>
              </div>

              {showRequirements && (
                <>
                  <div className="rr-controls">
                    <input
                      className="rr-search"
                      type="text"
                      placeholder="Search by keyword or ID…"
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                    />

                    {["All", "Functional", "Non-Functional"].map((f) => (
                      <button
                        key={f}
                        className={`fr-nfr-btns rr-filter-btn${filter === f ? " rr-filter-btn--active" : ""}`}
                        onClick={() => setFilter(f)}
                      >
                        {f === "Non-Functional" ? "Non-functional" : f}
                      </button>
                    ))}
                  </div>

                  <p className="rr-req-count">
                    Showing <strong>{filteredReqs.length}</strong> of{" "}
                    {requirements.length} requirements
                  </p>

                  <div className="rr-table">
                    <div className="rr-table-head">
                      <span className="rr-th">#</span>
                      <span className="rr-th">Requirement</span>
                      <span className="rr-th">Type</span>
                      <span className="rr-th">Category</span>
                    </div>

                    {filteredReqs.map((req) => {
                      const tb = typeBadge(req.type);
                      const nc = nfrColor(req.subtype);

                      return (
                        <div key={req.id} className="rr-table-row">
                          <span className="rr-td-id">
                            {String(req.id).padStart(2, "0")}
                          </span>
                          <span className="rr-td-text">{req.text}</span>

                          <span>
                            <span
                              className="rr-badge"
                              style={{ background: tb.bg, color: tb.text }}
                            >
                              {req.type === "Functional"
                                ? "Functional"
                                : "Non-func."}
                            </span>
                          </span>

                          <span>
                            <span
                              className="rr-badge"
                              style={{
                                background: nc.bg,
                                color: nc.text,
                                borderColor: nc.border,
                              }}
                            >
                              {req.subtype}
                            </span>
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </>
              )}
            </section>

            {/* ══ USER STORY & ASSESSMENT (merged) ══ */}
            <section className="rr-section">
              <div className="rr-section-toggle">
                <SectionLabel>User Story &amp; Assessment</SectionLabel>
                <button
                  className="rr-toggle-btn"
                  onClick={() => setShowQuality((v) => !v)}
                >
                  {showQuality ? "Hide" : "Show"}
                </button>
              </div>

              {/* User Story card */}
              <div
                className="rr-card"
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "14px",
                }}
              >
                <p style={{ margin: 0 }}>
                  View and manage generated user stories for this project.
                </p>

                <button
                  className="evolve-section-btn"
                  onClick={() =>
                    (window.location.href = `/project/${convId}/user-stories`)
                  }
                >
                  User Stories
                </button>
              </div>

              {/* Quality Assessment */}
              {showQuality && (
                <>
                  {/* Quality KPIs */}
                  <div className="rr-quality-kpis">
                    <div className="rr-kpi">
                      <div
                        className="rr-kpi-val"
                        style={{ color: "rgb(0,168,151)" }}
                      >
                        {avgAll}%
                      </div>
                      <div className="rr-kpi-label">Overall quality</div>
                      <div className="rr-kpi-sub">
                        avg across all dimensions
                      </div>
                    </div>
                    <div className="rr-kpi">
                      <div className="rr-kpi-val">{avgUs}%</div>
                      <div className="rr-kpi-label">User story quality</div>
                      <div className="rr-kpi-sub">URQ framework checks</div>
                    </div>
                    <div className="rr-kpi">
                      <div className="rr-kpi-val">
                        {perfectCount}/{allMetrics.length}
                      </div>
                      <div className="rr-kpi-label">Perfect scores</div>
                    </div>
                  </div>

                  {/* Metric panels */}
                  <div className="rr-quality-two">
                    <div className="rr-card">
                      <p className="rr-quality-group-label">
                        User story quality (URQ)
                      </p>
                      <p className="rr-quality-desc">
                        Evaluates the {summary.total_user_stories} generated
                        user stories against the URQ framework for structure,
                        simplicity, traceability, and completeness of coverage.
                      </p>
                      {quality.userStoryQuality.map((m) => (
                        <QualityMetricRow key={m.label} {...m} />
                      ))}
                    </div>
                  </div>

                  {/* Insight callouts */}
                  <div className="rr-insight-row">
                    <div
                      className="rr-insight"
                      style={{ background: "#e1f5ee", borderColor: "#9fe1cb" }}
                    >
                      <p
                        className="rr-insight-label"
                        style={{ color: "#0f6e56" }}
                      >
                        Conflict-free
                      </p>
                      <p
                        className="rr-insight-body"
                        style={{ color: "#085041" }}
                      >
                        {summary.total_conflict_pairs === 0
                          ? `All ${summary.total_original} requirements passed conflict detection. No contradictions were found.`
                          : `${summary.total_conflict_pairs} conflict pair(s) detected and require resolution.`}
                      </p>
                    </div>
                    <div
                      className="rr-insight"
                      style={{ background: "#e6f1fb", borderColor: "#b5d4f4" }}
                    >
                      <p
                        className="rr-insight-label"
                        style={{ color: "#185fa5" }}
                      >
                        Semantic uniqueness
                      </p>
                      <p
                        className="rr-insight-body"
                        style={{ color: "#0c447c" }}
                      >
                        {pct(
                          report.user_story_metadata
                            ?.urq_semantic_uniqueness_rate ?? 1,
                        )}
                        % semantic uniqueness — minor overlap may exist in
                        role-variant requirements.
                      </p>
                    </div>
                    <div
                      className="rr-insight"
                      style={{
                        background: "rgba(243,244,246,0.4)",
                        borderColor: "rgb(229,231,235)",
                      }}
                    >
                      <p
                        className="rr-insight-label"
                        style={{ color: "rgb(101,117,139)" }}
                      >
                        Minimality
                      </p>
                      <p className="rr-insight-body">
                        {pct(report.user_story_metadata?.minimal_rate ?? 1)}%
                        minimality rate —
                        {(report.user_story_metadata?.minimal_rate ?? 1) < 1
                          ? " a few requirements contain composite statements worth splitting further."
                          : " all requirements are appropriately minimal."}
                      </p>
                    </div>
                  </div>
                </>
              )}
            </section>
          </>
        )}
      </div>
    </div>
  );
}
