from .helpers import get_unread_notification_count

def notification_context(request):
    """
    Context processor to add unread notification count to all templates
    """
    context = {'unread_count': 0}
    
    if request.user.is_authenticated and hasattr(request, 'session'):
        user_id = request.session.get('user_id')
        role = request.session.get('role')
        
        if user_id and role:
            context['unread_count'] = getattr(request, 'unread_count', 0)
    
    return context
