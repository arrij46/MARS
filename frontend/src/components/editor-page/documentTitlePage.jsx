import React, { useEffect, useRef } from "react";
import { authFetch } from "../../utils/api";

// ── Editable block ─────────────────────────────────────────────────────────
function EditableBlock({ defaultValue, placeholder, className, onSave }) {
  const ref = useRef(null);

  useEffect(() => {
    if (ref.current && defaultValue !== undefined && defaultValue !== null) {
      ref.current.innerHTML = String(defaultValue).replace(/\n/g, "<br/>");
    }
  }, [defaultValue]);

  const handleBlur = (e) => {
    const value = e.currentTarget.innerText.trim();
    if (!value && ref.current) {
      ref.current.innerHTML = "";
    }
    if (onSave && value) {
      onSave(value);
    }
  };

  return (
    <div
      ref={ref}
      contentEditable
      suppressContentEditableWarning
      spellCheck={false}
      data-placeholder={placeholder}
      className={`title-page-editable ${className ?? ""}`}
      onBlur={handleBlur}
    />
  );
}

// ── Component ──────────────────────────────────────────────────────────────
// titlePageData is fetched in EditorPage after SRS loads and passed as a prop
export default function IeeeTitlePage({
  projectId,
  titlePageData,          // { title, version, date, org, author } — from EditorPage
  pageHeight = 1056,
  pageMargin = 96,
  pageWidth = 816,
}) {

  // ── Save a single field back to DB ───────────────────────────────────────
  const saveField = (field, value) => {
    authFetch(`/api/titlePage/${projectId}`, {
      method: "PATCH",
      body: JSON.stringify({ [field]: value }),
    }).catch(() => {});
  };

  const W = pageWidth  - 2 * pageMargin;
  const H = pageHeight - 2 * pageMargin;

  const today = new Date().toLocaleDateString("en-US", {
    year: "numeric", month: "long", day: "numeric",
  });

  return (
    <div
      className="title-page-wrapper"
      style={{ width: `${W}px`, height: `${H}px`, margin: `${pageMargin}px` }}
    >
      <hr className="title-page-top-rule" />

      <div className="title-page-body">

        {/* Fixed heading — always the same */}
        <EditableBlock
          defaultValue="Software Requirements Specification"
          placeholder="Document Title"
          className="title-page-heading"
        />

        <EditableBlock
          defaultValue="for"
          placeholder="for"
          className="title-page-for"
        />

        {/* title — raw value from srs_json.title, no angle brackets */}
        <EditableBlock
          defaultValue={titlePageData?.title ?? "<Project>"}
          placeholder="<Project>"
          className="title-page-project"
          onSave={(val) => saveField("title", val.trim())}
        />

        {/* version — from srs_documents.version e.g. "1.0.0" */}
        <EditableBlock
          defaultValue={titlePageData ? `Version ${titlePageData.version} approved` : "Version 1.0 approved"}
          placeholder="Version 1.0 approved"
          className="title-page-meta"
          onSave={(val) => {
            const clean = val.replace(/^Version\s*/i, "").replace(/\s*approved$/i, "").trim();
            saveField("version", clean);
          }}
        />

        {/* author — looked up from users.name via projects.user_id */}
        <EditableBlock
          defaultValue={titlePageData?.author ? `Prepared by ${titlePageData.author}` : "Prepared by <author>"}
          placeholder="Prepared by <author>"
          className="title-page-meta"
        />

        {/* org — empty string from backend until user fills it in */}
        <EditableBlock
          defaultValue={titlePageData?.org || "<organization>"}
          placeholder="<organization>"
          className="title-page-meta"
          onSave={(val) => saveField("org", val.replace(/^<|>$/g, "").trim())}
        />

        {/* date — formatted string from srs_documents.created_at */}
        <EditableBlock
          defaultValue={titlePageData?.date ?? today}
          placeholder="<date created>"
          className="title-page-meta"
        />

      </div>

      <hr className="title-page-bottom-rule" />

      <div
        contentEditable
        suppressContentEditableWarning
        spellCheck={false}
        data-placeholder="Copyright notice"
        className="title-page-copyright"
        dangerouslySetInnerHTML={{
          __html: "Copyright &copy; 2026 by D-099-MARS. Permission is granted to use, modify, and distribute this document.",
        }}
      />
    </div>
  );
}