from rest_framework import serializers

class AnalyzeSerializer(serializers.Serializer):
    # CharField trims surrounding whitespace and rejects blank values by default.
    query = serializers.CharField(required=True, max_length=500)
    # optional file upload will be available in request.FILES


class DownloadSerializer(AnalyzeSerializer):
    format = serializers.CharField(required=False, default="excel")

    def validate_format(self, value):
        value = value.lower()
        if value not in ("excel", "csv"):
            raise serializers.ValidationError('Must be "excel" or "csv".')
        return value
