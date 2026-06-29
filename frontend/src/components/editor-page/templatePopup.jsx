import React, { useState , useEffect} from "react";
import { useNavigate, useParams } from "react-router-dom";
import "../../style/TemplatePopup.css";
import {
  srsTemplates,
  fontSizeGrid,
  defaultFontSizes,
  fontSizeOptions,
  fontOptions,
} from "../editor-page/srsFormats";
import { authFetch } from "../../utils/api";

const tabKeys = Object.keys(srsTemplates);

export default function TemplatePopup({ onClose }) {
  const navigate = useNavigate();
    const { projectId } = useParams();

  const [mode, setMode] = useState("existing"); // "existing" | "create"
  const [existingTemplates, setExistingTemplates] = useState([]);
  const [selectedExisting, setSelectedExisting] = useState(null);
  const [loadingTemplates, setLoadingTemplates] = useState(false);

  // ── Create new template states ──
  const [templateName, setTemplateName] = useState("");
  const [activeTab, setActiveTab] = useState(tabKeys[0]);
  const [expanded, setExpanded] = useState({});
  const [checkedSections, setCheckedSections] = useState({});
  const [checkedSubs, setCheckedSubs] = useState({});
  const [fontStyle, setFontStyle] = useState("Inter");
  const [fontSizes, setFontSizes] = useState(defaultFontSizes);
  const sections = srsTemplates[activeTab];

  // ── Fetch existing templates on mount ──
  useEffect(() => {
    setLoadingTemplates(true);
    authFetch("/api/templates/getUserTemplates")
      .then((res) => res.json())
      .then((data) => {
        setExistingTemplates(data);
        // if no templates exist, default to create mode
        if (data.length === 0) setMode("create");
      })
      .catch((err) => {
        console.error("Failed to fetch templates:", err);
        setMode("create");
      })
      .finally(() => setLoadingTemplates(false));
  }, []);

  const handleClose = () => {
    setTemplateName("");
    setActiveTab(tabKeys[0]);
    setExpanded({});
    setCheckedSections({});
    setCheckedSubs({});
    setFontStyle("Inter");
    setFontSizes(defaultFontSizes);
    setSelectedExisting(null);
    onClose();
  };

  // ── Use existing template ──
const handleUseExisting = () => {
  if (!selectedExisting) { alert("Please select a template."); return; }

  authFetch(`/api/templates/linkToProject`, {
    method: "POST",
    body: JSON.stringify({ template_id: selectedExisting.id, project_id: projectId })
  })
    .then((res) => res.json())
    .then(() => authFetch(`/api/templates/templateReady/${projectId}`, { method: "POST" }))
    .then(() => {
      navigate(`/project/${projectId}/editor`);
      handleClose();
    })
    .catch((err) => { console.error(err); alert("Error."); });
};

  // ── Create new template ──
  const createTemplate = () => {
    if (templateName.trim() === "") {
      alert("Please enter a template name.");
      return;
    }

    const hasAnySelected = srsTemplates[activeTab].some((s) =>
      s.hasChildren
        ? s.sub.some((x) => checkedSubs[`${s.id}::${x}`])
        : !!checkedSections[s.id]
    );

    if (!hasAnySelected) {
      alert("Please select at least one section.");
      return;
    }

    const Template = {
      name: templateName,
      format: activeTab,
      sections: srsTemplates[activeTab]
        .filter((s) =>
          s.hasChildren
            ? s.sub.some((x) => checkedSubs[`${s.id}::${x}`])
            : !!checkedSections[s.id]
        )
        .map((s) => ({
          id: s.id,
          heading: s.heading,
          sub: s.hasChildren
            ? s.sub
                .filter((x) => !!checkedSubs[`${s.id}::${x}`])
                .map((x) => ({ id: `${s.id}::${x}`, heading: x }))
            : [],
        })),
      fontStyle,
      fontSizes,
    };
    let data= null;
    authFetch("/api/templates/saveTemplate", {
      method: "POST",
      body: JSON.stringify(Template),
    })
      .then(async (res) => {
        if (res.status === 409) {
          data = await res.json();
          alert(`⚠️ ${data.detail}`);
          return null;
        }
        if (!res.ok) throw new Error("Failed to save template");
        return res.json();
      })
      .then((data) => {
        if (!data) return;
         // Signal document agent that template is ready
        return authFetch(`/api/templates/templateReady/${projectId}`, { method: "POST" });
      })
      .then(() => {
        console.log("Template saved:", data);
         console.log("projectId:", projectId); 
        navigate(`/project/${projectId}/editor`);
        handleClose();
      })
      .catch((err) => {
        console.error(err);
        alert("Error saving template. Please try again.");
      });
  };

  // ── Reuse existing helpers ──
  const handleTabChange = (tab) => { setActiveTab(tab); setExpanded({}); setCheckedSections({}); setCheckedSubs({}); };
  const toggleExpand = (id) => setExpanded((p) => ({ ...p, [id]: !p[id] }));
  const subKey = (id, sub) => `${id}::${sub}`;
  const toggleSub = (id, sub) => setCheckedSubs((p) => ({ ...p, [subKey(id, sub)]: !p[subKey(id, sub)] }));
  const toggleLeaf = (id) => setCheckedSections((p) => ({ ...p, [id]: !p[id] }));
  const allSubsChecked = (s) => s.sub.length > 0 && s.sub.every((x) => checkedSubs[subKey(s.id, x)]);
  const someSubsChecked = (s) => s.sub.some((x) => checkedSubs[subKey(s.id, x)]);
  const toggleSelectAll = (s) => {
    const check = !allSubsChecked(s);
    setCheckedSubs((p) => { const n = { ...p }; s.sub.forEach((x) => { n[subKey(s.id, x)] = check; }); return n; });
  };
  const isSectionChecked = (s) => s.hasChildren ? allSubsChecked(s) : !!checkedSections[s.id];
  const isSectionPartial = (s) => s.hasChildren ? someSubsChecked(s) && !allSubsChecked(s) : false;
  const allRootChecked = sections.every((s) => isSectionChecked(s));
  const someRootChecked = sections.some((s) => isSectionChecked(s) || isSectionPartial(s));
  const toggleRootSelectAll = () => {
    const check = !allRootChecked;
    const newSubs = { ...checkedSubs };
    const newLeafs = { ...checkedSections };
    sections.forEach((s) => {
      if (s.hasChildren) s.sub.forEach((x) => { newSubs[subKey(s.id, x)] = check; });
      else newLeafs[s.id] = check;
    });
    setCheckedSubs(newSubs);
    setCheckedSections(newLeafs);
  };
  const updateFontSize = (label, v) => setFontSizes((p) => ({ ...p, [label]: v }));

  return (
    <>
      <div className="tp-overlay" onClick={(e) => e.target === e.currentTarget && handleClose()}>
        <div className="tp-modal">

          {/* Header */}
          <div className="tp-header">
            <button className="tp-back-btn" onClick={handleClose}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.3">
                <polyline points="15 18 9 12 15 6" />
              </svg>
            </button>
            <h2 className="tp-title">SRS Template</h2>
            <button className="tp-close-btn" onClick={handleClose}>✕</button>
          </div>

          {/* Mode Tabs */}
          <div className="tp-tabs" style={{ padding: "0 1.5rem" }}>
            <button
              className={`tp-tab${mode === "existing" ? " active" : ""}`}
              onClick={() => setMode("existing")}
            >
              Use Existing
            </button>
            <button
              className={`tp-tab${mode === "create" ? " active" : ""}`}
              onClick={() => setMode("create")}
            >
              Create New
            </button>
          </div>

          {/* Body */}
          <div className="tp-body">

            {/* ── Existing Templates Mode ── */}
            {mode === "existing" && (
              <div className="tp-field-group">
                {loadingTemplates ? (
                  <p className="tp-sublabel">Loading templates...</p>
                ) : existingTemplates.length === 0 ? (
                  <p className="tp-sublabel">No saved templates found. Create one first.</p>
                ) : (
                  <>
                    <div className="tp-label">Your Saved Templates</div>
                    <div className="tp-sublabel">Select a template to use for SRS generation.</div>
                    <div className="tp-sections-list">
                      {existingTemplates.map((t) => (
                        <div
                          key={t.id}
                          className={`tp-section-row ${selectedExisting?.id === t.id ? "selected" : ""}`}
                          onClick={() => setSelectedExisting(t)}
                          style={{ cursor: "pointer", padding: "0.6rem 0.8rem" }}
                        >
                          <input
                            type="radio"
                            className="tp-checkbox"
                            checked={selectedExisting?.id === t.id}
                            onChange={() => setSelectedExisting(t)}
                          />
                          <span className="tp-section-label">
                            {t.name}
                            <span className="tp-sublabel" style={{ marginLeft: "0.5rem" }}>
                              ({t.format})
                            </span>
                          </span>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}

            {/* ── Create New Template Mode ── */}
            {mode === "create" && (
              <>
                {/* Template Name */}
                <div className="tp-field-group">
                  <label className="tp-label">
                    Template Name <span className="tp-required">*</span>
                  </label>
                  <input
                    className="tp-input"
                    placeholder="e.g. My SRS Template"
                    value={templateName}
                    onChange={(e) => setTemplateName(e.target.value)}
                  />
                </div>

                {/* Format tabs */}
                <div className="tp-field-group">
                  <div className="tp-label">Format <span className="tp-required">*</span></div>
                  <div className="tp-sublabel">Select the format and headings for your SRS.</div>
                  <div className="tp-tabs">
                    {tabKeys.map((tab) => (
                      <button
                        key={tab}
                        className={`tp-tab${activeTab === tab ? " active" : ""}`}
                        onClick={() => handleTabChange(tab)}
                      >
                        {tab}
                      </button>
                    ))}
                  </div>

                  {/* Section rows */}
                  <div className="tp-sections-list">
                    <div className="tp-section-row is-select-all" onClick={toggleRootSelectAll}>
                      <input
                        type="checkbox"
                        className={`tp-checkbox${someRootChecked && !allRootChecked ? " indeterminate" : ""}`}
                        checked={allRootChecked}
                        onChange={toggleRootSelectAll}
                        onClick={(e) => e.stopPropagation()}
                      />
                      <span className="tp-select-all-label">Select all</span>
                    </div>

                    {sections.map((section) => {
                      const isExpanded = !!expanded[section.id];
                      const all = section.hasChildren ? allSubsChecked(section) : !!checkedSections[section.id];
                      const partial = section.hasChildren ? someSubsChecked(section) && !allSubsChecked(section) : false;
                      return (
                        <React.Fragment key={section.id}>
                          <div className="tp-section-row">
                            {section.hasChildren ? (
                              <button className={`tp-chevron-btn${isExpanded ? " expanded" : ""}`} onClick={() => toggleExpand(section.id)}>
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                  <polyline points="9 18 15 12 9 6" />
                                </svg>
                              </button>
                            ) : (
                              <span className="tp-chevron-spacer" />
                            )}
                            <input
                              type="checkbox"
                              className={`tp-checkbox${partial ? " indeterminate" : ""}`}
                              checked={all}
                              onChange={() => section.hasChildren ? toggleSelectAll(section) : toggleLeaf(section.id)}
                            />
                            <span
                              className="tp-section-label"
                              style={{ cursor: "pointer", fontWeight: all || partial ? 600 : 400 }}
                              onClick={() => section.hasChildren ? toggleExpand(section.id) : toggleLeaf(section.id)}
                            >
                              {section.heading}
                            </span>
                          </div>

                          {isExpanded && section.hasChildren && (
                            <>
                              <div className="tp-section-row is-select-all" onClick={() => toggleSelectAll(section)}>
                                <input
                                  type="checkbox"
                                  className={`tp-checkbox${partial ? " indeterminate" : ""}`}
                                  checked={allSubsChecked(section)}
                                  onChange={() => toggleSelectAll(section)}
                                  onClick={(e) => e.stopPropagation()}
                                />
                                <span className="tp-select-all-label">Select all</span>
                              </div>
                              {section.sub.map((sub) => (
                                <div key={sub} className="tp-section-row is-sub">
                                  <span className="tp-chevron-spacer" />
                                  <input
                                    type="checkbox"
                                    className="tp-checkbox"
                                    checked={!!checkedSubs[subKey(section.id, sub)]}
                                    onChange={() => toggleSub(section.id, sub)}
                                  />
                                  <span className="tp-section-label">{sub}</span>
                                </div>
                              ))}
                            </>
                          )}
                        </React.Fragment>
                      );
                    })}
                  </div>
                </div>

                {/* Font Style */}
                <div className="tp-field-group">
                  <div className="tp-label">Font Style</div>
                  <select className="tp-select" value={fontStyle} onChange={(e) => setFontStyle(e.target.value)}>
                    {fontOptions.map((f) => <option key={f} value={f}>{f}</option>)}
                  </select>
                </div>

                {/* Font Sizes */}
                <div className="tp-field-group">
                  <div className="tp-label">Font Sizes</div>
                  <div className="tp-sublabel">Set sizes for each heading level and paragraphs</div>
                  <div className="tp-font-grid">
                    {fontSizeGrid.map((row) =>
                      row.map((label) => (
                        <div className="tp-font-row" key={label}>
                          <span className="tp-font-row-label">{label}</span>
                          <select
                            className="tp-size-select"
                            value={fontSizes[label]}
                            onChange={(e) => updateFontSize(label, Number(e.target.value))}
                          >
                            {fontSizeOptions.map((s) => <option key={s} value={s}>{s}pt</option>)}
                          </select>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Footer */}
          <div className="tp-footer">
            {mode === "existing" ? (
              <button
                className="tp-create-btn"
                onClick={handleUseExisting}
                disabled={!selectedExisting}
              >
                Use Selected Template
              </button>
            ) : (
              <button className="tp-create-btn" onClick={createTemplate}>
                Create Template
              </button>
            )}
          </div>

        </div>
      </div>
    </>
  );
}
