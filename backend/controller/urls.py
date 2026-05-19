"""
Controller layer — URL routing.
Maps incoming requests to the appropriate view functions.
"""
from django.urls import path
from backend.view import views

app_name = 'streaming'

urlpatterns = [
    # Browse
    path('', views.home, name='home'),

    # Upload
    path('upload/', views.upload_video, name='upload'),

    # Video player & streaming
    path('watch/<uuid:video_id>/', views.watch, name='watch'),
    path('stream/<uuid:video_id>/', views.stream_video, name='stream'),

    # Reactions
    path('like/<uuid:video_id>/', views.toggle_like, name='like'),
    path('dislike/<uuid:video_id>/', views.toggle_dislike, name='dislike'),

    # Comments
    path('comment/<uuid:video_id>/', views.add_comment, name='add_comment'),
    path('comment/delete/<uuid:comment_id>/', views.delete_comment, name='delete_comment'),

    # Auth
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]
