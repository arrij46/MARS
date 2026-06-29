import { useLocation, useNavigate } from "react-router-dom";
import { useState } from "react";
import "../style/AuthenticationPage.css";

export default function AuthenticationPage() {
  const { search } = useLocation();
  const navigate = useNavigate();
  const params = new URLSearchParams(search);
  const mode = params.get("mode") || "signup"; // signup | login

  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
  });

  const [loading, setLoading] = useState(false);
  const [alert, setAlert] = useState({
    type: "", // success | warning | error
    message: "",
  });

  const handleChange = (e) => {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setAlert({ type: "", message: "" });
    setLoading(true);

    const payload =
      mode === "signup"
        ? {
            name: formData.name,
            email: formData.email,
            password: formData.password,
          }
        : {
            email: formData.email,
            password: formData.password,
          };

    try {
      const res = await fetch(`http://localhost:8000/api/auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json();

      // ---------------- HANDLE RESPONSES GRACEFULLY ----------------
      if (res.ok) {
        setAlert({ type: "success", message: data.message });

        // Store user name for splash screen
        const userName = mode === "signup" 
          ? formData.name 
          : (data.name || data.user?.name || "User");
        localStorage.setItem("user_name", userName);

        // Save token and user info to localStorage
        localStorage.setItem("token", data.token);
        localStorage.setItem("user", JSON.stringify(data.user));

        navigate("/splash-welcome");

        return;
      }

      // Expected validation / auth errors
      if ([400, 401, 409, 422].includes(res.status)) {
        setAlert({
          type: "warning",
          message: data.detail || "Invalid input",
        });
        return;
      }

      // Unexpected server error
      setAlert({
        type: "error",
        message: "Something went wrong. Please try again later.",
      });
    } catch (err) {
      setAlert({
        type: "error",
        message: "Unable to connect to server. Please try again later.",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <button className="back-btn" onClick={() => navigate(-1)}>Back</button>
  
      <div className="auth-card">
        <h2 className="auth-title">
          {mode === "signup" ? "Create an Account" : "Welcome Back"}
        </h2>

        {/* ALERT MESSAGE */}
        {alert.message && (
          <div className={`alert ${alert.type}`}>{alert.message}</div>
        )}

        <form onSubmit={handleSubmit}>
          {mode === "signup" && (
            <div className="form-group">
              <label htmlFor="name">Full Name</label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                placeholder="Enter your name"
                required
                autoComplete="name"
              />
            </div>
          )}

          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              placeholder="Enter your email"
              required
              autoComplete="username"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              placeholder="Enter your password"
              required
              autoComplete={
                mode === "signup" ? "new-password" : "current-password"
              }
            />
          </div>
          <div className="form-group google-login">
            <button
              type="button"
              className="btn-google"
              onClick={() => {
                if (mode === "signup") {
                  // window.location.href = "http://localhost:8000/api/auth/google/signup";
                  window.location.href =
                    "http://localhost:8000/api/auth/google";
                } else {
                  // window.location.href = "http://localhost:8000/api/auth/google/login";
                  window.location.href =
                    "http://localhost:8000/api/auth/google";
                }
              }}
            >
              {/* Optional Google icon */}
              <img src="../assets/icons/google.svg" alt="Google" />
              {mode === "signup" ? "Sign up with Google" : "Login with Google"}
            </button>
          </div>

          <button type="submit" className="btn-submit" disabled={loading}>
            {loading
              ? mode === "signup"
                ? "Signing up..."
                : "Logging in..."
              : mode === "signup"
                ? "Sign Up"
                : "Login"}
          </button>
        </form>

        <p className="toggle-text">
          {mode === "signup"
            ? "Already have an account?"
            : "Don’t have an account?"}{" "}
          <span
            className="toggle-link"
            onClick={() =>
              navigate(`/auth?mode=${mode === "signup" ? "login" : "signup"}`)
            }
            role="button"
            tabIndex={0}
          >
            {mode === "signup" ? "Login here" : "Sign up here"}
          </span>
        </p>
      </div>
    </div>
  );
}
