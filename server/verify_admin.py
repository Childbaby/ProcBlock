#!/usr/bin/env python3
import os
from pathlib import Path

# Load environment from repo root .env for local dev
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    with env_path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

# Ensure settings are available
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

try:
    import django
    django.setup()

    from django.contrib import admin

    registry = admin.site._registry
    print("Registered models:")
    for model in registry.keys():
        print("-", model._meta.app_label, model._meta.model_name, model.__name__)

    print()
    print("MedicineRecord registered:", any(m.__name__ == "MedicineRecord" for m in registry.keys()))
    print("AuditEvent registered:", any(m.__name__ == "AuditEvent" for m in registry.keys()))
    print()
    print("If both are True, admin registration is successful.")
except Exception as e:
    print("Django setup failed:", e)
    print("Falling back to static analysis of app/admin.py...")
    admin_path = Path(__file__).resolve().parent / "app" / "admin.py"
    if not admin_path.exists():
        admin_path = Path(__file__).resolve().parent / "app" / "admin.py"
    content = admin_path.read_text(encoding="utf-8")
    regs = []
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("admin.site.register("):
            inside = line[len("admin.site.register("):].rstrip(")").strip()
            if inside:
                model_name = inside.split(",")[0].strip()
                regs.append(model_name)
    print("Statically found registrations:", regs)
    print("MedicineRecord registered (static):", "MedicineRecord" in regs)
    print("AuditEvent registered (static):", "AuditEvent" in regs)
