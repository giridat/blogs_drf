from django.urls import path
from .views import (
    login_user,
    logout_user,
    register_user,
    user_profile,
    verify_login_otp,
    verify_registration_otp,
    create_blog,
    get_all_blogs,
    blog_detail,
    add_comment,
    list_comments,
    edit_comment,
    delete_comment,
    public_profile_view
)

urlpatterns = [
    # Authentication & OTP
    path('login/send-otp/', login_user, name='login_user'),
    path('login/verify-otp/', verify_login_otp, name='verify_login_otp'),
    path('register/send-otp/', register_user, name='register_user'),
    path('register/verify-otp/', verify_registration_otp, name='verify_otp'),
    path('profile/', user_profile, name='user_profile'),
    path('users/<int:user_id>/profile/', public_profile_view, name='public_profile'),
    path('logout/', logout_user, name='logout_user'),

    # Blog Endpoints
    path('blogs/', get_all_blogs, name='list_blogs'),
    path('blogs/create/', create_blog, name='create_blog'),
    path('blogs/<int:blog_id>/', blog_detail, name='blog_detail'),

    # Comment Endpoints
    path('blogs/<int:blog_id>/comments/', list_comments, name='list_comments'),
    path('blogs/<int:blog_id>/comments/add/', add_comment, name='add_comment'),
    path('blogs/<int:blog_id>/comments/<int:comment_id>/edit/', edit_comment, name='edit_comment'),
    path('blogs/<int:blog_id>/comments/<int:comment_id>/delete/', delete_comment, name='delete_comment'),
]
