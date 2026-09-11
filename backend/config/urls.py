from django.urls import path
from django.http import JsonResponse
from accounts.views import SessionView,LoginView,LogoutView
from coding_tasks.views import RepositoryList,TaskList,TaskDetail,TaskAction,ToolDetail
urlpatterns=[
 path('health/',lambda r:JsonResponse({'status':'ok','service':'repopilot-api'})),
 path('api/auth/session/',SessionView.as_view()),path('api/auth/login/',LoginView.as_view()),path('api/auth/logout/',LogoutView.as_view()),
 path('api/repositories/',RepositoryList.as_view()),path('api/tasks/',TaskList.as_view()),
 path('api/tasks/<uuid:pk>/',TaskDetail.as_view()),path('api/tasks/<uuid:pk>/<str:action>/',TaskAction.as_view()),
 path('api/tasks/<uuid:pk>/tools/<int:tool_id>/',ToolDetail.as_view())
]
