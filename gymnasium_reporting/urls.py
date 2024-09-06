from django.urls import path
from . import views

urlpatterns = [
    path('reporting/download/', views.reporting_download, name='reporting_download'),
]
