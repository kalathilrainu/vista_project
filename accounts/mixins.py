from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect
from django.contrib import messages

class AdminRequiredMixin(AccessMixin):
    """Verify that the current user has ADMIN or SUPER_ADMIN role."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
            
        if request.user.role not in ['ADMIN', 'SUPER_ADMIN']:
            messages.error(request, "You do not have permission to access this page.")
            return redirect('landing')  # Or any other appropriate redirect
            
        return super().dispatch(request, *args, **kwargs)
