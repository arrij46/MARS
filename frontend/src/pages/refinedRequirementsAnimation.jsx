import React, { useEffect, useState } from "react";
import AnimatedProgressBar from "../components/refined-requirements-page/AnimatedProgressBar";
import { useNavigate, useParams } from "react-router-dom";
import { connectWebSocket, closeWebSocket } from "../utils/websocket";

export default function RefinedRequirementsAnimation() {
  const navigate = useNavigate();
  const { projectId } = useParams();
  const [progressMessage, setProgressMessage] = useState("Connecting...");

  useEffect(() => {
    const handleMessage = (message) => {
      console.log("[WebSocket] Message:", message);
      const { step, cleaned_classified } = message;

      if (step === "workflow_started") {
        setProgressMessage("Workflow started...");
      } else if (step === "cdn_start") {
        setProgressMessage("CDN processing started...");
      } else if (step === "cdn_complete") {
        setProgressMessage("CDN processing complete...");
      } else if (step === "refinement_start") {
        setProgressMessage("Refinement started...");
      } else if (step === "refinement_progress") {
        setProgressMessage("Refinement in progress...");
      } else if (step === "refinement_complete") {
        setProgressMessage("Refinement complete!");
        navigate(`/project/${projectId}/refined`, {
          state: { results: cleaned_classified },
        });
      } else if (step === "doc_user_story_start") {
        setProgressMessage("Generating documents and user stories...");
      } else if (step === "workflow_complete") {
        setProgressMessage("Workflow complete!");
      }
    };

    // Orchestrator is already running from upload.
    // Just connect — backend flushes any buffered messages immediately on connect.
    connectWebSocket(projectId, handleMessage);

    return () => {
      closeWebSocket();
    };
  }, [navigate, projectId]);

  return (
    <div className="refinement-animation-container">
      <div className="navbar-refinement">
        <h2 className="text-center mb-4 fw-bold display-6 text-blue-dark">
          Requirement Refinement and Correction
        </h2>
      </div>
      <div className="refinement-animation">
        <div className="text-center mb-5">
          <h1 className="h3 fw-semibold">Processing Your Requirements</h1>
          <p className="text-muted">
            Please wait while we analyze and refine your input
          </p>
          {/* <p className="text-muted fst-italic mt-2">{progressMessage}</p> */}
        </div>
        <div className="mx-auto" style={{ maxWidth: 1300 }}>
          <AnimatedProgressBar />
        </div>
      </div>
    </div>
  );
}

// import React, { useEffect, useRef, useState } from "react";
// import { authFetch } from "../utils/api";
// import AnimatedProgressBar from "../components/refined-requirements-page/AnimatedProgressBar";
// import { useNavigate } from "react-router-dom";
// import { connectWebSocket, closeWebSocket } from "../utils/websocket";
// import { useParams } from "react-router-dom";

// export default function RefinedRequirementsAnimation() {
//   const navigate = useNavigate();
//   const wsConnected = useRef(false);
//   const { projectId } = useParams();

//   const [progressMessage, setProgressMessage] = useState(
//     "Waiting for refinement..."
//   );
// const [convId, setConvId] = useState(null);
// useEffect(() => {
//   // define async function inside the effect
//   const startWorkflow = async () => {
//     try {
//       const res = await authFetch("/api/get_conv_id", {
//         method: "POST",
//       });
//       const data = await res.json();
//       setConvId(data.conv_id);

//       console.log("[RefinementAnimation] Conv ID set:", data.conv_id);
//       // you can also connect WebSocket here if needed
//     } catch (err) {
//       console.error("Error starting workflow:", err);
//     }
//   };

//   // immediately call it
//   startWorkflow();
// }, []); // empty array = run once on mount


//   useEffect(() => {
//     if (!convId || wsConnected.current) return; // wait until convId exists & WS not connected

//     console.log("[RefinementAnimation] Connecting WS for conv:", convId);

//     connectWebSocket(convId, (message) => {
//       console.log("[WebSocket] Refinement message:", message);

//       const { step, cleaned_classified } = message;
//       console.log("[RefinementAnimation] Message recieved in payload:", message)
//       // Show heartbeat / progress
//       if (step === "refinement_processing") {
//         setProgressMessage("Refinement in progress...");
//       }
//       // Final results received → navigate to requirement list page
//       else if (step === "refinement_complete") {
//         setProgressMessage("Refinement complete!");
 
//         navigate(`/project/${projectId}/refined`, {
//           state: { results: cleaned_classified },
//         });

//       } else if (step === "refinement_timeout") {
//         setProgressMessage("Refinement timed out. Please try again.");
//       } else if (step === "cdn_start") {
//         setProgressMessage("CDN processing started...");
//       } else if (step === "cdn_complete") {
//         setProgressMessage("CDN processing complete...");
//       }
//     });

//     wsConnected.current = true;

//     // Cleanup WS on component unmount
//     return () => {
//       closeWebSocket();
//       wsConnected.current = false;
//     };
//   }, [convId, navigate]);

//   return (
//     <div className="refinement-animation-container">
//       <div className="navbar-refinement">
//         <h2 className="text-center mb-4 fw-bold display-6 text-blue-dark">
//           Requirement Refinement and Correction
//         </h2>
//       </div>
//       <div className="refinement-animation">
//         <div className="text-center mb-5">
//           <h1 className="h3 fw-semibold">Processing Your Requirements</h1>
//           <p className="text-muted">
//             Please wait while we analyze and refine your input
//           </p>
//         </div>

//         <div className="mx-auto" style={{ maxWidth: 1300 }}>
//           <AnimatedProgressBar />
//         </div>
//       </div>
//     </div>
//   );
// }
