from rest_framework.permissions import BasePermission

class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return (
            user.is_authenticated and
            getattr(user, "role", None) == "superadmin"
        )



class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return request.user.role in ["admin", "superadmin"]