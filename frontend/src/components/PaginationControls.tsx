export function PaginationControls({
  total,
  limit,
  offset,
  onPage,
}: {
  total: number;
  limit: number;
  offset: number;
  onPage: (offset: number) => void;
}) {
  const from = total === 0 ? 0 : offset + 1;
  const to = Math.min(offset + limit, total);
  const previousOffset = Math.max(0, offset - limit);
  const nextOffset = offset + limit;

  return (
    <div className="pagination-controls">
      <span>
        Showing {from}-{to} of {total}
      </span>
      <div>
        <button type="button" disabled={offset <= 0} onClick={() => onPage(previousOffset)}>
          Previous
        </button>
        <button type="button" disabled={nextOffset >= total} onClick={() => onPage(nextOffset)}>
          Next
        </button>
      </div>
    </div>
  );
}
