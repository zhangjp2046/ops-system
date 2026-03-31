from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import authenticate, update_session_auth_hash
from django_filters import rest_framework as filters

from .models import User
from .serializers import (
    UserSerializer, UserCreateSerializer, UserUpdateSerializer,
    LoginSerializer, ChangePasswordSerializer
)


class UserFilter(filters.FilterSet):
    """用户过滤器"""
    
    username = filters.CharFilter(lookup_expr='icontains')
    email = filters.CharFilter(lookup_expr='icontains')
    full_name = filters.CharFilter(lookup_expr='icontains')
    role = filters.CharFilter(lookup_expr='exact')
    is_active = filters.BooleanFilter()
    
    class Meta:
        model = User
        fields = ['username', 'email', 'full_name', 'role', 'is_active']


class UserViewSet(viewsets.ModelViewSet):
    """用户视图集"""
    
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = UserFilter
    
    def get_serializer_class(self):
        """根据动作选择序列化器"""
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        elif self.action == 'login':
            return LoginSerializer
        return super().get_serializer_class()
    
    @action(detail=False, methods=['post'], url_path='login')
    def login(self, request):
        """用户登录"""
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_data = serializer.save()
        return Response({
            'user': UserSerializer(user_data['user']).data,
            'message': '登录成功'
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """获取当前用户信息"""
        if not request.user.is_authenticated:
            return Response({'error': '未登录'}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put'], url_path='change-password')
    def change_password(self, request):
        """修改密码"""
        if not request.user.is_authenticated:
            return Response({'error': '未登录'}, status=status.HTTP_401_UNAUTHORIZED)
            
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']
        
        # 验证旧密码
        if not user.check_password(old_password):
            return Response(
                {'old_password': '旧密码错误'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 更新密码
        user.set_password(new_password)
        user.save()
        
        # 保持用户登录状态
        update_session_auth_hash(request, user)
        
        return Response({'message': '密码修改成功'})
    
    @action(detail=True, methods=['post'], url_path='activate')
    def activate(self, request, pk=None):
        """激活用户"""
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response({'message': '用户已激活'})
    
    @action(detail=True, methods=['post'], url_path='deactivate')
    def deactivate(self, request, pk=None):
        """禁用用户"""
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response({'message': '用户已禁用'})