export default function Footer() {
  return (
    <div className="container">
      <footer className="d-flex flex-wrap justify-content-between align-items-center py-3 my-4 border-top">
        <div className="col-md-4 d-flex align-items-center">
          <span className="mb-3 mb-md-0 text-body-secondary">
            © 2025 Company, Inc
          </span>
        </div>
        <ul className="nav col-md-4 justify-content-end list-unstyled d-flex">
          <li className="ms-3">
            <a className="text-body-secondary" href="#" aria-label="Instagram">
                <img
                  src="/assets/icons/instagram.svg"
                  alt="instagram"
                  width={24}
                  height={24}
                />
            </a>
          </li>
          <li className="ms-3">
            <a className="text-body-secondary" href="#" aria-label="Facebook">
                <img src="/assets/icons/facebook.svg" alt="facebook"  width={24}
                  height={24}/>
            </a>
          </li>
        </ul>
      </footer>
    </div>
  );
}
