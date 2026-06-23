from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

User = get_user_model()

class PhoneOrUserIdBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        # We will receive the login identifier in the 'username' kwarg from Django's built-in forms/auth,
        # or we might receive it explicitly.
        identifier = username or kwargs.get('user_id') or kwargs.get('phone')
        
        if not identifier:
            return None

        try:
            # Check if user exists by user_id OR phone OR username
            user = User.objects.get(Q(user_id=identifier) | Q(phone=identifier) | Q(username=identifier))
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        except User.DoesNotExist:
            return None
        except User.MultipleObjectsReturned:
            # Unlikely for user_id (unique), but phone might not be unique.
            # In case of multiple, we can just grab the first one or fail. 
            # It's safer to grab the first one that matches the password.
            users = User.objects.filter(Q(user_id=identifier) | Q(phone=identifier) | Q(username=identifier))
            for user in users:
                if user.check_password(password) and self.user_can_authenticate(user):
                    return user
        return None
