/**
 * User Story Download Button Component
 * 
 * A React component that provides a button to download user story PDFs
 * with loading states and error handling.
 * 
 * @example
 * // Basic usage
 * <UserStoryDownloadButton convId="conv-12345" />
 * 
 * // Download specific story
 * <UserStoryDownloadButton convId="conv-12345" storyId="R1-US1" />
 * 
 * // With custom styling
 * <UserStoryDownloadButton 
 *   convId="conv-12345" 
 *   className="my-custom-button"
 *   buttonText="Download PDF"
 * />
 */
import React, { useState } from 'react';
import { downloadUserStoryPDF, showNotification } from '../../utils/downloadUserStory';
import { FaDownload, FaSpinner } from 'react-icons/fa';

const UserStoryDownloadButton = ({
  convId = null,
  storyId = null,
  buttonText = 'Download User Stories PDF',
  className = '',
  onDownloadComplete = null,
  onDownloadError = null,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleDownload = async () => {
    setLoading(true);
    setError(null);

    try {
      const result = await downloadUserStoryPDF(
        convId,
        storyId,
        (filename) => {
          // Success callback
          if (onDownloadComplete) {
            onDownloadComplete(filename);
          }
        },
        (err) => {
          // Error callback
          setError(err.message);
          if (onDownloadError) {
            onDownloadError(err);
          }
        }
      );
    } catch (err) {
      setError(err.message);
      if (onDownloadError) {
        onDownloadError(err);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`user-story-download-container ${className}`}>
      <button
        onClick={handleDownload}
        disabled={loading}
        className={`download-button ${loading ? 'loading' : ''} ${error ? 'error' : ''}`}
        style={{
          padding: '10px 20px',
          fontSize: '16px',
          backgroundColor: loading ? '#ccc' : '#007bff',
          color: 'white',
          border: 'none',
          borderRadius: '5px',
          cursor: loading ? 'not-allowed' : 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}
      >
        {loading ? (
          <>
            <FaSpinner className="spinner" style={{ animation: 'spin 1s linear infinite' }} />
            Generating PDF...
          </>
        ) : (
          <>
            <FaDownload />
            {buttonText}
          </>
        )}
      </button>
      
      {error && (
        <div 
          className="error-message" 
          style={{
            color: 'red',
            marginTop: '10px',
            fontSize: '14px',
          }}
        >
          {error}
        </div>
      )}
      
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default UserStoryDownloadButton;

