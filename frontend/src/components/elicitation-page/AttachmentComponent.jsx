import React, { useState } from 'react';
import '../../style/elicitation.css'; // Optional CSS file

const AttachmentComponent = ({ onFileUpload }) => {
  const [showAttachmentPopup, setShowAttachmentPopup] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);

  // Toggle the attachment popup
  const toggleAttachmentPopup = () => {
    setShowAttachmentPopup(!showAttachmentPopup);
  };

  // Close the popup
  const closeAttachmentPopup = () => {
    setShowAttachmentPopup(false);
  };

  // Trigger the hidden file input
  const triggerFileInput = () => {
    document.getElementById('hidden-file-input').click();
    closeAttachmentPopup();
  };

  // Handle file selection
  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      setSelectedFile(file);
      // Auto-upload the file
      uploadFile(file);
      // Notify parent component if needed
      if (onFileUpload) {
        onFileUpload(file);
      }
    }
  };

  // Remove the selected file
  const removeFile = () => {
    setSelectedFile(null);
    document.getElementById('hidden-file-input').value = '';
  };

  // Upload file function
  const uploadFile = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await fetch('/your-upload-endpoint', {
        method: 'POST',
        body: formData
      });
      
      if (response.ok) {
        console.log('File uploaded successfully!');
      }
    } catch (error) {
      console.error('Upload error:', error);
    }
  };

  return (
    <div className="attachment-container">
      {/* Attachment Logo/Icon */}
      <div className="attachment-logo" onClick={toggleAttachmentPopup}>
        📎
      </div>
      
      {/* Popup for file selection */}
      {showAttachmentPopup && (
        <div className="attachment-popup">
          <div className="popup-content">
            <h4>Attach File</h4>
            <p>Select a file to attach</p>
            <input
              type="file"
              id="hidden-file-input"
              onChange={handleFileSelect}
              style={{ display: 'none' }}
            />
            <button className="browse-button" onClick={triggerFileInput}>
              Browse Files
            </button>
            <button className="cancel-button" onClick={closeAttachmentPopup}>
              Cancel
            </button>
          </div>
        </div>
      )}
      
      {/* File preview area */}
      <div className="file-preview-area">
        {selectedFile && (
          <div className="file-preview">
            <span className="file-info">
              {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
            </span>
            <button className="remove-file-btn" onClick={removeFile}>
              ×
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default AttachmentComponent;