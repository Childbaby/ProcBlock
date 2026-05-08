#!/usr/bin/env python3
import os
from pathlib import Path

# Ensure settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

USERNAME = os.environ.get("ADMIN_USER", "admin")
EMAIL = os.environ.get("ADMIN_EMAIL", "admin@example.com")
PASSWORD = os.environ.get("ADMIN_PASSWORD", "adminpass")

if User.objects.filter(username=USERNAME).exists():
    print(f"Superuser '{USERNAME}' already exists.")
else:
    User.objects.create_superuser(USERNAME, EMAIL, PASSWORD)
    print(f"Created superuser '{USERNAME}' with provided password.")
