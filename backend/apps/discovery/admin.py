from django.contrib import admin
from .models import DiscoveryTask, DiscoveredDevice, TopologyNode, TopologyEdge

admin.site.register(DiscoveryTask)
admin.site.register(DiscoveredDevice)
admin.site.register(TopologyNode)
admin.site.register(TopologyEdge)
