/**
 * Utility function to download user story PDFs from the backend
 * and display notifications to the user.
 */

/**
 * Download user story PDF and trigger browser download
 * 
 * @param {string} convId - Conversation ID (optional, will use most recent if not provided)
 * @param {string} storyId - Optional specific story ID to download (single story mode)
 * @param {function} onSuccess - Optional callback when download succeeds
 * @param {function} onError - Optional callback when download fails
 * 
 * @example
 * // Download all user stories for a conversation
 * downloadUserStoryPDF('conv-12345');
 * 
 * // Download a specific user story
 * downloadUserStoryPDF('conv-12345', 'R1-US1');
 * 
 * // With callbacks
 * downloadUserStoryPDF('conv-12345', null, 
 *   () => console.log('Downloaded!'),
 *   (error) => console.error('Error:', error)
 * );
 */
export const downloadUserStoryPDF = async (
  convId = null,
  storyId = null,
  onSuccess = null,
  onError = null
) => {
  try {
    // Build URL with query parameters
    const baseUrl = 'http://localhost:8000/api/user_story/download';
    const params = new URLSearchParams();
    
    if (convId) {
      params.append('conv_id', convId);
    }
    
    if (storyId) {
      params.append('story_id', storyId);
    }
    
    const url = params.toString() 
      ? `${baseUrl}?${params.toString()}` 
      : baseUrl;
    
    // Fetch PDF from backend
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Accept': 'application/pdf',
      },
    });
    
    // Check if request was successful
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({
        detail: `HTTP error! status: ${response.status}`
      }));
      throw new Error(errorData.detail || `Failed to download PDF: ${response.status}`);
    }
    
    // Get filename from Content-Disposition header or use default
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = 'user_stories.pdf';
    
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i);
      if (filenameMatch) {
        filename = filenameMatch[1];
      }
    }
    
    // Convert response to blob
    const blob = await response.blob();
    
    // Create download link and trigger download
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    
    // Cleanup
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
    
    // Call success callback if provided
    if (onSuccess) {
      onSuccess(filename);
    }
    
    return { success: true, filename };
    
  } catch (error) {
    console.error('Error downloading user story PDF:', error);
    
    // Show error notification
    showNotification(
      `Failed to download user story PDF: ${error.message}`,
      'error'
    );
    
    // Call error callback if provided
    if (onError) {
      onError(error);
    }
    
    throw error;
  }
};

/**
 * Show notification to user
 * 
 * @param {string} message - Notification message
 * @param {string} type - Notification type: 'success', 'error', 'info'
 */
export const showNotification = (message, type = 'info') => {
  // Try to use browser's native notification API if available
  if ('Notification' in window && Notification.permission === 'granted') {
    new Notification('MARS User Stories', {
      body: message,
      icon: '/favicon.ico', // Adjust path as needed
    });
  }
  
  // Also show alert for immediate feedback
  // You can replace this with a toast notification library if preferred
  if (type === 'success') {
    alert(`✅ ${message}`);
  } else if (type === 'error') {
    alert(`❌ ${message}`);
  } else {
    alert(`ℹ️ ${message}`);
  }
};

/**
 * Request notification permission from user
 * Call this once when the app loads to enable desktop notifications
 */
export const requestNotificationPermission = async () => {
  if ('Notification' in window && Notification.permission === 'default') {
    await Notification.requestPermission();
  }
};

// Note: For React hooks, import React and useState in your component file:
// import React, { useState } from 'react';

