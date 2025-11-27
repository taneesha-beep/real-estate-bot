import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";

// Import Bootstrap
import "bootstrap/dist/css/bootstrap.min.css";

// Import Custom CSS (order matters!)
import "./styles/custom.css";
import "./styles/components.css";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);