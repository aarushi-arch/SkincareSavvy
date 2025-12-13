"""
ASGI config for SkincareSavvy project.
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SkincareSavvy.settings")

application = get_asgi_application()

