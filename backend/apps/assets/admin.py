from django.contrib import admin
from .models import AssetType, AssetField, Asset, AssetData, AssetStatusHistory

admin.site.register(AssetType)
admin.site.register(AssetField)
admin.site.register(Asset)
admin.site.register(AssetData)
admin.site.register(AssetStatusHistory)
