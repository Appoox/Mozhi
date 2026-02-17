from django.urls import path
from . import views

app_name = 'export'

urlpatterns = [
    path('', views.project_list, name='project_list'),
    path('projects/<uuid:project_id>/', views.project_detail, name='project_detail'),
    path('projects/<uuid:project_id>/export/json/', views.export_project_json, name='export_project_json'),
]
