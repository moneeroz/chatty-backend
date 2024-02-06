from rest_framework import serializers
from .models import User


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
