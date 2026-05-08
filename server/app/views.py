"""
ProcBase – API Views
"""
import logging

from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AuditEvent, BlockchainSyncQueue, MedicineRecord
from .serializers import (
    AuditEventSerializer,
    BlockchainSyncQueueSerializer,
    DocumentUploadSerializer,
    MedicineRecordSerializer,
)
from .tasks import sync_record_to_blockchain

logger = logging.getLogger("procbase.views")


class MedicineViewSet(viewsets.ModelViewSet):
    """
    CRUD for MedicineRecord.

    POST  /api/v1/medicine/           → create record + queue blockchain sync
    GET   /api/v1/medicine/           → list (paginated)
    GET   /api/v1/medicine/{id}/      → retrieve single record
    PATCH /api/v1/medicine/{id}/      → partial update
    DELETE /api/v1/medicine/{id}/     → delete (admin only)

    Extra actions
    -------------
    POST /api/v1/medicine/{id}/retry_sync/  → manually re-queue failed syncs
    GET  /api/v1/medicine/unsynced/         → list records not yet on-chain
    """

    queryset = MedicineRecord.objects.select_related("sync_entry").all()
    serializer_class = MedicineRecordSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action == "destroy":
            return [IsAdminUser()]
        return super().get_permissions()

    @transaction.atomic
    def perform_create(self, serializer):
        record = serializer.save()

        # Create queue entry and dispatch Celery task
        BlockchainSyncQueue.objects.create(medicine=record)
        sync_record_to_blockchain.delay(record.pk)

        AuditEvent.objects.create(
            event_type=AuditEvent.EventType.RECORD_CREATED,
            medicine_batch=record.batch_number,
            detail={"drug_name": record.drug_name, "facility_code": record.facility_code},
        )
        logger.info("MedicineRecord created | batch=%s", record.batch_number)

    def perform_update(self, serializer):
        record = serializer.save()
        AuditEvent.objects.create(
            event_type=AuditEvent.EventType.RECORD_UPDATED,
            medicine_batch=record.batch_number,
            detail={"updated_fields": list(serializer.validated_data.keys())},
        )

    @action(detail=True, methods=["post"], url_path="retry_sync")
    def retry_sync(self, request, pk=None):
        """Manually re-queue a failed blockchain sync."""
        record = self.get_object()
        sync_record_to_blockchain.delay(record.pk)
        return Response(
            {"detail": f"Sync re-queued for batch {record.batch_number}."},
            status=status.HTTP_202_ACCEPTED,
        )

    @action(detail=False, methods=["get"], url_path="unsynced")
    def unsynced(self, request):
        """List all records that haven't been confirmed on-chain yet."""
        qs = self.get_queryset().filter(is_synced=False)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class DocumentHashView(APIView):
    """
    POST /api/v1/documents/hash/

    Upload a procurement PDF; receive its SHA-256 hash.
    The file is never persisted – only the hash is returned.

    Flow: Frontend uploads PDF → Django hashes it → returns digest →
          Frontend includes digest in the MedicineRecord POST body.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        serializer = DocumentUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        result = serializer.save()
        return Response(result, status=status.HTTP_200_OK)


class SyncQueueViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/v1/sync-queue/         → list all sync queue entries
    GET /api/v1/sync-queue/{id}/    → detail

    Admin-only; used for operational monitoring.
    """
    queryset = BlockchainSyncQueue.objects.select_related("medicine").all()
    serializer_class = BlockchainSyncQueueSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ["status"]


class AuditEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/v1/audit/   → append-only audit trail (admin only)
    """
    queryset = AuditEvent.objects.all()
    serializer_class = AuditEventSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ["event_type"]
