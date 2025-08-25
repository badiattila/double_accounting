from rest_framework import serializers
from accounting.models import Account

class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ["id", "code", "name", "type", "is_active", "normal_debit"]
