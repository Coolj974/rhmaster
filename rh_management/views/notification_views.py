from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.utils import timezone
from ..models import Notification

@login_required
def notifications_view(request):
    """Vue pour afficher toutes les notifications de l'utilisateur."""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    # Statistiques des notifications
    stats = {
        'total': notifications.count(),
        'unread': notifications.filter(read=False).count(),
        'leave': notifications.filter(notification_type='leave').count(),
        'expense': notifications.filter(notification_type='expense').count(),
        'km_expense': notifications.filter(notification_type='km_expense').count(),
        'system': notifications.filter(notification_type='system').count(),
    }
    
    context = {
        'notifications': notifications,
        'stats': stats
    }
    
    return render(request, 'rh_management/notifications.html', context)

@login_required
def mark_notification_read(request, notification_id):
    """Marque une notification comme lue."""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.read = True
    notification.save()
    
    # Si c'est une requête AJAX, retourner un JSON
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    
    # Sinon rediriger vers l'URL de la notification ou la page des notifications
    if notification.url:
        return redirect(notification.url)
    return redirect('notifications')

@login_required
def mark_all_read(request):
    """Marque toutes les notifications comme lues."""
    Notification.objects.filter(user=request.user, read=False).update(read=True)
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    return redirect('notifications')

@login_required
def delete_notification(request, notification_id):
    """Supprime une notification."""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.delete()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    return redirect('notifications')

@login_required
def delete_all_read(request):
    """Supprime toutes les notifications lues."""
    Notification.objects.filter(user=request.user, read=True).delete()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    return redirect('notifications')

@login_required
def get_notifications_count(request):
    """API pour obtenir le nombre de notifications non lues."""
    unread_count = Notification.objects.filter(user=request.user, read=False).count()
    return JsonResponse({'count': unread_count})

@login_required
def get_notifications_dropdown(request):
    """API pour obtenir le contenu HTML du dropdown de notifications."""
    notifications = Notification.objects.filter(user=request.user, read=False).order_by('-created_at')[:5]
    
    context = {
        'notifications': notifications,
        'unread_count': notifications.count(),
        'more_notifications': Notification.objects.filter(user=request.user).count() > 5
    }
    
    html = render_to_string('rh_management/partials/notification_dropdown.html', context, request=request)
    
    return JsonResponse({'html': html, 'count': notifications.count()})
