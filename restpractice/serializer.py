from rest_framework import serializers
from restpractice.models import DefaultUser, Blog, Comment, Profile
from django.contrib.auth import get_user_model

AuthUser = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = DefaultUser
        fields = '__all__'


class UserRegisterSerializer(serializers.ModelSerializer):

    class Meta:
        model = AuthUser
        fields = ['email', 'phone']

    def validate(self, data):
        # Ensure at least one of email or phone is provided
        if not data.get('email') and not data.get('phone'):
            raise serializers.ValidationError("Either email or phone must be provided.")
        return data

    def create(self, validated_data):
        # Create the user instance
        user = AuthUser.objects.create(**validated_data)
        return user

# serializers.py

class OTPVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False)
    otp = serializers.CharField()
    session_id = serializers.CharField()

    def validate(self, data):
        email = data.get("email")
        phone = data.get("phone")

        if (email and phone) or (not email and not phone):
            raise serializers.ValidationError("Provide either email or phone, not both.")

        return data



class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['id', 'bio', 'profile_image', 'website', 'location', 'is_author', 'joined_on']
        read_only_fields = ['id', 'joined_on']
class AuthUserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = AuthUser
        fields = ['id', 'email', 'phone', 'otp_verified', 'profile']

class BlogSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Blog
        fields = '__all__'

class CommentSerialzer(serializers.ModelSerializer):
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = '__all__'

    def getReplies(self,obj):
        replies = obj.replies.all()
        return CommentSerialzer(replies, many=True).data if replies else []    