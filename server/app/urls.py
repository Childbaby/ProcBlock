from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MedicineViewSet, DocumentHashView, SyncQueueViewSet, AuditEventViewSet

router = DefaultRouter()
router.register(r"medicine", MedicineViewSet, basename="medicine")
router.register(r"sync-queue", SyncQueueViewSet, basename="sync-queue")
router.register(r"audit", AuditEventViewSet, basename="audit")

urlpatterns = [
    path("", include(router.urls)),
    path("documents/hash/", DocumentHashView.as_view()),
]