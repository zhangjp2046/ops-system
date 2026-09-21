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
    path('api/inspection/', include('apps.inspection.urls')),
    path('api/dashboard/', include('apps.dashboard.urls')),
    path('api/system/', include('apps.system.urls')),
    path('api/discovery/', include('apps.discovery.urls')),
    path('api/skills/', include('apps.skills.urls')),
    path('api/scheduler/v2/', include('apps.scheduler_v2.urls')),
    path('api/lab/', include('apps.lab_inventory.urls')),
]

# 开发环境静态文件服务
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)