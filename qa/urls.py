from django.urls import path
from . import views

app_name = 'qa'

urlpatterns = [
    # Student
    path('qa/',                          views.qa_list_view,    name='qa_list'),
    path('qa/ask/',                      views.qa_ask_view,     name='qa_ask'),
    path('qa/choice/<int:q_id>/',        views.qa_choice_view,  name='qa_choice'),
    path('qa/submit/',                   views.qa_submit_view,  name='qa_submit'),
    path('qa/thread/<int:q_id>/',        views.qa_thread_view,  name='qa_thread'),

    # Teacher
    path('teacher/qa/',                          views.teacher_qa_list_view,  name='teacher_qa_list'),
    path('teacher/qa/<int:q_id>/reply/',         views.teacher_qa_reply_view, name='teacher_qa_reply'),
]
