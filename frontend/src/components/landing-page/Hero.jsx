import { useNavigate } from "react-router-dom";
import { BsArrowRight } from "react-icons/bs";

function Hero() {
    const navigate = useNavigate();
  // Local variables instead of parameters
  const description = "Transform how you gather requirements with conversational AI elicitation and automated quality checks for complete, conflict-free specifications.";
  const primaryBtn = { label: "Get Started",  onClick: () => navigate("/auth?mode=signup") 
 };
  const secondaryBtn = { label: "Try for Yourself", onClick: () => navigate("/auth?mode=signup") };
  const imageSrc = "/assets/demo-conversation-zoom.png";
  const trustedText = "Trusted by engineering teams at innovative companies";

  
  return (
    <div className="hero-section">
      <div className="hero-container">
        {/* Left side */}
        <div className="child-div1">
          <h1 className="hero-title">
            Create better <span className="line-break1">requirements —</span>
            <span className="gradient-text line-break2">faster</span>
          </h1>

          <p>{description}</p>

          <div className="get-started-buttons">
            <button
              type="button"
              className="get-started"
              aria-label={primaryBtn.label}
              onClick={primaryBtn.onClick}
            >
              {primaryBtn.label}
              <BsArrowRight className="arrow-icon" />
            </button>

            <button
              type="button"
              className="demo"
              aria-label={secondaryBtn.label}
              onClick={secondaryBtn.onClick}
            >
              {secondaryBtn.label}
            </button>
          </div>

          <p>{trustedText}</p>
        </div>

        {/* Right side */}
        <div className="child-div2">
          <img src={imageSrc} alt="background-hero-section" />
        </div>
      </div>
    </div>
  );
}

export default Hero;