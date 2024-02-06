import json
import base64
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from django.core.files.base import ContentFile
from django.db.models import Q, Exists, OuterRef

from .models import User, Connection
from .serializers import (
    UserSerializer,
    SearchSerializer,
    RequestSerializer,
    FriendSerializer,
)


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

        # Get friend list
        if data_source == "friend.list":
            self.receive_friend_list(data)

        # Accept friend request
        elif data_source == "request.accept":
            self.receive_request_accept(data)

        # Make friend request
        elif data_source == "request.connect":
            self.receive_request_connect(data)

        # Get request list
        elif data_source == "request.list":
            self.receive_request_list(data)

        # Search / filter users
        elif data_source == "search":
            self.recive_search(data)

        # Thumbnail upload
        elif data_source == "thumbnail":
            self.receive_thumbnail(data)

    def receive_friend_list(self, data):
        user = self.scope["user"]
        # Get all accepted connections for the user
        connections = Connection.objects.filter(
            Q(sender=user) | Q(receiver=user), accepted=True
        )
        # Serialize connections
        serialized = FriendSerializer(connections, context={"user": user}, many=True)
        # Send friend list back to user
        self.send_group(user.username, "friend.list", serialized.data)

    def receive_request_accept(self, data):
        username = data.get("username")
        # Attempt to fetch the connection object
        try:
            connection = Connection.objects.get(
                sender__username=username, receiver=self.scope["user"]
            )
        except Connection.DoesNotExist:
            print("Error: Connection does not exist")
            return
        # Update the connection
        connection.accepted = True
        connection.save()
        # Serialize connection
        serialized = RequestSerializer(connection)
        # Send accepted request to the sender and receiver
        self.send_group(connection.sender.username, "request.accept", serialized.data)
        self.send_group(connection.receiver.username, "request.accept", serialized.data)

    def receive_request_connect(self, data):
        username = data.get("username")
        # Attempt to fetch the recipient user
        try:
            receiver = User.objects.get(username=username)
        except User.DoesNotExist:
            print("Error: User does not exist")
            return
        # Create connection
        connection, _ = Connection.objects.get_or_create(
            sender=self.scope["user"], receiver=receiver
        )
        # Serialize connection
        serialized = RequestSerializer(connection)
        # Send back to sender
        self.send_group(connection.sender.username, "request.connect", serialized.data)
        # Send to receiver
        self.send_group(
            connection.receiver.username, "request.connect", serialized.data
        )

    def receive_request_list(self, data):
        user = self.scope["user"]
        # Get all connections for the user
        connections = Connection.objects.filter(receiver=user, accepted=False)
        # Serialize connections
        serialized = RequestSerializer(connections, many=True)
        # Send request list back to user
        self.send_group(user.username, "request.list", serialized.data)

    def recive_search(self, data):
        query = data.get("query")
        # Get users from query search term
        users = (
            User.objects.filter(
                Q(username__istartswith=query)
                | Q(first_name__istartswith=query)
                | Q(last_name__istartswith=query)
            )
            .exclude(username=self.username)
            .annotate(
                pending_them=Exists(
                    Connection.objects.filter(
                        sender=self.scope["user"],
                        receiver=OuterRef("id"),
                        accepted=False,
                    )
                ),
                pending_me=Exists(
                    Connection.objects.filter(
                        sender=OuterRef("id"),
                        receiver=self.scope["user"],
                        accepted=False,
                    )
                ),
                connected=Exists(
                    Connection.objects.filter(
                        Q(sender=self.scope["user"], receiver=OuterRef("id"))
                        | Q(sender=OuterRef("id"), receiver=self.scope["user"]),
                        accepted=True,
                    )
                ),
            )
        )

        # Serialize results
        serialized = SearchSerializer(users, many=True)
        # Send the results back to the user
        self.send_group(self.username, "search", serialized.data)

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
