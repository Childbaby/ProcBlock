from rest_framework import serializers
from .models import MedicineRecord

class MedicineSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicineRecord
        fields = '__all__'