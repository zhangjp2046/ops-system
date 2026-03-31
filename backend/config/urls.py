"""ops_system URL Configuration"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API路由
    path('api/auth/', include('apps.users.urls')),
    path('api/customers/', include('apps.customers.urls')),
    path('api/assets/', include('apps.assets.urls')),
    path('api/monitoring/', include('apps.monitoring.urls')),
    path('api/alerts/', include('apps.alerts.urls')),
    path('api/scheduler/', include('apps.scheduler.urls')),
    path('api/inspection/', include('apps.inspection.urls')),
    path('api/dashboard/', include('apps.dashboard.urls')),
    path('api/workorder/', include('apps.workorder.urls')),
]

# 开发环境静态文件服务
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)