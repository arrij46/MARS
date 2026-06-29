import { useEffect, useState } from "react";
import { useNavigate, useParams, useLocation } from "react-router-dom";
import { authFetch } from "../utils/api";
import "bootstrap/dist/css/bootstrap.min.css";
import "../style/requirementList.css";

export default function RequirementList() {
  const navigate = useNavigate();
  const { projectId } = useParams();
  const location = useLocation();
  const displayType = location.state?.myString;
  const [categorizedPairs, setCategorizedPairs] = useState({
    Duplicate: [],
    Conflict: [],
    Neutral: [],
  });
  const [activeTab, setActiveTab] = useState(displayType);
  const [resultsData, setResults] = useState(null);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // === Fetch JSON from backend ===
  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await authFetch(`/api/cdn_results/${projectId}`);
        const data = await response.json();
        console.log("DATA ", data);
        console.log("Fetched result data:", data);
        if (data.status === "processing") {
          // If still processing, try again in 2 seconds
          setTimeout(() => fetchData(), 2000);
          return;
        }
        setResults(data);
        setIsLoading(false);
      } catch (err) {
        console.error("Error fetching results:", err);
        setError(err.message);
        setIsLoading(false);
      }
    };  

    fetchData();
  }, []);


  useEffect(() => {
  if (!resultsData) return;

  console.log("Processing results data:", resultsData);

  // Check if status is completed
  if (resultsData.status !== "completed") {
    console.log("Results not ready yet:", resultsData.status);
    return;
  }

  let allPairs = [];

  // Case 1: all_pairs is already provided (from our API transformation)
  if (resultsData.all_pairs && Array.isArray(resultsData.all_pairs)) {
    console.log("Using all_pairs array");
    allPairs = resultsData.all_pairs;
  }
  // Case 2: siamese_results format (object with nested arrays)
  else if (
    resultsData.siamese_results &&
    typeof resultsData.siamese_results === "object"
  ) {
    console.log("Detected siamese_results format, flattening...");
    const siameseResults = resultsData.siamese_results;
    // Flatten all pairs from all clusters
    allPairs = Object.values(siameseResults).flat();
  }
  // Case 3: classification_results format (object with arrays for each category)
  else if (resultsData.classification_results) {
    console.log("Detected classification_results format");
    const classificationResults = resultsData.classification_results;
    allPairs = [
      ...(classificationResults.duplicate || []),
      ...(classificationResults.conflict || []),
      ...(classificationResults.neutral || []),
    ];
  } else {
    console.warn("No recognizable results format found", resultsData);
    return;
  }

  console.log(`Found ${allPairs.length} total pairs`);

  // Categorize pairs by predicted_class
  const categories = { Duplicate: [], Conflict: [], Neutral: [] };
  allPairs.forEach((pair) => {
    // Normalize predicted_class (handle case variations)
    const predictedClass =
      pair.predicted_class || pair.predictedClass || "Neutral";
    const normalizedClass =
      predictedClass.charAt(0).toUpperCase() +
      predictedClass.slice(1).toLowerCase();

    if (categories[normalizedClass]) {
      categories[normalizedClass].push(pair);
    } else {
      // If class doesn't match, default to Neutral
      categories.Neutral.push(pair);
    }
  });

  console.log("Categorized pairs:", {
    Duplicate: categories.Duplicate.length,
    Conflict: categories.Conflict.length,
    Neutral: categories.Neutral.length,
  });

  setCategorizedPairs(categories);
}, [resultsData]);

  // === Tab Button Helper ===
  const renderTabButton = (label) => (
    <button
      className={`tab-btn ${label} me-2 px-4 py-2 fw-semibold ${
        activeTab === label ? "active-tab" : ""
      }`}
      onClick={() => setActiveTab(label)}
      type="button"
    >
      {label}
    </button>
  );

  // === Render ===
  return (
    <div className="requirement-page container py-4">
      <h2 className="text-center mb-4 fw-bold display-6 text-blue-dark">
        Requirement Pair Analysis
      </h2>

      <div className="d-flex justify-content-center mb-4 flex-wrap">
        {renderTabButton("Neutral")}
        {renderTabButton("Duplicate")}
        {renderTabButton("Conflict")}
      </div>

      <div className="card border-0 shadow-sm">
        <div
          className="card-body"
          style={{
            maxHeight: "70vh",
            overflowY: "auto",
            backgroundColor: "var(--grey-lightest)",
          }}
        >
          {isLoading ? (
            <div className="text-center py-5">
              <div className="spinner-border text-primary" role="status">
                <span className="visually-hidden">Loading...</span>
              </div>
              <p className="mt-3 text-muted">Loading analysis results...</p>
            </div>
          ) : error ? (
            <div className="alert alert-danger text-center" role="alert">
              Error loading results: {error}
            </div>
          ) : !resultsData ? (
            <p className="text-center text-muted">No results available</p>
          ) : activeTab === "Duplicate" ? (
            <PairList pairs={categorizedPairs.Duplicate} />
          ) : activeTab === "Conflict" ? (
            <PairList pairs={categorizedPairs.Conflict} />
          ) : (
            <PairList pairs={categorizedPairs.Neutral} />
            // <NeutralList requirements={categorizedPairs.Neutral} />
          )}
        </div>
      </div>
    </div>
  );
}

// === PairList Component ===
function PairList({ pairs }) {
  if (!pairs?.length)
    return <p className="text-muted text-center mt-4">No pairs found.</p>;

  return (
    <div className="row row-cols-1 row-cols-md-2 g-3">
       
      {pairs.map((pair, index) => (
        <div key={index} className="col">
          <div className="requirement-card p-3 rounded-3 bg-white h-100 shadow-sm">
            <p className="mb-2" style={{color:"black"}}>
            {pair.req1 || pair.idx1}
            </p>
            <hr className="my-2" />
            <p className="mb-0 " style={{color:"black"}}>
              {pair.req2 || pair.idx2}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}

// === NeutralList Component ===
function NeutralList({ requirements }) {
  if (!requirements?.length)
    return (
      <p className="text-muted text-center mt-4">No neutral requirements.</p>
    );

  return (
    <div className="row row-cols-1 row-cols-md-2 g-3">
      {requirements.map((req, index) => (
        <div key={index} className="col">
          <div className="requirement-card p-3 rounded-3 bg-white h-100 shadow-sm">
            <p className="mb-0 text-blue-dark">
              <strong>Req {req.index}:</strong> {req.text}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
