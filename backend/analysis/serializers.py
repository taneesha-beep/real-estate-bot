from rest_framework import serializers

class AnalyzeSerializer(serializers.Serializer):
    query = serializers.CharField(required=True)
    # optional file upload will be available in request.FILES
