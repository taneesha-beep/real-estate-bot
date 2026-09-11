import { useState } from "react";
import ChatInput from "./components/ChatInput";
import ResponseCard from "./components/ResponseCard";
import TrendChart from "./components/TrendChart";
import DataTable from "./components/DataTable";
import { analyzeQuery, downloadData, describeError } from "./api/analyze";

function App() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [currentQuery, setCurrentQuery] = useState("");
  const [currentFile, setCurrentFile] = useState(null);

  const handleAnalyze = async (query, file) => {
    setLoading(true);
    // Clear the previous answer so it can't be mistaken for this query's.
    setResult(null);
    setError(null);
    setCurrentQuery(query);
    setCurrentFile(file);
    try {
      const data = await analyzeQuery(query, file);
      setResult(data);
    } catch (err) {
      setError(await describeError(err));
    }
    setLoading(false);
  };

  const handleDownload = async (format) => {
    try {
      await downloadData(currentQuery, currentFile, format);
    } catch (err) {
      const { message } = await describeError(err);
      alert("Download Error: " + message);
    }
  };

  return (
    <div className="app-wrapper">
      <div className="container my-4">
        {/* Header */}
        <header className="app-header">
          <h1>Real Estate Analysis</h1>
          <p className="subtitle">Explore price and demand trends by area.</p>
        </header>

        {/* Input Section */}
        <ChatInput onSubmit={handleAnalyze} loading={loading} />

        {/* Loading State */}
        {loading && (
          <div className="loading-container" role="status" aria-live="polite">
            <div className="spinner"></div>
            <p className="loading-text">Analyzing real estate data...</p>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="alert alert-danger mt-4" role="alert">
            <strong>{error.message}</strong>
            {error.availableAreas?.length > 0 && (
              <p className="mb-0 mt-2">
                Available areas: {error.availableAreas.join(", ")}
              </p>
            )}
            {error.missingColumns?.length > 0 && (
              <p className="mb-0 mt-2">
                Missing columns: {error.missingColumns.join(", ")}
              </p>
            )}
          </div>
        )}

        {/* Results Section */}
        {result && !loading && (
          <div className="results-container">
            <ResponseCard
              summary={result.summary}
              areas={result.areas_detected}
            />

            <div className="charts-grid">
              <TrendChart
                title="Price trends"
                data={result.chart.price_trend}
              />

              <TrendChart
                title="Demand trends"
                data={result.chart.demand_trend}
              />
            </div>

            <DataTable 
              rows={result.table} 
              onDownload={handleDownload}
            />
          </div>
        )}

        {/* Footer */}
        <footer className="app-footer">
          <p>Real Estate Analysis · Taneesha Badhe</p>
        </footer>
      </div>
    </div>
  );
}

export default App;