import { useState } from "react";
import ChatInput from "./components/ChatInput";
import ResponseCard from "./components/ResponseCard";
import TrendChart from "./components/TrendChart";
import DataTable from "./components/DataTable";
import { analyzeQuery, downloadData } from "./api/analyze";

function App() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [currentQuery, setCurrentQuery] = useState("");
  const [currentFile, setCurrentFile] = useState(null);

  const handleAnalyze = async (query, file) => {
    setLoading(true);
    setCurrentQuery(query);
    setCurrentFile(file);
    try {
      const data = await analyzeQuery(query, file);
      setResult(data);
    } catch (err) {
      alert("Error: " + err.message);
    }
    setLoading(false);
  };

  const handleDownload = async (format) => {
    try {
      await downloadData(currentQuery, currentFile, format);
    } catch (err) {
      alert("Download Error: " + err.message);
    }
  };

  return (
    <div className="app-wrapper">
      <div className="container my-4">
        {/* Header with modern design */}
        <header className="app-header">
          <h1>
            <span className="emoji">🏘️</span> Real Estate Analysis
          </h1>
          <p className="subtitle">Intelligent insights for smart investments</p>
        </header>

        {/* Input Section */}
        <ChatInput onSubmit={handleAnalyze} loading={loading} />

        {/* Loading State */}
        {loading && (
          <div className="loading-container">
            <div className="spinner"></div>
            <p className="loading-text">Analyzing real estate data...</p>
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
                title="💰 Price Trend Analysis"
                data={result.chart.price_trend}
              />

              <TrendChart
                title="📊 Demand Trend Analysis"
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
          <p>Powered by OpenAI • Built with React & Django • By Taneesha Badhe</p>
        </footer>
      </div>
    </div>
  );
}

export default App;