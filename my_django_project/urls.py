from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),  # this points to the above file
    path("", lambda request: HttpResponse("✅ API is running")),
]
