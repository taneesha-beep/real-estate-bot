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
    <form className="chat-input-form" onSubmit={handleSubmit}>
      <div className="form-header mb-4">
        <h2 className="form-title">Analyze real estate data</h2>
        <p className="form-subtitle">Compare areas or review price and demand over time.</p>
      </div>

      <div className="mb-4">
        <label className="form-label" htmlFor="query">
          Query
        </label>
        <input
          type="text"
          id="query"
          aria-describedby="query-help"
          className="form-control"
          placeholder="e.g., Analyze price trends in Wakad"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={loading}
        />
        <small className="form-text" id="query-help">
          Try: "Compare Wakad and Akurdi" or "Show demand in Aundh"
        </small>
      </div>

      <div className="mb-4">
        <label className="form-label" htmlFor="file-upload">
          Excel file (optional)
        </label>
        <div className="file-input-wrapper">
          <input
            type="file"
            className="form-control"
            accept=".xlsx"
            onChange={handleFileChange}
            disabled={loading}
            id="file-upload"
            aria-describedby="file-help"
          />
          {fileName && (
            <div className="file-name-display">
              {fileName}
            </div>
          )}
        </div>
        <small className="form-text" id="file-help">
          Upload an .xlsx dataset, or leave blank to use the sample data.
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
          "Analyze data"
        )}
      </button>
    </form>
  );
}
