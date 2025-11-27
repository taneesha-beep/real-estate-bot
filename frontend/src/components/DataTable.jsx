export default function DataTable({ rows, onDownload }) {
  if (!rows || rows.length === 0) return null;

  const columns = Object.keys(rows[0]);

  return (
    <div className="card mt-4 shadow-sm data-table-card">
      <div className="card-body">
        <div className="table-header">
          <div className="table-title-section">
            <span className="table-icon">📋</span>
            <h5 className="card-title mb-0">Data Overview</h5>
            <span className="record-count">{rows.length} records</span>
          </div>
          
          <div className="download-buttons">
            <button
              className="btn btn-success btn-sm download-btn"
              onClick={() => onDownload("excel")}
              title="Download as Excel"
            >
              <span className="btn-icon">📊</span>
              Excel
            </button>
            <button
              className="btn btn-info btn-sm download-btn"
              onClick={() => onDownload("csv")}
              title="Download as CSV"
            >
              <span className="btn-icon">📄</span>
              CSV
            </button>
          </div>
        </div>

        <div className="table-responsive">
          <table className="table table-striped table-bordered custom-table">
            <thead>
              <tr>
                {columns.map((c) => (
                  <th key={c}>
                    <div className="th-content">
                      {c.toUpperCase()}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, idx) => (
                <tr key={idx}>
                  {columns.map((c) => (
                    <td key={c}>
                      <span className="td-content">{row[c]}</span>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="table-footer">
          <p className="table-info">
            💡 Tip: Click excel or csv button to export this data
          </p>
        </div>
      </div>
    </div>
  );
}