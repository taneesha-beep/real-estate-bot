export default function ResponseCard({ summary, areas }) {
  if (!summary) return null;

  return (
    <div className="card mt-4 response-card">
      <div className="card-body">
        <div className="card-header-custom">
          <h2 className="card-title">Analysis summary</h2>
        </div>
        
        <div className="summary-content">
          <p className="card-text">{summary}</p>
        </div>

        {areas?.length > 0 && (
          <div className="areas-detected">
            <div className="areas-label">
              <strong>Detected areas</strong>
            </div>
            <div className="areas-badges">
              {areas.map((area, index) => (
                <span key={index} className="area-badge">
                  {area}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}