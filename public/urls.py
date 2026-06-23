from django.urls import path
from . import views

app_name = 'public'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('courses/', views.all_courses_view, name='courses'),
    path('free-courses/', views.free_courses_view, name='free_courses'),
    path('about/', views.about_view, name='about'),
    path('shop/', views.shop_view, name='shop'),
    path('course/<int:course_id>/', views.course_detail_view, name='course_detail'),
    path('enroll/<int:course_id>/', views.enroll_course_view, name='enroll_course'),
]
