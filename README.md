## Real Estate Bot (Django + React) 

## Overview

This project is a **Real Estate Analysis Bot** with:

* A **Django backend** (API + data processing)
* A **React frontend** (user interface)
* Tools to upload Excel data, run property analysis, and display results.

---

## **Project Structure**

```
realestate_bot_green 2/
│
├── backend/          → Django project
│   ├── analysis/     → API, ML/logic, serializers, views, utils
│   ├── data/         → sample input files
│   ├── media/        → uploaded files
│   ├── requirements.txt
│   └── manage.py
│
└── frontend/         → React + Vite app
    ├── src/
    ├── public/
    ├── package.json
    └── vite.config.js
```

---

## **Tech Stack**

### **Backend**

* Python + Django
* Django REST Framework
* SQLite (default)

### **Frontend**

* React (Vite)
* Axios

---

## **How to Run the Project**

### **1. Backend Setup**

```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Backend runs at:
**[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

### **2. Frontend Setup**

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at:
**[http://localhost:5173](http://localhost:5173)**

---

## **Key Backend Endpoints**

| Endpoint        | Purpose                             |
| --------------- | ----------------------------------- |
| `/api/upload/`  | Upload Excel file for analysis      |
| `/api/analyze/` | Run property comparisons/processing |
| `/api/results/` | Fetch processed data                |

(The `analysis/` app contains: `views.py`, `serializers.py`, `utils.py` for all logic.)

---

## **Features**

* Upload property data (Excel)
* Analyze and compare real estate information
* View results in the frontend
* Simple UI built using React
* API-driven backend for clean separation

---

## **Environment Variables**

Backend uses a `.env` file.
Update values such as:

```

SECRET_KEY=django-insecure-replace-me-in-prod
DEBUG=True

```

## Deployment

Frontend includes vercel.json for optional Vercel deployment.
Backend can be deployed on any Django-compatible host.
