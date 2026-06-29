import React, { createContext, useState, useCallback } from 'react';

export const ReportContext = createContext();

/**
 * ReportProvider: Global context for caching and managing report state
 * 
 * Provides:
 * - reportCache: Cached report data by convId
 * - reportLoading: Loading states for reports
 * - reportError: Error states for reports
 * - Helper methods: cacheReport, setLoading, setError, getReport
 */
export function ReportProvider({ children }) {
  const [reportCache, setReportCache] = useState({});
  const [reportLoading, setReportLoading] = useState({});
  const [reportError, setReportError] = useState({});

  const cacheReport = useCallback((convId, reportData) => {
    setReportCache(prev => ({ ...prev, [convId]: reportData }));
    // Clear error when report is cached
    setReportError(prev => {
      const updated = { ...prev };
      delete updated[convId];
      return updated;
    });
  }, []);

  const setLoadingState = useCallback((convId, isLoading) => {
    setReportLoading(prev => ({ ...prev, [convId]: isLoading }));
  }, []);

  const setErrorState = useCallback((convId, error) => {
    setReportError(prev => ({ ...prev, [convId]: error }));
  }, []);

  const getReport = useCallback((convId) => {
    return reportCache[convId] || null;
  }, [reportCache]);

  const isReportLoading = useCallback((convId) => {
    return reportLoading[convId] || false;
  }, [reportLoading]);

  const hasReportError = useCallback((convId) => {
    return reportError[convId] || null;
  }, [reportError]);

  const clearReportCache = useCallback((convId) => {
    setReportCache(prev => {
      const updated = { ...prev };
      delete updated[convId];
      return updated;
    });
    setReportLoading(prev => {
      const updated = { ...prev };
      delete updated[convId];
      return updated;
    });
    setReportError(prev => {
      const updated = { ...prev };
      delete updated[convId];
      return updated;
    });
  }, []);

  return (
    <ReportContext.Provider value={{
      reportCache,
      reportLoading,
      reportError,
      cacheReport,
      setLoading: setLoadingState,
      setError: setErrorState,
      getReport,
      isReportLoading,
      hasReportError,
      clearReportCache
    }}>
      {children}
    </ReportContext.Provider>
  );
}

/**
 * Hook to use ReportContext
 */
export function useReportContext() {
  const context = React.useContext(ReportContext);
  if (!context) {
    throw new Error('useReportContext must be used within ReportProvider');
  }
  return context;
}
