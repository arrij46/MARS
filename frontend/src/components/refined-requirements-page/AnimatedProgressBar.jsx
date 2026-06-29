import React, { useState, useEffect } from "react";
import ProgressPoint from "./ProgressPoint";
import "../../style/RefinedRequirementsAnimation.css";

const steps = [
  { id: 1, label: "Initial Correction of the detected Conflicts and Duplicates" },
  { id: 2, label: "Converting corrected requirements into Atomic Requirements" },
  { id: 3, label: "Refining Additional Detected Conflicts and Duplicates" },
  { id: 4, label: "Classifying corrected Requirements in FR/NFR Catagories" },
];

const STEP_DURATION =20000; // ms

const AnimatedProgressBar = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [progress, setProgress] = useState(0);
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    if (isComplete) return;
    const stepTimer = setInterval(() => {
      setCurrentStep((prev) => {
        if (prev >= steps.length - 1) {
          setIsComplete(true);
          return prev;
        }
        return prev + 1;
      });
    }, STEP_DURATION);
    return () => clearInterval(stepTimer);
  }, [isComplete]);

  useEffect(() => {
    if (isComplete) {
      setProgress(100);
      return;
    }

    const totalGaps = steps.length - 1;
    const stepPct = 100 / totalGaps;
    const startPct = currentStep * stepPct;
    const targetPct = Math.min(100, (currentStep + 1) * stepPct);

    let current = startPct;
    setProgress(startPct);

    const tick = 50;
    const increments = (targetPct - startPct) / (STEP_DURATION / tick);
    const progTimer = setInterval(() => {
      current = Math.min(targetPct, current + increments);
      setProgress(current);
      if (current >= targetPct) clearInterval(progTimer);
    }, tick);

    return () => clearInterval(progTimer);
  }, [currentStep, isComplete]);

  const handleRestart = () => {
    setCurrentStep(0);
    setProgress(0);
    setIsComplete(false);
  };

  return (
    <div className="animated-progress-bar">
      <div className="progress-track">
        <div className="progress-track-bg" />
        <div className="progress-track-fill" style={{ width: `${progress}%` }} />
        <div className="progress-track-glow" style={{ width: `${progress}%` }} />
      </div>

      {/* Points overlay on bar */}
      <div className="progress-points">
  {steps.map((s, idx) => {
    // Define the activation points in percentages
    const triggerPercents = [0, 35, 62, 85];
    const pointPct = triggerPercents[idx] ?? 100; // fallback in case of mismatch

    const pointActive = progress >= pointPct && progress < (triggerPercents[idx + 1] ?? 100);
    const pointCompleted = progress >= pointPct;

    return (
      <div key={s.id} className="flex-fill text-center position-relative">
        <ProgressPoint
          label={s.label}
          isActive={pointActive}
          isCompleted={pointCompleted}
        />
      </div>
    );
  })}
</div>


      {/* <div className="progress-bottom">
        {!isComplete ? (
          <div className="display-5 fw-light">{Math.round(progress)}%</div>
        ) : (
          <div className="mt-3">
            {/* <div className="processing-complete">
              <i className="bi bi-check2-circle"></i>
              <span>Processing Complete</span>
            </div>
            <p className="text-muted mt-2">All requirements have been processed successfully.</p>
            <button className="btn btn-primary" onClick={handleRestart}>
              Run Again
            </button> *}
          </div>
        )}
      </div>
      */}
    </div>
  );
};

export default AnimatedProgressBar;

// import React, { useState, useEffect } from "react";
// import ProgressPoint from "./ProgressPoint";
// import "../../style/RefinedRequirements.css";

// const steps = [
//   { id: 1, label: "Initial Correction of the detected Conflicts and Duplicates" },
//   { id: 2, label: "Converting corrected requirements into Atomic Requirements" },
//   { id: 3, label: "Refining Additional Detected Conflicts and Duplicates" },
//   { id: 4, label: "Classifying corrected Requirements in FR/NFR" },
// ];

// const STEP_DURATION = 5000; // ms

// const AnimatedProgressBar = () => {
//   const [currentStep, setCurrentStep] = useState(0);
//   const [progress, setProgress] = useState(0);
//   const [isComplete, setIsComplete] = useState(false);

//   useEffect(() => {
//     if (isComplete) return;
//     const stepTimer = setInterval(() => {
//       setCurrentStep((prev) => {
//         if (prev >= steps.length - 1) {
//           setIsComplete(true);
//           return prev;
//         }
//         return prev + 1;
//       });
//     }, STEP_DURATION);
//     return () => clearInterval(stepTimer);
//   }, [isComplete]);

//   useEffect(() => {
//     if (isComplete) {
//       setProgress(100);
//       return;
//     }

//     const totalGaps = steps.length - 1;
//     const stepPct = 100 / totalGaps;
//     const startPct = currentStep * stepPct;
//     const targetPct = Math.min(100, (currentStep + 1) * stepPct);

//     let current = startPct;
//     setProgress(startPct);

//     const tick = 50;
//     const increments = (targetPct - startPct) / (STEP_DURATION / tick);
//     const progTimer = setInterval(() => {
//       current = Math.min(targetPct, current + increments);
//       setProgress(current);
//       if (current >= targetPct) clearInterval(progTimer);
//     }, tick);

//     return () => clearInterval(progTimer);
//   }, [currentStep, isComplete]);

//   const handleRestart = () => {
//     setCurrentStep(0);
//     setProgress(0);
//     setIsComplete(false);
//   };

