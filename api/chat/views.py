from django.contrib.auth import authenticate
from django.shortcuts import render
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserSerializer, SignUpSerializer

# Create your views here.


def get_auth_for_user(user):
    refresh = RefreshToken.for_user(user)

    return {
        "user": UserSerializer(user).data,
        "tokens": {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        },
    }


class SignInView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        if not username or not password:
            return Response(
                {"error": "Please provide both username and password"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(username=username, password=password)

        if not user:
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        user_data = get_auth_for_user(user)

        return Response(user_data, status=status.HTTP_200_OK)


class SignUpView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        new_user = SignUpSerializer(data=request.data)
        new_user.is_valid(raise_exception=True)
        user = new_user.save()

        user_data = get_auth_for_user(user)

        return Response(user_data, status=status.HTTP_200_OK)
