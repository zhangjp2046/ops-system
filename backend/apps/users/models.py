from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


class UserManager(BaseUserManager):
    """自定义用户管理器"""
    
    def create_user(self, username, email, password=None, **extra_fields):
        """创建普通用户"""
        if not email:
            raise ValueError('用户必须提供邮箱')
        if not username:
            raise ValueError('用户必须提供用户名')
        
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, username, email, password=None, **extra_fields):
        """创建超级用户"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('超级用户必须设置 is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('超级用户必须设置 is_superuser=True')
        
        return self.create_user(username, email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """自定义用户模型"""
    
    username = models.CharField('用户名', max_length=50, unique=True)
    email = models.EmailField('邮箱', max_length=100, unique=True)
    
    # 个人信息
    full_name = models.CharField('姓名', max_length=100, blank=True)
    phone = models.CharField('电话', max_length=20, blank=True)
    avatar_url = models.URLField('头像', max_length=500, blank=True)
    
    # 权限信息
    role = models.CharField('角色', max_length=50, default='USER')
    permissions = models.JSONField('权限列表', default=dict, blank=True)
    
    # 状态信息
    is_active = models.BooleanField('是否激活', default=True)
    is_staff = models.BooleanField('是否员工', default=False)
    is_superuser = models.BooleanField('是否超级用户', default=False)
    last_login_time = models.DateTimeField('最后登录时间', null=True, blank=True)
    
    # 时间戳
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']
    
    class Meta:
        db_table = 'users'
        verbose_name = '用户'
        verbose_name_plural = '用户管理'
    
    def __str__(self):
        return f'{self.username} ({self.full_name or self.email})'
    
    def update_last_login(self):
        """更新最后登录时间"""
        self.last_login_time = timezone.now()
        self.save(update_fields=['last_login_time'])