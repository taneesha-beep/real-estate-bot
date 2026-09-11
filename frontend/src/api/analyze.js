import axios from "axios";

// Backend base URL, e.g. https://api.example.com (set VITE_API_URL at build time).
const API_BASE_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");
const API_URL = `${API_BASE_URL}/api/analyze/`;
const DOWNLOAD_URL = `${API_BASE_URL}/api/download/`;

export const analyzeQuery = async (query, file = null) => {
  const formData = new FormData();
  formData.append("query", query);
  if (file) formData.append("file", file);

  const res = await axios.post(API_URL, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });

  return res.data;
};

export const downloadData = async (query, file = null, format = "excel") => {
  const formData = new FormData();
  formData.append("query", query);
  formData.append("format", format);
  if (file) formData.append("file", file);

  const res = await axios.post(DOWNLOAD_URL, formData, {
    headers: { "Content-Type": "multipart/form-data" },
    responseType: "blob",
  });

  // Create download link
  const url = window.URL.createObjectURL(new Blob([res.data]));
  const link = document.createElement("a");
  link.href = url;
  link.setAttribute(
    "download",
    format === "csv" ? "real_estate_data.csv" : "real_estate_data.xlsx",
  );
  document.body.appendChild(link);
  link.click();
  link.remove();
  // Release the blob once the browser has started the download.
  setTimeout(() => window.URL.revokeObjectURL(url), 0);
};

// Turn a failed request into { message, availableAreas, missingColumns },
// using the backend's JSON error body when there is one.
export const describeError = async (err) => {
  if (!err.response) {
    return { message: `Could not reach the server at ${API_BASE_URL}. Is the backend running?` };
  }

  let data = err.response.data;
  // Downloads use responseType "blob", so their error bodies arrive as a Blob.
  if (data instanceof Blob) {
    try {
      data = JSON.parse(await data.text());
    } catch {
      data = null;
    }
  }

  if (data?.error) {
    return {
      message: data.error,
      availableAreas: data.available_areas,
      missingColumns: data.missing_columns,
    };
  }
  // Validation errors look like {"query": ["This field may not be blank."]}.
  if (data && typeof data === "object") {
    const [field, messages] = Object.entries(data)[0] || [];
    if (field) {
      return { message: `${field}: ${[].concat(messages).join(" ")}` };
    }
  }
  return { message: err.message };
};
