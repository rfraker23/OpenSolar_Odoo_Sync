from django.contrib import admin
from django.urls import path, include  # include function needed

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),  # Make sure this line is present
]
