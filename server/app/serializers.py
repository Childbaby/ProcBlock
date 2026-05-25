from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import MedicineRecord, BlockchainSyncQueue, AuditEvent
from crypto.hashing import hash_file


class MedicineRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicineRecord
        fields = [
            'id',
            'drug_name',
            'batch_number',
            'atc_code',
            'quantity',
            'unit_of_measure',
            'facility_code',
            'district_code',
            'expiry_date',
            'received_date',
            'document_hash',
            'on_chain_signature',
            'is_synced',
            'stock_status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'received_date',
            'is_synced',
            'on_chain_signature',
            'created_at',
            'updated_at',
        ]


class BlockchainSyncQueueSerializer(serializers.ModelSerializer):
    medicine = MedicineRecordSerializer(read_only=True)

    class Meta:
        model = BlockchainSyncQueue
        fields = '__all__'


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = '__all__'


class DocumentUploadSerializer(serializers.Serializer):
    """Accepts a file upload and returns its SHA-256 hex digest.

    Used by the DocumentHashView which expects `serializer.save()` to
    return a serializable result (dict with `document_hash`).
    """

    file = serializers.FileField(write_only=True)

    def validate_file(self, value):
        # simple size limit to avoid extremely large uploads
        max_bytes = 10 * 1024 * 1024
        if getattr(value, 'size', None) and value.size > max_bytes:
            raise ValidationError('File too large (max 10MB)')
        return value

    def create(self, validated_data):
        uploaded = validated_data['file']
        # UploadedFile may wrap the actual file-like in `uploaded.file`
        file_obj = getattr(uploaded, 'file', uploaded)
        digest = hash_file(file_obj)
        return {'document_hash': digest}