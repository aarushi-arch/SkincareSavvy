from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("users.urls")),
    path("", include("user_management.urls")),
    path("recommendations/", include("recommendations.urls")),
    path("face-analysis/", include("face_analysis.urls")),
    path("shop/", include("shop.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

