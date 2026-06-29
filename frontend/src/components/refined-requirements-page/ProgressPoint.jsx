import React from "react";
import AnimatedCircles from "./AnimatedCircles";
import "../../style/RefinedRequirementsAnimation.css";

const ProgressPoint = ({ label, isActive, isCompleted }) => {
  let labelClass = "progress-label inactive";
  if (isActive) labelClass = "progress-label active";
  else if (isCompleted) labelClass = "progress-label completed";

  let nodeClass = "progress-node inactive";
  if (isActive) nodeClass = "progress-node active";
  else if (isCompleted) nodeClass = "progress-node completed";

  return (
    <div className="progress-point-container">
      <div className="progress-point-wrapper">
        <AnimatedCircles isActive={isActive || isCompleted} />
        <div className={nodeClass}>
          {isCompleted && !isActive && (
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3">
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          )}
        </div>
      </div>
      <small className={labelClass}>{label}</small>
    </div>
  );
};

export default ProgressPoint;



// import React from "react";
// import AnimatedCircles from "./AnimatedCircles";
// import "../../style/RefinedRequirements.css";

// const ProgressPoint = ({ label, isActive, isCompleted, index }) => {
//   let labelClass = "progress-label inactive";
//   if (isActive) labelClass = "progress-label active";
//   else if (isCompleted) labelClass = "progress-label completed";

//   let nodeClass = "progress-node inactive";
//   if (isActive) nodeClass = "progress-node active";
//   else if (isCompleted) nodeClass = "progress-node completed";

//   return (
//     <div className="progress-point-container">
//       <div className="progress-point-wrapper">
//         <AnimatedCircles isActive={isActive} index={index} />

//         <div className={nodeClass}>
//           {isCompleted && !isActive && (
//             <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3">
//               <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
//             </svg>
//           )}
//         </div>
//       </div>

//       <small className={labelClass}>{label}</small>
//     </div>
//   );
// };

// export default ProgressPoint;

// import React from "react";
// import AnimatedCircles from "./AnimatedCircles";

// const ProgressPoint = ({ label, isActive, isCompleted, index }) => {
//   const labelClass = isActive ? "text-dark fw-semibold" : isCompleted ? "text-primary" : "text-muted";

//   const nodeStyle = {
//     width: isActive ? 28 : 20,
//     height: isActive ? 28 : 20,
//     borderRadius: 9999,
//   };

//   return (
//     <div className="d-flex flex-column align-items-center position-relative">
//       <div className={`position-relative d-flex align-items-center justify-content-center`} style={{ width: 80, height: 80 }}>
//         <AnimatedCircles isActive={isActive} index={index} />

//         <div
//           className={`d-flex align-items-center justify-content-center position-relative`}
//           style={{
//             ...nodeStyle,
//             zIndex: 2,
//             background: isActive ? "linear-gradient(180deg,#06b6a4,#6366f1)" : isCompleted ? "#6366f1" : "#fff",
//             boxShadow: isActive ? "0 10px 20px rgba(99,102,241,0.18)" : isCompleted ? "0 6px 12px rgba(99,102,241,0.12)" : "none",
//             border: isActive || isCompleted ? "none" : "2px solid rgba(0,0,0,0.06)",
//           }}
//         >
//           {isCompleted && !isActive ? (
//             <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3">
//               <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
//             </svg>
//           ) : null}
//         </div>
//       </div>

//       <div className="mt-2 text-center" style={{ width: 160 }}>
//         <small className={labelClass} style={{ display: "block" }}>{label}</small>
//       </div>
//     </div>
//   );
// };

// export default ProgressPoint;
