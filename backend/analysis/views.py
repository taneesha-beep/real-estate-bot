from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse
from .serializers import AnalyzeSerializer
from . import utils
import os
from django.conf import settings
from io import BytesIO
import pandas as pd


class AnalyzeAPIView(APIView):
    """
    POST endpoint to analyze real estate data.

    POST fields:
    - query: text (required)
    - file: Excel file (optional)
    """

    def post(self, request, *args, **kwargs):
        serializer = AnalyzeSerializer(data=request.data)

        if not serializer.is_valid():
            print("Serializer errors:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        query = serializer.validated_data["query"]
        upload = request.FILES.get("file", None)

        # -----------------------
        # 1) LOAD EXCEL DATAFRAME
        # -----------------------
        try:
            if upload:
                file_bytes = BytesIO(upload.read())
                df = utils.read_excel_from_filelike(file_bytes)
            else:
                sample_path = os.path.join(settings.BASE_DIR, "data", "sample.xlsx")
                if not os.path.exists(sample_path):
                    msg = "No file uploaded and sample.xlsx not found in backend/data/"
                    print(msg)
                    return Response({"error": msg}, status=status.HTTP_400_BAD_REQUEST)

                df = utils.read_excel_from_filelike(sample_path)
        except Exception as e:
            print("Excel read error:", e)
            return Response(
                {"error": f"Failed to read Excel file: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -----------------------
        # 2) CHECK REQUIRED COLUMNS
        # -----------------------
        required = ["area", "year", "price", "demand", "size"]
        missing = [col for col in required if col not in df.columns]

        if missing:
            print("Missing columns after rename:", missing)
            return Response(
                {
                    "error": "Missing required columns after header mapping.",
                    "missing_columns": missing,
                    "available_columns": list(df.columns),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -----------------------
        # 3) FIND AREAS FROM QUERY WITH LLM + FALLBACK
        # -----------------------
        available_areas = sorted(df["area"].dropna().unique().tolist())

        try:
            parsed = utils.parse_query_with_llm(query, available_areas)
            areas = parsed.get("areas", [])
            intent = parsed.get("intent", "analysis")
            metrics = parsed.get("metrics", ["price"])
            print("LLM parsed:", parsed)
        except Exception as e:
            print("LLM failed, using fallback:", e)
            areas = utils.extract_areas_from_query(query, available_areas)
            intent = "analysis"
            metrics = ["price", "demand"]

        print("Areas detected:", areas)

        if not areas:
            return Response(
                {
                    "error": "No matching area found in dataset.",
                    "available_areas": available_areas,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # -----------------------
        # 4) CHART DATA
        # -----------------------
        chart = utils.prepare_chart_data(df, areas)

        # -----------------------
        # 5) FILTERED TABLE
        # -----------------------
        table = utils.prepare_table_data(df, areas)

        # -----------------------
        # 6) SUMMARY (LLM IF AVAILABLE)
        # -----------------------
        if os.getenv("OPENAI_API_KEY"):
            try:
                summary = utils.generate_llm_summary(df, areas)
            except Exception as e:
                print("LLM summary failed:", e)
                summary = utils.generate_mock_summary(df, areas)
        else:
            summary = utils.generate_mock_summary(df, areas)

        # -----------------------
        # 7) FINAL RESPONSE
        # -----------------------
        return Response(
            {
                "summary": summary,
                "areas_detected": areas,
                "chart": chart,
                "table": table,
            },
            status=status.HTTP_200_OK,
        )


class DownloadDataAPIView(APIView):
    """
    POST endpoint to download filtered data as Excel or CSV.
    """

    def post(self, request, *args, **kwargs):
        query = request.data.get("query", "")
        upload = request.FILES.get("file", None)
        download_format = request.data.get("format", "excel").lower()

        # Load DataFrame
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
        except Exception as e:
            return Response(
                {"error": f"Failed to read file: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Extract areas
        available_areas = sorted(df["area"].dropna().unique().tolist())
        areas = utils.extract_areas_from_query(query, available_areas)

        # Filter data
        if areas:
            mask = df["area"].str.lower().isin([a.lower() for a in areas])
            filtered_df = df[mask]
        else:
            filtered_df = df

        # Select important columns
        cols = [c for c in ["year", "area", "price", "demand", "size"] if c in filtered_df.columns]
        filtered_df = filtered_df[cols]

        # CSV download
        if download_format == "csv":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="real_estate_data.csv"'
            filtered_df.to_csv(response, index=False)
            return response

        # Excel download
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
