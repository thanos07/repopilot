from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

class SessionView(APIView):
    permission_classes=[AllowAny]
    def get(self,request):return Response({'username':request.user.username if request.user.is_authenticated else '', 'can_operate':bool(request.user.is_authenticated and request.user.is_active and request.user.is_staff), 'csrf_token':get_token(request)})

@method_decorator(csrf_protect,name='dispatch')
class LoginView(APIView):
    permission_classes=[AllowAny]
    throttle_classes=[ScopedRateThrottle]
    throttle_scope='login'
    def post(self,request):
        user=authenticate(request,username=request.data.get('username'),password=request.data.get('password'))
        if user is None:return Response({'detail':'Invalid username or password.'},status=400)
        login(request,user)
        return Response({'username':user.username,'can_operate':bool(request.user.is_authenticated and request.user.is_active and request.user.is_staff), 'csrf_token':get_token(request)})

class LogoutView(APIView):
    def post(self,request):
        logout(request)
        return Response({'detail':'Signed out.'})
