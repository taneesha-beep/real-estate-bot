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
from .serializers import AnalyzeSerializer, DownloadSerializer

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB
# Returned for unexpected failures; details go to the server log, not the client.
INTERNAL_ERROR = "Something went wrong on the server. Please try again."


class BadRequest(Exception):
    """An expected problem with the request, returned to the client as a 400."""

    def __init__(self, body):
        super().__init__(body["error"])
        self.body = body


def load_dataframe(upload):
    """
    Read the uploaded Excel file (or backend/data/sample.xlsx when there is no
    upload) and check that the required columns exist after header mapping.
    """
    if upload:
        if not upload.name.lower().endswith(".xlsx"):
            raise BadRequest(
                {
                    "error": "Unsupported file type. Please upload an Excel .xlsx file "
                    "(.xls and .csv files are not supported)."
                }
            )
        if upload.size > MAX_UPLOAD_BYTES:
            raise BadRequest({"error": "File is too large. The maximum size is 5 MB."})
        source = BytesIO(upload.read())
    else:
        source = os.path.join(settings.BASE_DIR, "data", "sample.xlsx")
        if not os.path.exists(source):
            msg = "No file uploaded and sample.xlsx not found in backend/data/"
            logger.error(msg)
            raise BadRequest({"error": msg})

    try:
        df = utils.read_excel_from_filelike(source)
    except utils.SpreadsheetError as exc:
        raise BadRequest({"error": str(exc)})
    except Exception:
        logger.exception("Excel read error")
        raise BadRequest(
            {"error": "Could not read the file. Please upload a valid Excel .xlsx workbook."}
        )

    missing = [col for col in utils.EXPECTED_COLUMNS if col not in df.columns]
    if missing:
        logger.warning("Missing columns after rename: %s", missing)
        raise BadRequest(
            {
                "error": "Missing required columns after header mapping.",
                "missing_columns": missing,
                "available_columns": list(df.columns),
            }
        )
    return df


def resolve_areas(query, df):
    """
    Work out which areas the query refers to: the LLM first (its answer is
    validated against the data), then deterministic matching. Returns
    (areas, intent, metrics); raises BadRequest when no known area is found.
    """
    available_areas = sorted(df["area"].dropna().unique().tolist())
    try:
        parsed = utils.parse_query_with_llm(query, available_areas)
        areas, intent, metrics = parsed["areas"], parsed["intent"], parsed["metrics"]
        logger.info("LLM parsed query: %s", parsed)
    except Exception as exc:
        logger.info("LLM parse failed, using fallback: %s", exc)
        areas = utils.extract_areas_from_query(query, available_areas)
        intent = "analysis"
        metrics = ["price", "demand"]

    logger.info("Areas detected: %s", areas)

    if not areas:
        raise BadRequest(
            {
                "error": "No matching area found in dataset.",
                "available_areas": available_areas,
            }
        )
    return areas, intent, metrics


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

        try:
            # 1) Load Excel into a DataFrame and verify the required columns.
            df = load_dataframe(request.FILES.get("file"))

            # 2) Resolve areas from the query (LLM first, deterministic fallback).
            areas, intent, metrics = resolve_areas(query, df)

            # 3) Build chart data.
            chart = utils.prepare_chart_data(df, areas)

            # 4) Build filtered table data.
            table = utils.prepare_table_data(df, areas)

            # 5) Build summary (LLM when a key is configured, else deterministic).
            summary = utils.generate_llm_summary(df, areas)
        except BadRequest as exc:
            return Response(exc.body, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Unexpected error while analyzing")
            return Response({"error": INTERNAL_ERROR}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 6) Final response.
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
        serializer = DownloadSerializer(data=request.data)

        if not serializer.is_valid():
            logger.warning("Serializer errors: %s", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        query = serializer.validated_data["query"]
        download_format = serializer.validated_data["format"]

        try:
            # Same loading and area resolution as analyze, so the export
            # contains exactly the areas that were charted.
            df = load_dataframe(request.FILES.get("file"))
            areas, _, _ = resolve_areas(query, df)

            mask = df["area"].str.lower().isin([a.lower() for a in areas])
            filtered_df = df.loc[mask, utils.EXPECTED_COLUMNS]

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
        except BadRequest as exc:
            return Response(exc.body, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Unexpected error while preparing download")
            return Response({"error": INTERNAL_ERROR}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
