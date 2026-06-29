import React, { useEffect, useState } from "react";
import "../../style/RefinedRequirementsAnimation.css";

const AnimatedCircles = ({ isActive }) => {
  const [animate, setAnimate] = useState(false);

  useEffect(() => {
    if (isActive) {
      const timer = setTimeout(() => setAnimate(true), 80);
      return () => clearTimeout(timer);
    } else {
      setAnimate(false);
    }
  }, [isActive]);

  return (
    <div className="animated-circles-container">
      {/* Outer ring */}
      <div
        className={`outer-ring ${animate ? "active animate-rotate-slow" : ""}`}
        style={{
          width: animate ? 96 : 40,
          height: animate ? 96 : 40,
        }}
      />

      {/* Inner glow */}
      <div
        className={`inner-glow ${animate ? "active" : ""}`}
        style={{
          width: animate ? 64 : 32,
          height: animate ? 64 : 32,
        }}
      />

      {animate && (
        <>
          {/* Dot 1 orbit */}
          <div className="dot-orbit animate-rotate-fast">
            <div style={{ marginLeft: 34 }}>
              <div className="dot" style={{ width: 6, height: 6, background: "#06b6a4" }} />
              <div
                className="dot dot-small"
                style={{ width: 4, height: 4, background: "rgba(6,182,164,0.6)" }}
              />
            </div>
          </div>

          {/* Dot 2 reverse orbit */}
          <div className="dot-orbit animate-rotate-med-rev">
            <div style={{ marginLeft: 26 }}>
              <div className="dot" style={{ width: 6, height: 6, background: "rgb(13, 68, 145)" }} />
              <div
                className="dot dot-small"
                style={{ width: 4, height: 4, background: "rgba(99,102,241,0.5)" }}
              />
            </div>
          </div>

          {/* Dot 3 vertical orbit */}
          <div className="dot-orbit animate-rotate-vertical">
            <div style={{ marginTop: -28 }}>
              <div
                className="dot"
                style={{ width: 6, height: 6, background: "rgba(6,182,164,0.75)" }}
              />
              <div
                className="dot dot-small"
                style={{ width: 4, height: 4, background: "rgba(6,182,164,0.4)" }}
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default AnimatedCircles;


// import React from "react";

// const AnimatedCircles = ({ isActive }) => {
//   return (
//     <div className="position-absolute top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center pointer-events-none">
//       {/* outer ring */}
//       <div
//         className={`position-absolute rounded-circle ${isActive ? "animate-rotate-slow" : ""}`}
//         style={{
//           width: isActive ? 96 : 40,
//           height: isActive ? 96 : 40,
//           border: isActive ? "1px solid rgba(99,102,241,0.25)" : "1px solid transparent",
//           background: isActive ? "conic-gradient(from 0deg, rgba(16,185,129,0.08), transparent)" : "transparent",
//           transition: "all 0.45s ease",
//         }}
//       />

//       {/* inner glow */}
//       <div
//         style={{
//           width: isActive ? 64 : 32,
//           height: isActive ? 64 : 32,
//           borderRadius: 9999,
//           transition: "all 0.45s ease",
//           background: isActive ? "linear-gradient(135deg, rgba(99,102,241,0.12), rgba(16,185,129,0.08))" : "transparent",
//           zIndex: 1,
//         }}
//       />

//       {isActive && (
//         <>
//           {/* Dot 1 orbit */}
//           <div className="position-absolute w-100 h-100 d-flex align-items-center justify-content-center animate-rotate-fast">
//             <div style={{ marginLeft: 34 }}>
//               <div style={{ width: 6, height: 6, borderRadius: 9999, background: "#06b6a4" }} />
//               <div style={{ width: 4, height: 4, borderRadius: 9999, background: "rgba(6,182,164,0.6)", marginTop: 6 }} />
//             </div>
//           </div>

//           {/* Dot 2 reverse */}
//           <div className="position-absolute w-100 h-100 d-flex align-items-center justify-content-center animate-rotate-med-rev">
//             <div style={{ marginLeft: 26 }}>
//               <div style={{ width: 6, height: 6, borderRadius: 9999, background: "rgb(13, 68, 145)" }} />
//               <div style={{ width: 4, height: 4, borderRadius: 9999, background: "rgba(99,102,241,0.5)", marginTop: 6 }} />
//             </div>
//           </div>

//           {/* Dot 3 vertical orbit */}
//           <div className="position-absolute w-100 h-100 d-flex align-items-center justify-content-center animate-rotate-vertical">
//             <div style={{ marginTop: -28 }}>
//               <div style={{ width: 6, height: 6, borderRadius: 9999, background: "rgba(6,182,164,0.75)" }} />
//               <div style={{ width: 4, height: 4, borderRadius: 9999, background: "rgba(6,182,164,0.4)", marginTop: 6 }} />
//             </div>
//           </div>
//         </>
//       )}
//     </div>
//   );
// };

// export default AnimatedCircles;
