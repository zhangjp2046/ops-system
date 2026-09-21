from django.contrib import admin
from .models import Alert, AlertRule, AlertSubscription
from .threshold_models import AlertThreshold, AlertThresholdRule, AlertThresholdTemplate

admin.site.register(Alert)
admin.site.register(AlertRule)
admin.site.register(AlertSubscription)
admin.site.register(AlertThreshold)
admin.site.register(AlertThresholdRule)
admin.site.register(AlertThresholdTemplate)
