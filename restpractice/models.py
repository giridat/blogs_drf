from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
import random
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from datetime import timedelta


class DefaultUser(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    age = models.IntegerField()

    def __str__(self):
        return self.name


class CustomUserManager(BaseUserManager):
    def create_user(self, email=None, phone=None, password=None, **extra_fields):
        if not email and not phone:
            raise ValueError('Users must have either an email address or a phone number')

        if email:
            email = self.normalize_email(email)

        user = self.model(email=email, phone=phone, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email=None, phone=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, phone, password, **extra_fields)


class AuthUser(AbstractBaseUser, PermissionsMixin):
    id = models.AutoField(primary_key=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    phone = models.CharField(max_length=15, unique=True, blank=True, null=True)
    first_name = models.CharField(max_length=30, default="")
    last_name = models.CharField(max_length=30, default="")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    otp = models.CharField(max_length=6, null=True, blank=True)
    otp_verified = models.BooleanField(default=False)
    otp_created_at = models.DateTimeField(null=True, blank=True)
    otp_last_requested = models.DateTimeField(null=True, blank=True)
    otp_failed_attempts = models.IntegerField(default=0)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['phone']

    def generate_otp(self):
        now = timezone.now()

        if self.otp_last_requested and now - self.otp_last_requested < timedelta(seconds=30):
            raise Exception("OTP was requested recently. Please wait.")

        self.otp = str(random.randint(100000, 999999))
        self.otp_created_at = now
        self.otp_failed_attempts = 0
        self.otp_last_requested = now
        self.save()
        return self.otp

    def verify_otp(self, otp_input):
        now = timezone.now()

        if not self.otp or not self.otp_created_at:
            return False, "No OTP generated."

        if now - self.otp_created_at > timedelta(minutes=2):
            self.otp = None
            self.save()
            return False, "OTP expired."

        if self.otp_failed_attempts >= 3:
            return False, "Too many incorrect attempts. Try again later."

        if self.otp == otp_input:
            self.otp_verified = True
            self.otp = None
            self.otp_failed_attempts = 0
            self.save()
            return True, "OTP verified successfully."

        self.otp_failed_attempts += 1
        self.save()
        return False, "Incorrect OTP."

    def get_tokens_for_user(self):
        refresh = RefreshToken.for_user(self)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.__class__.objects.normalize_email(self.email)
        super().save(*args, **kwargs)

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

    def __str__(self):
        return self.email or self.phone or "Anonymous User"
class Profile(models.Model):
    user = models.OneToOneField(AuthUser, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True, null=True)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    is_author = models.BooleanField(default=False)
    joined_on = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile of {self.user}"

    @classmethod
    def create_or_update(cls, user, **kwargs):
        profile, created = cls.objects.get_or_create(user=user)
        for key, value in kwargs.items():
            setattr(profile, key, value)
        profile.save()
        return profile    


class Blog(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()
    author = models.ForeignKey(
        AuthUser, on_delete=models.CASCADE, related_name="authored_blogs"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Comment(models.Model):
    blog = models.ForeignKey(
        Blog, related_name="comments", on_delete=models.CASCADE
    )
    user = models.ForeignKey(AuthUser, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        related_name='replies',
        on_delete=models.CASCADE
    )

    def __str__(self):
        return f"Comment by {self.user} on {self.blog.title}"
