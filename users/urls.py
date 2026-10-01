from django.urls import path

from .views import UserListView, dashboard_view, login_otp_view, login_view, logout_view, password_reset_view, profile_view, register_view, send_otp_view, verify_otp_view

urlpatterns = [
    path('', login_view, name='login'),
    path('login/otp/', login_otp_view, name='login-otp'),
    path('logout/', logout_view, name='logout'),
    path('password-reset/', password_reset_view, name='password-reset'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('profile/', profile_view, name='profile'),
    path('register/', register_view, name='register'),
    path('register/send-otp/', send_otp_view, name='send-otp'),
    path('register/verify-otp/', verify_otp_view, name='verify-otp'),
    path('api/users/', UserListView.as_view(), name='user-list'),
]
