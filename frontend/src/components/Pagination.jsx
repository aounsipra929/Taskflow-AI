export default function Pagination({ page, pages, total, onChange }) {
  if (!total) return null;
  return (
    <div className="pagination">
      <button className="btn btn-outline btn-sm" disabled={page <= 1} onClick={() => onChange(page - 1)}>
        ← Prev
      </button>
      <span>
        Page {page} of {pages} · {total} item{total === 1 ? "" : "s"}
      </span>
      <button className="btn btn-outline btn-sm" disabled={page >= pages} onClick={() => onChange(page + 1)}>
        Next →
      </button>
    </div>
  );
}
