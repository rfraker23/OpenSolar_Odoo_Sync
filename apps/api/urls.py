from django.urls import path
from .views import sync_all

urlpatterns = [
    # GET /api/sync-all/?key=<YOUR_SECRET>
    path('sync-all/', sync_all, name='sync_all'),
]

