from django.urls import path
from . import views

app_name = 'live'

urlpatterns = [
    path('comments/<int:node_id>/', views.get_comments, name='get_comments'),
]

