from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),  # <-- this line
]
from django.contrib import admin
from django.urls import path, include  # Include is necessary for routing to apps

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),  # This line includes your api app's URLs
]
