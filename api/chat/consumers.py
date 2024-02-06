import json
import base64
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from django.core.files.base import ContentFile
from .serializers import UserSerializer


class ChatConsumer(WebsocketConsumer):

    def connect(self):
        user = self.scope["user"]

        if not user.is_authenticated:
            self.close()
            return

        self.username = user.username
        # Join the user to a group with their username
        async_to_sync(self.channel_layer.group_add)(self.username, self.channel_name)

        self.accept()

    def disconnect(self, close_code):
        # Leave the group
        async_to_sync(self.channel_layer.group_discard)(
            self.username, self.channel_name
        )

    # Handle requests

    def receive(self, text_data):
        # Recive message from WebSocket
        data = json.loads(text_data)
        data_source = data["source"]

        print("receive", json.dumps(data, indent=2))

        # Thumbnail upload
        if data_source == "thumbnail":
            self.receive_thumbnail(data)

    def receive_thumbnail(self, data):
        user = self.scope["user"]
        # Convert base64 to dgango content file
        img_str = data.get("base64")
        image = ContentFile(base64.b64decode(img_str))
        # Update user thumbnail
        filename = data.get("filename")
        user.thumbnail.save(filename, image, save=True)
        # Serialize user
        serialized = UserSerializer(user)
        # Send serialized user to the group
        self.send_group(self.username, "thumbnail", serialized.data)

    # Catch/all broadcast to client helpers

    def send_group(self, group, source, data):
        response = {"type": "broadcast_group", "source": source, "data": data}

        async_to_sync(self.channel_layer.group_send)(group, response)

    def broadcast_group(self, data):
        data.pop("type")
        self.send(text_data=json.dumps(data))
