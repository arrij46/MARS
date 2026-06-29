import React from "react";
import "../../style/RefinedRequirementsAnimation.css";

const SquigglyCircle = ({ isActive, size = "md", delay = 0 }) => {
  const sizeClass = `squiggly-${size}`; // sm, md, lg
  const stateClass = isActive ? "squiggly-active" : "squiggly-inactive";

  return (
    <div className="squiggly-container">
      <svg className={`${sizeClass} ${stateClass}`} viewBox="0 0 100 100">
        <defs>
          <linearGradient id={`g1-${delay}`} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#06b6a4" stopOpacity="0.85" />
            <stop offset="50%" stopColor="#06b6a4" stopOpacity="0.6" />
            <stop offset="100%" stopColor="#6366f1" stopOpacity="0.4" />
          </linearGradient>
        </defs>
        <path
          d="M50 10 Q65 15 70 30 Q75 45 65 55 Q55 65 50 80 Q45 95 30 85 Q15 75 20 60 Q25 45 30 30 Q35 15 50 10 Z"
          stroke={`url(#g1-${delay})`}
          className="squiggle-glow"
        />
      </svg>
    </div>
  );
};

export default SquigglyCircle;

// import React from "react";

// const SquigglyCircle = ({ isActive, size = "md", delay = 0 }) => {
//   const sizes = {
//     sm: 64,
//     md: 96,
//     lg: 128,
//   };
//   const s = sizes[size] || sizes.md;

//   return (
//     <div className="position-absolute top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center pointer-events-none">
//       <svg width={s} height={s} viewBox="0 0 100 100" style={{ opacity: isActive ? 1 : 0, transition: "all 0.6s ease", transform: isActive ? "scale(1)" : "scale(0.8)" }}>
//         <defs>
//           <linearGradient id={`g1-${delay}`} x1="0%" y1="0%" x2="100%" y2="100%">
//             <stop offset="0%" stopColor="#06b6a4" stopOpacity="0.85" />
//             <stop offset="50%" stopColor="#06b6a4" stopOpacity="0.6" />
//             <stop offset="100%" stopColor="#6366f1" stopOpacity="0.4" />
//           </linearGradient>
//         </defs>
//         <path d="M50 10 Q65 15 70 30 Q75 45 65 55 Q55 65 50 80 Q45 95 30 85 Q15 75 20 60 Q25 45 30 30 Q35 15 50 10 Z" fill="none" stroke={`url(#g1-${delay})`} strokeWidth="2" className="squiggle-glow" />
//       </svg>
//     </div>
//   );
// };

// export default SquigglyCircle;
