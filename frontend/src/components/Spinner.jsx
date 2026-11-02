export default function Spinner({ label = "Loading…", fullPage = false }) {
  return (
    <div className={fullPage ? "spinner-wrap full" : "spinner-wrap"} role="status">
      <div className="spinner" />
      <span>{label}</span>
    </div>
  );
}
