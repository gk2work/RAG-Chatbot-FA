# app/utils/__init__.py
"""
Utilities package for the university chatbot application
"""

from .rbac import (
    Roles,
    require_auth,
    require_role,
    require_superadmin,
    require_admin_or_above,
    require_student_or_above,
    require_university_access,
    filter_by_university_access,
    is_superadmin,
    is_admin_or_above,
    get_user_permissions
)

__all__ = [
    'Roles',
    'require_auth',
    'require_role', 
    'require_superadmin',
    'require_admin_or_above',
    'require_student_or_above',
    'require_university_access',
    'filter_by_university_access',
    'is_superadmin',
    'is_admin_or_above',
    'get_user_permissions'
]