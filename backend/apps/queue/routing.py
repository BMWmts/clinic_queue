"""WebSocket routing ของหน้าจอคิว"""
from django.urls import path

from apps.queue.consumers import QueueConsumer

websocket_urlpatterns = [
    path("ws/queue/<int:clinic_id>/", QueueConsumer.as_asgi()),
]
