export default function ResponseCard({ summary, areas }) {
  if (!summary) return null;

  return (
    <div className="card mt-4 shadow-sm response-card">
      <div className="card-body">
        <div className="card-header-custom">
          <div className="icon-wrapper">
            <span className="card-icon">📊</span>
          </div>
          <h5 className="card-title">AI-Generated Analysis</h5>
        </div>
        
        <div className="summary-content">
          <p className="card-text">{summary}</p>
        </div>

        {areas?.length > 0 && (
          <div className="areas-detected">
            <div className="areas-label">
              <span className="label-icon">📍</span>
              <strong>Detected Areas:</strong>
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