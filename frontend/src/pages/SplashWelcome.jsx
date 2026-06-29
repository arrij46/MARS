import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "../style/SplashWelcome.css";

// Generate particle config once (stable across renders)
const PARTICLES = Array.from({ length: 18 }, (_, i) => ({
  id: i,
  size: `${Math.random() * 6 + 3}px`,
  x: `${Math.random() * 100}%`,
  dur: `${Math.random() * 6 + 5}s`,
  delay: `${Math.random() * 6}s`,
}));

export default function SplashWelcome() {
  const navigate = useNavigate();

  useEffect(() => {
    const userName = localStorage.getItem("user_name");

    if (!userName) {
      navigate("/auth?mode=login");
      return;
    }

    const timer = setTimeout(() => {
      navigate("/dashboard");
    }, 2500);

    return () => clearTimeout(timer);
  }, [navigate]);

  const userName = localStorage.getItem("user_name") || "User";

  // Dynamically shrink font for long names so it never clips
  const getNameFontSize = (name) => {
    const len = name.length;
    if (len <= 8)  return "clamp(4rem, 10vmin, 7rem)";
    if (len <= 12) return "clamp(3rem, 8vmin, 5.5rem)";
    if (len <= 16) return "clamp(2.4rem, 6.5vmin, 4.5rem)";
    if (len <= 22) return "clamp(1.8rem, 5vmin, 3.5rem)";
    return "clamp(1.4rem, 3.8vmin, 2.8rem)";
  };

  return (
    <div className="splash-welcome-container">
      {/* Floating particles */}
      <div className="splash-particles">
        {PARTICLES.map((p) => (
          <span
            key={p.id}
            className="splash-particle"
            style={{
              "--size": p.size,
              "--x": p.x,
              "--dur": p.dur,
              "--delay": p.delay,
            }}
          />
        ))}
      </div>

      {/* Ring system — outer spins, middle pulses, inner accents */}
      <div className="splash-ring-outer" />
      <div className="splash-ring" />
      <div className="splash-ring-inner" />

      <div className="splash-welcome-content">
        {/* Three decorative dots */}
        <div className="splash-dots">
          <span className="splash-dot" />
          <span className="splash-dot" />
          <span className="splash-dot" />
        </div>

        <p className="splash-welcome-text">Welcome</p>
        <span
          className="splash-user-name"
          style={{ fontSize: getNameFontSize(userName) }}
        >
          {userName}
        </span>
        <div className="splash-divider" />
        <p className="splash-tagline">Glad to have you back</p>
      </div>
    </div>
  );
}