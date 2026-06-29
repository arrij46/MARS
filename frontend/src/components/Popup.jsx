import React, { useState } from "react";
import "../style/Popup.css";

export default function Popup({ onFileSelect, onClose }) {
  const [file, setFile] = useState(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (file) onFileSelect(file);
  };

  return (
    <div className="popup-overlay">
      <div className="popup-content">
        <h2>Upload Requirements File</h2>
     <p>
  Please upload a requirements document that contains only a list of requirement statements. 
  Each statement should be written on a new line and may be either numbered or unnumbered.
  
  Avoid including any additional text, headings, or formatting to ensure accurate analysis.
  
  Supported file formats are: <strong>.txt, .doc, or .docx</strong>.
</p>

        <input
          type="file"
          accept=".txt,.docx,.pdf"
          onChange={(e) => setFile(e.target.files[0])}
          className="popup-file-input"
        />

        {file && (
          <p className="selected-file">
            Selected File: <strong>{file.name}</strong>
          </p>
        )}

        <div className="popup-actions">
          <button
            className="popup-btn upload"
            onClick={handleSubmit}
            disabled={!file}
          >
            Upload & Analyze
          </button>
          <button className="popup-btn cancel" onClick={onClose}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
