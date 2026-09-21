from django.contrib import admin
from .models import (
    InspectionPlan, InspectionTask, InspectionResult,
    InspectionRecord, InspectionTemplate, Inspection, InspectionItem
)

admin.site.register(InspectionPlan)
admin.site.register(InspectionTask)
admin.site.register(InspectionResult)
admin.site.register(InspectionRecord)
admin.site.register(InspectionTemplate)
admin.site.register(Inspection)
admin.site.register(InspectionItem)
