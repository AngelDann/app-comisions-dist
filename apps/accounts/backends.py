"""Autenticación por correo electrónico (campo ``username`` del formulario = email)."""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailAuthBackend(ModelBackend):
    """Autentica comparando la contraseña con el usuario cuyo email coincide (sin distinguir mayúsculas)."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
        email = username.strip()
        if not email:
            return None
        UserModel = get_user_model()
        qs = UserModel.objects.filter(email__iexact=email)
        if qs.count() != 1:
            return None
        user = qs.first()
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
