import { useState, useEffect, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { connectWebSocket, closeWebSocket } from "../utils/websocket";
import "../style/completeAnimation.css";

const STAGES = [
  {
    id: 0,
    label: "Conflict Detection",
    status: "Detecting conflicts...",
    CenterAnim: ConflictDetectAnim,
  },
  {
    id: 1,
    label: "Conflict Resolution",
    status: "Resolving conflicts...",
    CenterAnim: ConflictResolveAnim,
  },
  {
    id: 2,
    label: "Requirement Structuring",
    status: "Structuring requirements...",
    CenterAnim: StructuringAnim,
  },
  {
    id: 3,
    label: "Requirement Classification",
    status: "Classifying requirements...",
    CenterAnim: ClassificationAnim,
  },
  {
    id: 4,
    label: "Iterative Refinement",
    status: "Refining outputs...",
    CenterAnim: RefinementAnim,
  },
];

const RADIUS = 148;
const CX = 250;
const CY = 250;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
const STAGE_DURATION = 3000;

function getNodePosition(index, total) {
  const angle = (index / total) * 2 * Math.PI - Math.PI / 2;
  return {
    x: CX + RADIUS * Math.cos(angle),
    y: CY + RADIUS * Math.sin(angle),
  };
}

function getLabelPosition(index, total) {
  const LABEL_RADIUS = RADIUS + 42;
  const angle = (index / total) * 2 * Math.PI - Math.PI / 2;
  return {
    x: CX + LABEL_RADIUS * Math.cos(angle),
    y: CY + LABEL_RADIUS * Math.sin(angle),
  };
}

function ConflictDetectAnim() {
  return (
    <div className="center-anim conflict-detect">
      <div className="card card-a">
        <div className="card-line" />
        <div className="card-line short" />
      </div>
      <div className="card card-b overlap">
        <div className="card-line" />
        <div className="card-line short" />
      </div>
      <div className="conflict-glow" />
    </div>
  );
}

function ConflictResolveAnim() {
  return (
    <div className="center-anim conflict-resolve">
      <div className="card card-merge-a">
        <div className="card-line" />
        <div className="card-line short" />
      </div>
      <div className="card card-merge-b">
        <div className="card-line" />
        <div className="card-line short" />
      </div>
      <div className="merge-arrow">→</div>
      <div className="card card-merged">
        <div className="card-line" />
        <div className="card-line" />
        <div className="card-line short" />
      </div>
    </div>
  );
}

function StructuringAnim() {
  return (
    <div className="center-anim structuring">
      <div className="card card-source">
        <div className="card-line" />
        <div className="card-line short" />
      </div>
      <div className="split-cards">
        <div className="card card-small">
          <div className="card-line short" />
        </div>
        <div className="card card-small">
          <div className="card-line short" />
        </div>
        <div className="card card-small">
          <div className="card-line short" />
        </div>
      </div>
    </div>
  );
}

function ClassificationAnim() {
  return (
    <div className="center-anim classification">
      {["P0", "P1", "P2"].map((tag, i) => (
        <div key={i} className="tagged-card" style={{ animationDelay: `${i * 0.2}s` }}>
          <span className="tag">{tag}</span>
          <div className="card-line" />
          <div className="card-line short" />
        </div>
      ))}
    </div>
  );
}

function RefinementAnim() {
  return (
    <div className="center-anim refinement">
      <div className="card card-final">
        <div className="card-line" />
        <div className="card-line" />
        <div className="card-line short" />
        <div className="refine-glow" />
      </div>
      <div className="check-ring">
        <svg width="28" height="28" viewBox="0 0 28 28">
          <circle cx="14" cy="14" r="12" fill="none" stroke="rgba(255,255,255,0.5)" strokeWidth="1.5" />
          <polyline points="8,14 12,18 20,10" fill="none" stroke="rgba(255,255,255,0.85)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
    </div>
  );
}

export default function CompleteAnimation() {
  const navigate = useNavigate();
  const { projectId } = useParams();
  const [activeStage, setActiveStage] = useState(0);
  const [progress, setProgress] = useState(0);
  const [completedStages, setCompletedStages] = useState([]);
  const [animKey, setAnimKey] = useState(0);
  const progressRef = useRef(null);
  const startTimeRef = useRef(null);

  useEffect(() => {
    const handleMessage = (message) => {
      const { step, cleaned_classified } = message;
      if (step === "refinement_complete") {
        navigate(`/project/${projectId}/refined`, {
          state: { results: cleaned_classified },
        });
      }
    };

    connectWebSocket(projectId, handleMessage);

    return () => {
      closeWebSocket();
    };
  }, [navigate, projectId]);

  useEffect(() => {
    let raf;
    const animate = (timestamp) => {
      if (!startTimeRef.current) startTimeRef.current = timestamp;
      const elapsed = timestamp - startTimeRef.current;
      const p = Math.min(elapsed / STAGE_DURATION, 1);
      setProgress(p);

      if (p < 1) {
        raf = requestAnimationFrame(animate);
      } else {
        setTimeout(() => {
          setCompletedStages((prev) => [...prev, activeStage]);
          const next = (activeStage + 1) % STAGES.length;
          if (next === 0) setCompletedStages([]);
          setActiveStage(next);
          setAnimKey((k) => k + 1);
          startTimeRef.current = null;
          setProgress(0);
        }, 200);
      }
    };

    raf = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(raf);
  }, [activeStage]);

  const stageProgress = progress;
  const totalProgress = (activeStage + stageProgress) / STAGES.length;
  const arcLength = CIRCUMFERENCE * totalProgress;
  const strokeDashoffset = CIRCUMFERENCE - arcLength;

  const displayPercent = Math.round(totalProgress * 100);
  const { CenterAnim } = STAGES[activeStage];

  return (
    <div className="ca-root">
      <div className="ca-bg-circle ca-bg-circle--tl" />
      <div className="ca-bg-circle ca-bg-circle--br" />

      <div className="ca-wrapper">
        <div className="ca-svg-container">
          <svg
            width="500"
            height="500"
            viewBox="0 0 500 500"
            className="ca-svg"
          >
            <defs>
              <filter id="glow-soft">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
            </defs>

            {/* Outer decorative track */}
            <circle
              cx={CX}
              cy={CY}
              r={RADIUS + 18}
              fill="none"
              stroke="rgba(255,255,255,0.04)"
              strokeWidth="1"
            />

            {/* Main track */}
            <circle
              cx={CX}
              cy={CY}
              r={RADIUS}
              fill="none"
              stroke="rgba(255,255,255,0.08)"
              strokeWidth="2"
            />

            {/* Progress arc */}
            <circle
              cx={CX}
              cy={CY}
              r={RADIUS}
              fill="none"
              stroke="rgba(255,255,255,0.75)"
              strokeWidth="2"
              strokeLinecap="round"
              strokeDasharray={CIRCUMFERENCE}
              strokeDashoffset={strokeDashoffset}
              transform={`rotate(-90 ${CX} ${CY})`}
              className="ca-progress-arc"
            />

            {/* Stage nodes */}
            {STAGES.map((stage, i) => {
              const pos = getNodePosition(i, STAGES.length);
              const labelPos = getLabelPosition(i, STAGES.length);
              const isCompleted = completedStages.includes(i);
              const isActive = activeStage === i;
              const isPending = !isCompleted && !isActive;

              const nodeLabel = stage.label.split(" ");
              const line1 = nodeLabel.slice(0, Math.ceil(nodeLabel.length / 2)).join(" ");
              const line2 = nodeLabel.slice(Math.ceil(nodeLabel.length / 2)).join(" ");

              const textAnchor =
                labelPos.x < CX - 10
                  ? "end"
                  : labelPos.x > CX + 10
                  ? "start"
                  : "middle";

              return (
                <g key={i}>
                  {/* Glow for completed/active */}
                  {(isCompleted || isActive) && (
                    <circle
                      cx={pos.x}
                      cy={pos.y}
                      r={10}
                      fill="rgba(255,255,255,0.12)"
                      className={isActive ? "ca-node-glow-active" : "ca-node-glow"}
                    />
                  )}

                  {/* Node circle */}
                  <circle
                    cx={pos.x}
                    cy={pos.y}
                    r={isActive ? 7 : 5}
                    fill={
                      isCompleted
                        ? "rgba(255,255,255,0.9)"
                        : isActive
                        ? "rgba(255,255,255,0.85)"
                        : "transparent"
                    }
                    stroke={
                      isPending
                        ? "rgba(255,255,255,0.25)"
                        : "rgba(255,255,255,0.9)"
                    }
                    strokeWidth="1.5"
                    className={isActive ? "ca-node-active" : ""}
                  />

                  {/* Pulse ring for active node */}
                  {isActive && (
                    <circle
                      cx={pos.x}
                      cy={pos.y}
                      r={12}
                      fill="none"
                      stroke="rgba(255,255,255,0.3)"
                      strokeWidth="1"
                      className="ca-node-pulse"
                    />
                  )}

                  {/* Label */}
                  <text
                    x={labelPos.x}
                    y={labelPos.y - 6}
                    textAnchor={textAnchor}
                    className={`ca-node-label ${isActive ? "ca-node-label--active" : ""} ${isPending ? "ca-node-label--pending" : ""}`}
                  >
                    {line1}
                  </text>
                  {line2 && (
                    <text
                      x={labelPos.x}
                      y={labelPos.y + 9}
                      textAnchor={textAnchor}
                      className={`ca-node-label ${isActive ? "ca-node-label--active" : ""} ${isPending ? "ca-node-label--pending" : ""}`}
                    >
                      {line2}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>

          {/* Center content */}
          <div className="ca-center">
            <div className="ca-center-anim" key={animKey}>
              <CenterAnim />
            </div>
            <div className="ca-percent">{displayPercent}%</div>
          </div>
        </div>

        {/* Status text */}
        <div className="ca-status" key={`status-${activeStage}`}>
          <span className="ca-status-dot" />
          {STAGES[activeStage].status}
        </div>
      </div>
    </div>
  );
}
