import { useEffect, useState } from "react"; // ← add this
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import "bootstrap/dist/css/bootstrap.min.css";
import "./style/index.css";
import "./style/landing_page.css";
import Dashboard from "./pages/Dashboard";
import LandingPage from "./pages/landing-page";
import AuthenticationPage from "./pages/AuthenticationPage"; 
import SplashWelcome from "./pages/SplashWelcome";
import ElicitationPage from "./pages/elicitation";
import RequirementList from "./pages/requirementList";
import CompleteAnimation from "./pages/completeanimation";
import AttachmentComponent from "./components/elicitation-page/AttachmentComponent";
import RefinedRequirementsList from "./pages/refinedRequirementsList";
import EditorPage from "./pages/editorPage";
import UserStoryPage from "./pages/UserStoryPage";
import CDNComparison from "./components/CDNComparison";
import ProjectLayout from "./components/ProjectLayout";
// ── Protected Route wrapper ───────────────────────────────
function ProtectedRoute({ children }) {
  const token = localStorage.getItem("token");
  if (!token) return <Navigate to="/auth" replace />;
  return children;
}



function App() {
  const [authChecked, setAuthChecked] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");
    if (token) {
      localStorage.setItem("token", token);
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  // Verify token on every app load
  useEffect(() => {
    const token = localStorage.getItem("token");

    if (!token) {
      setAuthChecked(true);
      return;
    }

    fetch("http://localhost:8000/api/auth/me", {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (!res.ok) {
          // Token expired or invalid
          localStorage.removeItem("token");
          localStorage.removeItem("user");
        }
      })
      .catch(() => {
        // Server unreachable — leave token as is, don't log out
      })
      .finally(() => {
        setAuthChecked(true);
      });
  }, []);

  // Don't render routes until auth check is done (prevents flicker)
  if (!authChecked) return null;

  return (
    <Router>
        <Routes>
                  {/* Public routes */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/dashboard/:projectId?" element={<Dashboard />} />
          <Route path="/auth" element={<AuthenticationPage />} />
          <Route path="/splash-welcome" element={<SplashWelcome />} />

        {/* Protected routes */}
        <Route path="/dashboard" element={
          <ProtectedRoute><Dashboard /></ProtectedRoute>
        } />

        <Route path="/project/:projectId" element={
          <ProtectedRoute><ProjectLayout /></ProtectedRoute>
        }>
          <Route path="elicit" element={<ElicitationPage />} />
          <Route path="requirements" element={<RequirementList />} />
          <Route path="attachment" element={<AttachmentComponent />} />
          <Route path="refined-animation" element={<CompleteAnimation />} />
          <Route path="refined" element={<RefinedRequirementsList />} />
          <Route path="user-stories" element={<UserStoryPage />} />
          <Route path="editor" element={<EditorPage />} />
          <Route path="cdn-comparison" element={<CDNComparison />} />
        </Route>

        {/* Catch all → redirect to home */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
