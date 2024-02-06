from rest_framework import serializers
from .models import User, Connection, Message


class SignUpSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "password", "first_name", "last_name", "thumbnail"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        username = validated_data["username"].lower()
        first_name = validated_data["first_name"].lower()
        last_name = validated_data["last_name"].lower()

        user = User.objects.create_user(
            username=username, first_name=first_name, last_name=last_name
        )
        user.set_password(validated_data["password"])
        user.save()

        return user


class UserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "name", "thumbnail"]

    def get_name(self, obj):
        fname = obj.first_name.capitalize()
        lname = obj.last_name.capitalize()
        return f"{fname} {lname}"


class SearchSerializer(UserSerializer):
    status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "name", "thumbnail", "status"]

    def get_status(self, obj):
        if obj.pending_them:
            return "pending-them"
        elif obj.pending_me:
            return "pending-me"
        elif obj.connected:
            return "connected"

        return "no-connection"


class RequestSerializer(serializers.ModelSerializer):
    sender = UserSerializer()
    receiver = UserSerializer()

    class Meta:
        model = Connection
        fields = ["id", "sender", "receiver", "created", "updated"]


class FriendSerializer(serializers.ModelSerializer):
    friend = serializers.SerializerMethodField()
    preview = serializers.SerializerMethodField()
    updated = serializers.SerializerMethodField()

    class Meta:
        model = Connection
        fields = ["id", "friend", "preview", "updated"]

    def get_friend(self, obj):
        # If the current user is the sender
        if self.context["user"] == obj.sender:
            return UserSerializer(obj.receiver).data
        # If the current user is the receiver
        elif self.context["user"] == obj.receiver:
            return UserSerializer(obj.sender).data
        else:
            print("Error: User is not part of the connection")

    def get_preview(self, obj):
        default = "New connection"
        if not hasattr(obj, "latest_text"):
            return default
        return obj.latest_text or default

    def get_updated(self, obj):
        if not hasattr(obj, "latest_created"):
            date = obj.updated
        else:
            date = obj.latest_created or obj.updated
        return date.isoformat()


class MessageSerializer(serializers.ModelSerializer):
    is_me = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ["id", "is_me", "text", "created"]

    def get_is_me(self, obj):
        return obj.user == self.context["user"]
