from django.contrib import admin
from .models import MedicineRecord, AuditEvent

admin.site.register(MedicineRecord)
admin.site.register(AuditEvent)