//   return (
//     <div className="animated-progress-bar">
//       {/* background track */}
//       <div className="progress-track">
//         <div className="progress-track-bg" />
//         <div className="progress-track-fill" style={{ width: `${progress}%` }} />
//         <div className="progress-track-glow" style={{ width: `${progress}%` }} />
//       </div>

//       {/* points */}
//       <div className="progress-points">
//         {steps.map((s, idx) => (
//           <div key={s.id} className="flex-fill text-center position-relative">
//             <ProgressPoint
//               label={s.label}
//               index={idx}
//               isActive={currentStep === idx}
//               isCompleted={currentStep > idx}
//             />
//           </div>
//         ))}
//       </div>

//       {/* bottom state */}
//       <div className="progress-bottom">
//         {!isComplete ? (
//           <div className="display-5 fw-light">{Math.round(progress)}%</div>
//         ) : (
//           <div className="mt-3">
//             <div className="processing-complete">
//               <i className="bi bi-check2-circle"></i>
//               <span>Processing Complete</span>
//             </div>
//             <p className="text-muted mt-2">All requirements have been processed successfully.</p>
//             <button className="btn btn-primary" onClick={handleRestart}>
//               Run Again
//             </button>
//           </div>
//         )}
//       </div>
//     </div>
//   );
// };

// export default AnimatedProgressBar;


// import React, { useState, useEffect } from "react";
// import ProgressPoint from "./ProgressPoint";

// const steps = [
//   { id: 1, label: "Initial Correction" },
//   { id: 2, label: "Making Your Requirements Atomic" },
//   { id: 3, label: "Refining Additional Detected Conflicts" },
//   { id: 4, label: "Classifying Refined and Corrected Requirements" },
// ];

// const STEP_DURATION = 5000; // ms

// const AnimatedProgressBar = () => {
//   const [currentStep, setCurrentStep] = useState(0);
//   const [progress, setProgress] = useState(0);
//   const [isComplete, setIsComplete] = useState(false);

//   // advance step every STEP_DURATION
//   useEffect(() => {
//     if (isComplete) return;
//     const stepTimer = setInterval(() => {
//       setCurrentStep((prev) => {
//         if (prev >= steps.length - 1) {
//           setIsComplete(true);
//           return prev;
//         }
//         return prev + 1;
//       });
//     }, STEP_DURATION);
//     return () => clearInterval(stepTimer);
//   }, [isComplete]);

//   // animate progress smoothly between steps
//   useEffect(() => {
//     if (isComplete) {
//       setProgress(100);
//       return;
//     }

//     const totalGaps = steps.length - 1;
//     const stepPct = 100 / totalGaps;
//     const startPct = currentStep * stepPct;
//     const targetPct = Math.min(100, (currentStep + 1) * stepPct);

//     let current = startPct;
//     setProgress(startPct);

//     const tick = 50;
//     const increments = (targetPct - startPct) / (STEP_DURATION / tick);
//     const progTimer = setInterval(() => {
//       current = Math.min(targetPct, current + increments);
//       setProgress(current);
//       if (current >= targetPct) clearInterval(progTimer);
//     }, tick);

//     return () => clearInterval(progTimer);
//   }, [currentStep, isComplete]);

//   const handleRestart = () => {
//     setCurrentStep(0);
//     setProgress(0);
//     setIsComplete(false);
//   };

//   return (
//     <div className="position-relative py-4">
//       {/* background track */}
//       <div className="position-relative" style={{ height: 8 }}>
//         <div className="bg-secondary rounded-pill w-100" style={{ height: 8, opacity: 0.15 }} />
//         <div
//           className="position-absolute top-0 start-0 rounded-pill"
//           style={{
//             height: 8,
//             width: `${progress}%`,
//             background: "linear-gradient(90deg, rgba(16,185,129,0.9), rgba(99,102,241,0.95))",
//             transition: "width 0.2s ease-out",
//             boxShadow: "0 6px 18px rgba(99,102,241,0.12)",
//           }}
//         />
//         <div
//           className="position-absolute top-0 start-0 rounded-pill"
//           style={{
//             height: 14,
//             width: `${progress}%`,
//             transform: "translateY(-3px)",
//             filter: "blur(6px)",
//             opacity: 0.35,
//             background: "linear-gradient(90deg, rgba(16,185,129,0.5), rgba(99,102,241,0.6))",
//             transition: "width 0.2s ease-out",
//             borderRadius: 9999,
//             pointerEvents: "none",
//           }}
//         />
//       </div>

//       {/* points */}
//       <div className="d-flex justify-content-between align-items-center position-relative mt-4">
//         {steps.map((s, idx) => (
//           <div key={s.id} className="flex-fill text-center position-relative">
//             <ProgressPoint
//               label={s.label}
//               index={idx}
//               isActive={currentStep === idx}
//               isCompleted={currentStep > idx}
//             />
//           </div>
//         ))}
//       </div>

//       {/* bottom state */}
//       <div className="text-center mt-5">
//         {!isComplete ? (
//           <>
//             <div className="display-5 fw-light">{Math.round(progress)}%</div>
//           </>
//         ) : (
//           <div className="mt-3">
//             <div className="d-inline-flex align-items-center gap-2 px-4 py-2 rounded-pill bg-success bg-opacity-10">
//               <i className="bi bi-check2-circle text-success fs-5"></i>
//               <span className="text-success fw-medium">Processing Complete</span>
//             </div>
//             <p className="text-muted mt-2">All requirements have been processed successfully.</p>
//             <button className="btn btn-primary" onClick={handleRestart}>
//               Run Again
//             </button>
//           </div>
//         )}
//       </div>
//     </div>
//   );
// };

// export default AnimatedProgressBar;
