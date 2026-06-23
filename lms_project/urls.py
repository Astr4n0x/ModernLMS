from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('public.urls')),
    path('', include('accounts.urls')),
    path('', include('courses.urls')),
    path('live/', include('live.urls')),
    path('', include('teacher.urls')),
    path('', include('qa.urls')),
    path('discussion/', include('discussion.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
