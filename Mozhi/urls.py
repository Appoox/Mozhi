"""
URL configuration for Mozhi project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from transcription import views
from django.contrib.auth import views as auth_views
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/login/', never_cache(csrf_exempt(auth_views.LoginView.as_view(redirect_authenticated_user=True))), name='login'),    
    path('users/logout/', views.logout_view, name='logout'),    
    path("users/", include("django.contrib.auth.urls")),
    path('', views.project_list, name='project_list'),
    path('projects/create/', views.create_project, name='create_project'),
    path('projects/import/', views.import_project, name='import_project'),
    path('projects/<uuid:project_id>/', views.project_detail, name='project_detail'),
    path('projects/<uuid:project_id>/delete/', views.delete_project, name='delete_project'),
    path('transcripts/<uuid:transcript_id>/delete/', views.delete_transcript, name='delete_transcript'),
    path('transcripts/<uuid:transcript_id>/edit/', views.edit_transcript, name='edit_transcript'),
    path('api/save-record/', views.save_record, name='save_record'),
    path('audio/<uuid:transcript_id>/', views.serve_audio, name='serve_audio'),
    path('export/', include('export.urls')),
    re_path(r'^.*$', RedirectView.as_view(pattern_name='project_list', permanent=False)),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
