import { useState, useEffect, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import "../style/CDNComparison.css";

/**
 * CDN Requirements Comparison Component
 *
 * Displays original CDN extracted requirements and compares them with
 * refined/cleaned requirements. Shows visual indicators (GREEN for kept,
 * RED for removed) for each requirement.
 */
export default function CDNComparison() {
  const { projectId: convId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filterStatus, setFilterStatus] = useState("all"); // "all", "kept", "removed"
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("number"); // "number", "status"

  // Fetch comparison data
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch(
          `http://localhost:8000/api/cdn_requirements_comparison/${convId}`
        );

        if (!response.ok) {
          throw new Error(`Failed to fetch CDN comparison data: ${response.statusText}`);
        }

        const result = await response.json();

        if (result.status === "error" || result.status === "not_found") {
          setError(result.message || "Failed to load comparison data");
          setData(null);
        } else {
          setData(result);
        }
      } catch (err) {
        console.error("[CDNComparison] Error fetching data:", err);
        setError(err.message || "An error occurred while fetching data");
        setData(null);
      } finally {
        setLoading(false);
      }
    };

    if (convId) {
      fetchData();
    } else {
      setError("No conversation ID provided");
      setLoading(false);
    }
  }, [convId]);

  // Filter and sort requirements
  const filteredAndSortedRequirements = useMemo(() => {
    if (!data || !data.requirements) return [];

    let filtered = data.requirements;

    // Apply status filter
    if (filterStatus !== "all") {
      filtered = filtered.filter((req) => req.status === filterStatus);
    }

    // Apply search filter
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (req) =>
          req.requirement.toLowerCase().includes(q) ||
          String(req.req_number).includes(q)
      );
    }

    // Apply sorting
    if (sortBy === "status") {
      filtered.sort(
        (a, b) =>
          (a.status === "removed" ? 1 : 0) - (b.status === "removed" ? 1 : 0)
      );
    } else {
      filtered.sort((a, b) => a.req_number - b.req_number);
    }

    return filtered;
  }, [data, filterStatus, searchQuery, sortBy]);

  // Calculate statistics
  const stats = useMemo(() => {
    if (!data) return { total: 0, kept: 0, removed: 0, keptPercent: 0 };

    const total = data.original_count || 0;
    const kept = data.kept_count || 0;
    const removed = data.removed_count || 0;
    const keptPercent = total > 0 ? Math.round((kept / total) * 100) : 0;

    return { total, kept, removed, keptPercent };
  }, [data]);

  if (loading) {
    return (
      <div className="cdn-comparison-container">
        <div className="cdn-loading">
          <div className="spinner"></div>
          <p>Loading CDN requirements comparison...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="cdn-comparison-container">
        <div className="cdn-error">
          <div className="error-icon">⚠️</div>
          <h3>Error Loading Comparison</h3>
          <p>{error}</p>
          <button className="cdn-btn-back" onClick={() => navigate(-1)}>
            Go Back
          </button>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="cdn-comparison-container">
        <div className="cdn-no-data">
          <h3>No Data Available</h3>
          <p>Could not retrieve CDN requirements for this project.</p>
          <button className="cdn-btn-back" onClick={() => navigate(-1)}>
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="cdn-comparison-container">
      {/* Header */}
      <div className="cdn-header">
        <button className="cdn-btn-back" onClick={() => navigate(-1)} title="Go back">
          ← Back
        </button>
        <div className="cdn-header-content">
          <h1 className="cdn-title">CDN Requirements Comparison</h1>
          <p className="cdn-subtitle">
            Comparing original extracted requirements with refined requirements
          </p>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="cdn-stats">
        <div className="cdn-stat-card cdn-stat-total">
          <div className="stat-value">{stats.total}</div>
          <div className="stat-label">Total Original Requirements</div>
          <div className="stat-description">From CDN extraction</div>
        </div>

        <div className="cdn-stat-card cdn-stat-kept">
          <div className="stat-value" style={{ color: "#10b981" }}>
            {stats.kept}
          </div>
          <div className="stat-label">Kept in Refinement</div>
          <div className="stat-description">{stats.keptPercent}% retained</div>
        </div>

        <div className="cdn-stat-card cdn-stat-removed">
          <div className="stat-value" style={{ color: "#ef4444" }}>
            {stats.removed}
          </div>
          <div className="stat-label">Removed in Refinement</div>
          <div className="stat-description">
            {stats.total > 0 ? Math.round(((stats.removed / stats.total) * 100)) : 0}% removed
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="cdn-legend">
        <div className="legend-title">Legend:</div>
        <div className="legend-items">
          <div className="legend-item">
            <span className="legend-badge legend-badge-kept">✓</span>
            <span className="legend-text">Kept in refined requirements</span>
          </div>
          <div className="legend-item">
            <span className="legend-badge legend-badge-removed">✕</span>
            <span className="legend-text">Removed during refinement</span>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="cdn-controls">
        <div className="cdn-search-box">
          <input
            type="text"
            placeholder="Search by requirement text or number..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="cdn-search-input"
          />
          {searchQuery && (
            <button
              className="cdn-search-clear"
              onClick={() => setSearchQuery("")}
              title="Clear search"
            >
              ✕
            </button>
          )}
        </div>

        <div className="cdn-filter-group">
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="cdn-select"
          >
            <option value="all">All Requirements ({data.original_count})</option>
            <option value="kept">Kept Only ({data.kept_count})</option>
            <option value="removed">Removed Only ({data.removed_count})</option>
          </select>

          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="cdn-select"
          >
            <option value="number">Sort by Number</option>
            <option value="status">Sort by Status (Removed First)</option>
          </select>
        </div>
      </div>

      {/* Requirements Table */}
      <div className="cdn-requirements-section">
        <h2 className="cdn-section-title">
          Showing {filteredAndSortedRequirements.length} of {data.original_count}{" "}
          requirements
        </h2>

        {filteredAndSortedRequirements.length === 0 ? (
          <div className="cdn-no-results">
            <p>No requirements match your current filters.</p>
          </div>
        ) : (
          <div className="cdn-table">
            <div className="cdn-table-head">
              <div className="cdn-th cdn-th-status">Status</div>
              <div className="cdn-th cdn-th-number">#</div>
              <div className="cdn-th cdn-th-cluster">Cluster</div>
              <div className="cdn-th cdn-th-requirement">Requirement</div>
            </div>

            <div className="cdn-table-body">
              {filteredAndSortedRequirements.map((req, idx) => {
                const isKept = req.status === "kept";
                const statusClass = isKept
                  ? "cdn-status-kept"
                  : "cdn-status-removed";
                const rowClass = isKept ? "cdn-row-kept" : "cdn-row-removed";

                return (
                  <div key={idx} className={`cdn-table-row ${rowClass}`}>
                    <div className={`cdn-td cdn-td-status ${statusClass}`}>
                      <span className="cdn-status-badge" title={req.status}>
                        {isKept ? "✓ Kept" : "✕ Removed"}
                      </span>
                    </div>

                    <div className="cdn-td cdn-td-number">
                      <strong>{req.req_number}</strong>
                    </div>

                    <div className="cdn-td cdn-td-cluster">
                      <span className="cdn-cluster-badge">{req.cluster_id}</span>
                    </div>

                    <div className="cdn-td cdn-td-requirement">
                      <p className="cdn-requirement-text">{req.requirement}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Summary Footer */}
      <div className="cdn-footer">
        <div className="cdn-summary">
          <p>
            Out of <strong>{stats.total}</strong> original requirements,{" "}
            <strong className="cdn-emphasis-kept">{stats.kept}</strong> were kept
            ({stats.keptPercent}%) and{" "}
            <strong className="cdn-emphasis-removed">{stats.removed}</strong> were
            removed.
          </p>
        </div>
      </div>
    </div>
  );
}
