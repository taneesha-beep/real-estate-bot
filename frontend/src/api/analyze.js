import axios from "axios";

const API_URL = "http://localhost:8000/api/analyze/";
const DOWNLOAD_URL = "http://localhost:8000/api/download/";

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
    format === "csv" ? "real_estate_data.csv" : "real_estate_data.xlsx"
  );
  document.body.appendChild(link);
  link.click();
  link.remove();
};
