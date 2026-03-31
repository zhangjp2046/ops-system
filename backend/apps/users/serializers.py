from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'full_name', 'phone',
            'avatar_url', 'role', 'is_active', 'last_login_time',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'last_login_time']


class UserCreateSerializer(serializers.ModelSerializer):
    """用户创建序列化器"""
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True, min_length=6)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'full_name', 'phone', 'role'
        ]
    
    def validate(self, data):
        """验证数据"""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({'password_confirm': '两次密码不一致'})
        return data
    
    def create(self, validated_data):
        """创建用户"""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """用户更新序列化器"""
    
    class Meta:
        model = User
        fields = ['full_name', 'phone', 'avatar_url', 'role', 'is_active']
    
    def update(self, instance, validated_data):
        """更新用户"""
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class LoginSerializer(serializers.Serializer):
    """登录序列化器"""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        """验证登录"""
        username = data.get('username')
        password = data.get('password')
        
        if username and password:
            user = authenticate(username=username, password=password)
            if user:
                if not user.is_active:
                    raise serializers.ValidationError('用户已被禁用')
                data['user'] = user
            else:
                raise serializers.ValidationError('用户名或密码错误')
        else:
            raise serializers.ValidationError('必须提供用户名和密码')
        
        return data
    
    def create(self, validated_data):
        """返回用户"""
        user = validated_data['user']
        user.update_last_login()
        return {
            'user': UserSerializer(user).data
        }


class ChangePasswordSerializer(serializers.Serializer):
    """修改密码序列化器"""
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, min_length=6, required=True)
    new_password_confirm = serializers.CharField(write_only=True, min_length=6, required=True)
    
    def validate(self, data):
        """验证密码"""
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': '两次新密码不一致'})
        return data