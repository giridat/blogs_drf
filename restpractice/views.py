import random
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.views import TokenObtainPairView
from django.db.models import Q
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from django.contrib.sessions.backends.db import SessionStore


from .models import DefaultUser, AuthUser, Blog, Comment, Profile
from .serializer import (ProfileSerializer, UserSerializer, UserRegisterSerializer, CommentSerialzer,
                         OTPVerificationSerializer, BlogSerializer,AuthUserSerializer)
                         

User = get_user_model()
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_user(request):
    refresh_token = request.data.get("refresh")

    if not refresh_token:
        return Response({"message": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({"message": "User logged out successfully."}, status=status.HTTP_205_RESET_CONTENT)
    except TokenError as e:
        return Response({"message": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)
@api_view(['POST'])
def login_user(request):
    identifier = request.data.get("email") or request.data.get("phone")
    if not identifier:
        return Response({"message": "Email or phone is required."}, status=400)

    try:
        user = AuthUser.objects.get(email=identifier) if "@" in identifier else AuthUser.objects.get(phone=identifier)
    except AuthUser.DoesNotExist:
        return Response({"message": "User not found. Please register."}, status=404)

    try:
        otp = user.generate_otp()
    except Exception as e:
        return Response({"message": str(e)}, status=429)

    # Create session to track OTP and identifier
    session = SessionStore()
    session["otp"] = otp
    session["identifier"] = identifier
    session["user_id"] = user.id
    session.create()

    # Simulate sending OTP
    print(f"[OTP Sent for Login] {identifier}: {otp}")

    return Response({
        "message": "OTP sent successfully for login",
        "otp": otp,
        "session_id": session.session_key  # Client uses this to verify
    }, status=200)


@api_view(['POST'])
def register_user(request):
    serializer = UserRegisterSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data.get("email")
        phone = serializer.validated_data.get("phone")

        identifier = email or phone
        user = AuthUser.objects.filter(email=email) if email else AuthUser.objects.filter(phone=phone)

        if user.exists():
            return Response({"message": "User already exists. Please log in instead."}, status=400)

        # Temporarily create user for OTP generation
        user = AuthUser(email=email, phone=phone)
        try:
            otp = user.generate_otp()
        except Exception as e:
            return Response({"message": str(e)}, status=429)

        user.save()

        # Create a session
        session = SessionStore()
        session["identifier"] = identifier
        session["user_id"] = user.id
        session.create()

        # Simulate sending OTP
        print(f"[OTP Sent] {identifier}: {otp}")

        return Response({
            "message": "OTP sent successfully",
            'otp': otp,
            "session_id": session.session_key
        })

    return Response(serializer.errors, status=400)
@api_view(['POST'])
def verify_login_otp(request):
    session_id = request.data.get("session_id")
    otp_input = request.data.get("otp")

    if not session_id or not otp_input:
        return Response({"message": "Session ID and OTP are required."}, status=400)

    # Load session
    session = SessionStore(session_key=session_id)
    if not session or not session.get("otp") or not session.get("user_id"):
        return Response({"message": "Invalid or expired session."}, status=400)

    try:
        user = AuthUser.objects.get(id=session["user_id"])
    except AuthUser.DoesNotExist:
        return Response({"message": "User not found."}, status=404)

    if session["otp"] != otp_input:
        # Optionally increase failed attempts here if you want (advanced)
        return Response({"message": "Incorrect OTP."}, status=400)

    # OTP matched — clean up session and return tokens
    user.otp_verified = True
    user.otp = None
    user.otp_failed_attempts = 0
    user.save()

    # Clean session
    session.flush()

    tokens = user.get_tokens_for_user()
    serialized_user = AuthUserSerializer(user)

    return Response({
        "message": "OTP verified successfully.",
        "user": serialized_user.data,
        "access": tokens["access"],
        "refresh": tokens["refresh"]
    }, status=200)


@api_view(['POST'])
def verify_registration_otp(request):
    session_id = request.data.get("session_id")
    otp_input = request.data.get("otp")

    if not session_id or not otp_input:
        return Response({"message": "Session ID and OTP are required."}, status=400)

    session = SessionStore(session_key=session_id)
    if not session.exists(session.session_key):
        return Response({"message": "Invalid or expired session."}, status=400)

    user_id = session.get("user_id")
    try:
        user = AuthUser.objects.get(id=user_id)
    except AuthUser.DoesNotExist:
        return Response({"message": "User not found."}, status=404)

    success, message = user.verify_otp(otp_input)

    if not success:
        return Response({"message": message}, status=400)

    tokens = user.get_tokens_for_user()
    serialized_user = AuthUserSerializer(user)

    Profile.create_or_update(user)


    return Response({
        "message": message,
        "user": serialized_user.data,
        "access": tokens["access"],
        "refresh": tokens["refresh"]
    })


@api_view(['GET'])
def get_users(request):
    return Response(UserSerializer(DefaultUser.objects.all(), many=True).data)


@api_view(['POST'])
def create_user(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
def user_detail(request, pk):

    try:
        user = DefaultUser.objects.get(pk=pk)
    except DefaultUser.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = UserSerializer(user)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = UserSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
@api_view(['GET'])
@permission_classes([])  # Publicly accessible
def public_profile_view(request, user_id):
    try:
        user = AuthUser.objects.get(id=user_id)
        profile = user.profile
        serializer = ProfileSerializer(profile)
        return Response(serializer.data)
    except AuthUser.DoesNotExist:
        return Response({"message": "User not found."}, status=404)
   

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    profile = request.user.profile

    if request.method == 'GET':
        serializer = ProfileSerializer(profile)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_all_blogs(request):
    blogs = Blog.objects.all()
    serializer = BlogSerializer(blogs, many=True)
    return Response(serializer.data)


@api_view(['Post'])
@permission_classes([IsAuthenticated])
def create_blog(request):
    serializer = BlogSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(author=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def blog_detail(request, blog_id):
    try:
        blog = Blog.objects.get(id=blog_id)
    except Blog.DoesNotExist:
        return Response({"status": False, "message": "Blog not found"}, status=status.HTTP_404_NOT_FOUND)

    serializer = BlogSerializer(blog)
    return Response(serializer.data)


@api_view(['GET'])
def list_comments(request, blog_id):
    try:
        blog = Blog.objects.get(id=blog_id)
    except Blog.DoesNotExist:
        return Response({"status": False, "message": "Blog not found"}, status=status.HTTP_404_NOT_FOUND)

    comments = Comment.objects.filter(blog=blog)
    serializer = CommentSerialzer(comments, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_comment(request, blog_id):
    try:
        blog = Blog.objects.get(id=blog_id)
    except Blog.DoesNotExist:
        return Response({"status": False, "message": "Blog not found"}, status=status.HTTP_404_NOT_FOUND)

    # Check if content is provided in the request
    if 'content' not in request.data:
        return Response({"status": False, "message": "'content' is required to add a comment"}, status=status.HTTP_400_BAD_REQUEST)

    # Check if it's a reply to an existing comment
    parent_comment = None
    if 'parent' in request.data:
        try:
            parent_comment = Comment.objects.get(id=request.data['parent'])
        except Comment.DoesNotExist:
            return Response({"status": False, "message": "Parent comment not found"}, status=status.HTTP_404_NOT_FOUND)

    # Create the comment (either a top-level comment or a reply)
    comment = Comment.objects.create(
        blog=blog,
        user=request.user,  # Ensure the logged-in user is the one adding the comment
        content=request.data['content'],
        parent=parent_comment  # This will link the comment to its parent if it's a reply
    )

    # Serialize the comment and return it in the response
    serializer = CommentSerialzer(comment)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def edit_comment(request, blog_id, comment_id):
    try:
        blog = Blog.objects.get(id=blog_id)
    except Blog.DoesNotExist:
        return Response({"status": False, "message": "Blog not found"}, status=status.HTTP_404_NOT_FOUND)

    try:
        comment = Comment.objects.get(id=comment_id)
    except Comment.DoesNotExist:
        return Response({"status": False, "message": "Comment not found"}, status=status.HTTP_404_NOT_FOUND)

    if comment.user != request.user:
        return Response({"status": False, "message": "You are not authorized to edit this comment"}, status=status.HTTP_403_FORBIDDEN)

    serializer = CommentSerialzer(comment, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_comment(request, blog_id, comment_id):
    try:
        blog = Blog.objects.get(id=blog_id)
    except Blog.DoesNotExist:
        return Response({"status": False, "message": "Blog not found"}, status=status.HTTP_404_NOT_FOUND)

    try:
        comment = Comment.objects.get(id=comment_id)
    except Comment.DoesNotExist:
        return Response({"status": False, "message": "Comment not found"}, status=status.HTTP_404_NOT_FOUND)

    if comment.user != request.user:
        return Response({"status": False, "message": "You are not authorized to delete this comment"}, status=status.HTTP_403_FORBIDDEN)

    comment.delete()
    return Response({"status": True, "message": "Comment deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
