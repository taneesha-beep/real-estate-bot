export default function DataTable({ rows, onDownload }) {
  if (!rows || rows.length === 0) {
    return (
      <div className="card mt-4 data-table-card">
        <div className="card-body">
          <p className="table-info mb-0">No rows match this query.</p>
        </div>
      </div>
    );
  }

  const columns = Object.keys(rows[0]);

  return (
    <div className="card mt-4 data-table-card">
      <div className="card-body">
        <div className="table-header">
          <div className="table-title-section">
            <h2 className="card-title mb-0">Data overview</h2>
            <span className="record-count">{rows.length} records</span>
          </div>
          
          <div className="download-buttons">
            <button
              className="btn btn-success btn-sm download-btn"
              onClick={() => onDownload("excel")}
              title="Download as Excel"
            >
              Excel
            </button>
            <button
              className="btn btn-info btn-sm download-btn"
              onClick={() => onDownload("csv")}
              title="Download as CSV"
            >
              CSV
            </button>
          </div>
        </div>

        <div className="table-responsive" tabIndex={0} role="region" aria-label="Query results">
          <table className="table table-striped custom-table">
            <thead>
              <tr>
                {columns.map((c) => (
                  <th key={c}>
                    <div className="th-content">
                      {c.replaceAll("_", " ")}
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
            Export these results as an Excel or CSV file.
          </p>
        </div>
      </div>
    </div>
  );
}