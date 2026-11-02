import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="page narrow">
      <div className="card empty">
        <h1>404</h1>
        <p>Page not found.</p>
        <Link to="/" className="btn">Go home</Link>
      </div>
    </div>
  );
}
