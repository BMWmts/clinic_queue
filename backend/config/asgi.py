"""
ASGI entrypoint — รองรับทั้ง HTTP (REST API) และ WebSocket (queue dashboard realtime)
"""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# ต้องเรียก get_asgi_application() ก่อน import consumer เพื่อให้ app registry พร้อมใช้งาน
django_asgi_application = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402

from apps.common.websocket_auth import JWTAuthMiddleware  # noqa: E402
from apps.queue.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_application,
        "websocket": JWTAuthMiddleware(URLRouter(websocket_urlpatterns)),
    }
)
