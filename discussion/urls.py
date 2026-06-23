from django.urls import path
from . import views

app_name = 'discussion'

urlpatterns = [
    path('', views.discussion_list, name='discussion_list'),
    path('<int:course_id>/', views.discussion_view, name='discussion_group'),
    path('<int:course_id>/send/', views.send_message, name='send_message'),
    path('<int:course_id>/upload/', views.upload_attachment, name='upload_attachment'),
]
