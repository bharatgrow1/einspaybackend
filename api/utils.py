from django.db.models import Q
from users.models import User


def get_all_child_users(user):
    role = user.role

    if role == "superadmin":
        return User.objects.all()

    if role == "admin":
        return User.objects.filter(
            Q(created_by=user) |
            Q(created_by__created_by=user) |
            Q(created_by__created_by__created_by=user) |
            Q(id=user.id)
        )

    if role == "master":
        return User.objects.filter(
            Q(created_by=user) |
            Q(created_by__created_by=user) |
            Q(id=user.id)
        )

    if role == "dealer":
        return User.objects.filter(
            Q(created_by=user) |
            Q(id=user.id)
        )

    return User.objects.filter(id=user.id)
