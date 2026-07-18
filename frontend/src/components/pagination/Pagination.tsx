import "../../styles/pagination/Pagination.css";

export function Pagination({ page, pages, onChange }: any) {
    return (
        <div className="mq-pagination">
            {Array.from({ length: pages }, (_, i) => i + 1).map((p) => (
                <button
                    key={p}
                    onClick={() => onChange(p)}
                    className={`mq-page-item ${p === page ? "active" : ""}`}
                >
                    {p}
                </button>
            ))}
        </div>
    );
}