from rest_framework import serializers

class OpenSolarProjectSerializer(serializers.Serializer):
    name = serializers.CharField()
    address = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    postal_code = serializers.CharField()
    country = serializers.CharField(default="USA")
    customer_email = serializers.EmailField(required=False, allow_null=True)
    customer_first_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    customer_last_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    phone_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    project_stage = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    utility_provider = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    utility_rate = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    sales_rep_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
