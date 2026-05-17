import { useState } from "react";

export default function ChatInput({ onSubmit, loading }) {
  const [query, setQuery] = useState("");
  const [file, setFile] = useState(null);
  const [fileName, setFileName] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!query.trim()) {
      alert("Please enter a query");
      return;
    }
    onSubmit(query, file);
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    setFile(selectedFile);
    setFileName(selectedFile ? selectedFile.name : "");
  };

  return (
    <form className="chat-input-form p-4 border rounded bg-light" onSubmit={handleSubmit}>
      <div className="form-header mb-4">
        <h3 className="form-title">🔍 Query Your Data</h3>
        <p className="form-subtitle">Ask anything about real estate trends and insights</p>
      </div>

      <div className="mb-4">
        <label className="form-label">
          <span className="label-icon">💬</span> Your Query
        </label>
        <input
          type="text"
          className="form-control"
          placeholder="e.g., Analyze price trends in Wakad"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={loading}
        />
        <small className="form-text">
          Try: "Compare Wakad and Akurdi" or "Show demand in Aundh"
        </small>
      </div>

      <div className="mb-4">
        <label className="form-label">
          <span className="label-icon">📁</span> Upload Excel File (Optional)
        </label>
        <div className="file-input-wrapper">
          <input
            type="file"
            className="form-control"
            accept=".xlsx,.xls"
            onChange={handleFileChange}
            disabled={loading}
            id="file-upload"
          />
          {fileName && (
            <div className="file-name-display">
              <span className="file-icon">📄</span> {fileName}
            </div>
          )}
        </div>
        <small className="form-text">
          Upload your own dataset or use our sample data
        </small>
      </div>

      <button 
        className="btn btn-primary w-100" 
        type="submit"
        disabled={loading}
      >
        {loading ? (
          <>
            <span className="btn-spinner"></span>
            Analyzing...
          </>
        ) : (
          <>
            <span className="btn-icon">🚀</span>
            Analyze Data
          </>
        )}
      </button>
    </form>
  );
}
