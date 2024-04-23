from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^reporting/download$', views.reporting_download, name='reporting_download'),
]
