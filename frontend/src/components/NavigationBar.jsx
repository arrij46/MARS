import { Link } from "react-router-dom";
import { SiPlanetscale } from "react-icons/si";

export default function Navigation() {
  return (
    <nav className="navbar navbar-expand-md navbar-light bg-light shadow-sm">
      <div className="container">
        {/* Brand */}
        <a className="navbar-brand d-flex align-items-center" href="#">
          <div
            className="d-flex align-items-center justify-content-center text-white rounded logo"
          >
            <SiPlanetscale className="logo"/>
          </div>
          <span className="ms-2 fw-bold fs-5 text-dark">MARS</span>
        </a>

        {/* Toggler */}
        <button
          className="navbar-toggler"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#navbarNav"
          aria-controls="navbarNav"
          aria-expanded="false"
          aria-label="Toggle navigation"
        >
          <span className="navbar-toggler-icon"></span>
        </button>

        {/* Links */}
        <div className="collapse navbar-collapse" id="navbarNav">
          <ul className="navbar-nav mx-auto mb-2 mb-md-0">
            <li className="nav-item button">
              <a className="nav-link" href="#features">
                Features
              </a>
            </li>
            <li className="nav-item button">
              <a className="nav-link" href="#workflow">
                Workflow
              </a>
            </li>
            <li className="nav-item button">
              <a className="nav-link" href="#demo">
                Demo
              </a>
            </li>
          </ul>

          {/* Auth buttons */}
          <div className="d-flex ms-3 buttonsdiv">
          <Link to="/auth?mode=login" className="btn me-2 button-login">
              Login
            </Link>
            <Link to="/auth?mode=signup" className="btn button-signup">
              Sign Up
            </Link>
            
          </div>
        </div>
      </div>
    </nav>
  );
}
