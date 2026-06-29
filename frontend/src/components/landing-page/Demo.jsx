import { useNavigate } from "react-router-dom";

export default function Demo() {
  const navigate = useNavigate();
  const title = "See MARS in Action";
  const subtitle =
    "Watch how MARS transforms requirement gathering from hours of meetings into minutes of intelligent conversation.";
  const sampleTitle = "Try a Sample Conversation";
  const aiMessage = `Let's start with your e-commerce platform requirements. Can you tell me about the core user actions customers should be able to perform?`;
  const userMessage = `Users should be able to browse products, add them to cart, and checkout...`;
  const buttonLabel = "Try Interactive Sample";
  const onButtonClick= () => navigate("/elicit");
  return (
    <div className="features" id="demo">
      {/* Title Section */}
      <h2 className="title">{title}</h2>
      <p className="subtitle">{subtitle}</p>

      {/* Sample Conversation Section */}
      <div className="sample-conversation">
        <h3 className="sample-title">{sampleTitle}</h3>

        {/* Conversation Box */}
        <div className="conversation-box">
          {/* AI Message */}
          <div className="message">
            <div className="avatar ai" aria-label="AI message">
              AI
            </div>
            <p>{aiMessage}</p>
          </div>

          {/* User Message */}
          <div className="message">
            <div className="avatar you" aria-label="User message">
              You
            </div>
            <p className="user-text">{userMessage}</p>
          </div>
        </div>

        {/* Button */}
        <div className="btn-container">
          <button
            className="sample-btn"
            onClick={onButtonClick}
            aria-label={buttonLabel}
          >
            {buttonLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
