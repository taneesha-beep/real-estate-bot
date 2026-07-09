import logging
import os
from io import BytesIO

import pandas as pd
from django.conf import settings
from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import utils
from .serializers import AnalyzeSerializer

logger = logging.getLogger(__name__)


class AnalyzeAPIView(APIView):
    """
    POST endpoint to analyze real estate data.

    POST fields:
    - query: text (required)
    - file: Excel file (optional; falls back to backend/data/sample.xlsx)
    """

    def post(self, request, *args, **kwargs):
        serializer = AnalyzeSerializer(data=request.data)

        if not serializer.is_valid():
            logger.warning("Serializer errors: %s", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        query = serializer.validated_data["query"]
        upload = request.FILES.get("file", None)

        # 1) Load Excel into a DataFrame.
        try:
            if upload:
                file_bytes = BytesIO(upload.read())
                df = utils.read_excel_from_filelike(file_bytes)
            else:
                sample_path = os.path.join(settings.BASE_DIR, "data", "sample.xlsx")
                if not os.path.exists(sample_path):
                    msg = "No file uploaded and sample.xlsx not found in backend/data/"
                    logger.error(msg)
                    return Response({"error": msg}, status=status.HTTP_400_BAD_REQUEST)
                df = utils.read_excel_from_filelike(sample_path)
        except Exception as exc:
            logger.exception("Excel read error")
            return Response(
                {"error": f"Failed to read Excel file: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 2) Verify required columns exist after header mapping.
        required = ["area", "year", "price", "demand", "size"]
        missing = [col for col in required if col not in df.columns]
        if missing:
            logger.warning("Missing columns after rename: %s", missing)
            return Response(
                {
                    "error": "Missing required columns after header mapping.",
                    "missing_columns": missing,
                    "available_columns": list(df.columns),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 3) Resolve areas from the query (LLM first, deterministic fallback).
        available_areas = sorted(df["area"].dropna().unique().tolist())
        try:
            parsed = utils.parse_query_with_llm(query, available_areas)
            areas = parsed.get("areas", [])
            intent = parsed.get("intent", "analysis")
            metrics = parsed.get("metrics", ["price"])
            logger.info("LLM parsed query: %s", parsed)
        except Exception as exc:
            logger.info("LLM parse failed, using fallback: %s", exc)
            areas = utils.extract_areas_from_query(query, available_areas)
            intent = "analysis"
            metrics = ["price", "demand"]

        logger.info("Areas detected: %s", areas)

        if not areas:
            return Response(
                {
                    "error": "No matching area found in dataset.",
                    "available_areas": available_areas,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 4) Build chart data.
        chart = utils.prepare_chart_data(df, areas)

        # 5) Build filtered table data.
        table = utils.prepare_table_data(df, areas)

        # 6) Build summary (LLM when a key is configured, else deterministic).
        summary = utils.generate_llm_summary(df, areas)

        # 7) Final response.
        return Response(
            {
                "summary": summary,
                "areas_detected": areas,
                "intent": intent,
                "metrics": metrics,
                "chart": chart,
                "table": table,
            },
            status=status.HTTP_200_OK,
        )


class DownloadDataAPIView(APIView):
    """POST endpoint to download filtered data as Excel or CSV."""

    def post(self, request, *args, **kwargs):
        query = request.data.get("query", "")
        upload = request.FILES.get("file", None)
        download_format = request.data.get("format", "excel").lower()

        try:
            if upload:
                file_bytes = BytesIO(upload.read())
                df = utils.read_excel_from_filelike(file_bytes)
            else:
                sample_path = os.path.join(settings.BASE_DIR, "data", "sample.xlsx")
                if not os.path.exists(sample_path):
                    return Response(
                        {"error": "No file uploaded and sample.xlsx not found"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                df = utils.read_excel_from_filelike(sample_path)
        except Exception as exc:
            logger.exception("Download read error")
            return Response(
                {"error": f"Failed to read file: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        available_areas = sorted(df["area"].dropna().unique().tolist())
        areas = utils.extract_areas_from_query(query, available_areas)

        if areas:
            mask = df["area"].str.lower().isin([a.lower() for a in areas])
            filtered_df = df[mask]
        else:
            filtered_df = df

        cols = [c for c in ["year", "area", "price", "demand", "size"] if c in filtered_df.columns]
        filtered_df = filtered_df[cols]

        if download_format == "csv":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="real_estate_data.csv"'
            filtered_df.to_csv(response, index=False)
            return response

        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            filtered_df.to_excel(writer, index=False, sheet_name="Real Estate Data")

        output.seek(0)
        response = HttpResponse(
            output.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="real_estate_data.xlsx"'
        return response
