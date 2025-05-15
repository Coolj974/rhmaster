from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from django.contrib import messages
from ..models import Notification

@login_required
def get_notifications(request):
    """
    Vue API pour récupérer les notifications de l'utilisateur connecté
    Utilisée par AJAX pour mettre à jour le dropdown de notifications
    """
    try:
        # Récupérer les notifications non lues (limitées à 5)
        unread_notifications = Notification.objects.filter(
            user=request.user,
            read=False
        ).order_by('-created_at')[:5]
        
        # Récupérer toutes les notifications (limitées à 15)
        all_notifications = Notification.objects.filter(
            user=request.user
        ).order_by('-created_at')[:15]
        
        # Compter le total de notifications non lues
        unread_count = Notification.objects.filter(
            user=request.user,
            read=False
        ).count()
        
        # Formater les données pour le client
        notifications_data = []
        for notification in all_notifications:
            notifications_data.append({
                'id': notification.id,
                'title': notification.title,
                'message': notification.message,
                'icon': notification.icon or 'fa-bell',
                'color': notification.color or 'primary',
                'url': notification.url,
                'created_at': notification.created_at.strftime('%d/%m/%Y %H:%M'),
                'read': notification.read,
                'time_since': _get_time_since(notification.created_at)
            })
        
        return JsonResponse({
            'success': True,
            'unread_count': unread_count,
            'notifications': notifications_data
        })
    except Exception as e:
        # Gérer les erreurs et renvoyer une réponse appropriée
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
def get_notifications_dropdown(request):
    """
    Vue API pour récupérer les notifications pour le dropdown de navigation
    Version simplifiée de get_notifications avec un format spécifique pour l'interface dropdown
    """
    # Récupérer les notifications (limitées à 10)
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:10]
    
    # Compter le total de notifications non lues
    unread_count = Notification.objects.filter(
        user=request.user,
        read=False
    ).count()
    
    # Vérifier s'il y a plus de notifications que celles affichées
    more_notifications = Notification.objects.filter(
        user=request.user
    ).count() > 10
    
    # Préparer le contexte pour le template
    context = {
        'notifications': notifications,
        'unread_count': unread_count,
        'more_notifications': more_notifications
    }
    
    # Rendre le HTML du dropdown
    from django.template.loader import render_to_string
    html = render_to_string('rh_management/notification_dropdown.html', context)
    
    return JsonResponse({
        'count': unread_count,
        'html': html
    })

@login_required
def mark_notification_as_read(request, notification_id):
    """
    Marque une notification spécifique comme lue
    """
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    
    if not notification.read:
        notification.read = True
        notification.save()
    
    # Rediriger vers l'URL associée à la notification ou vers le tableau de bord
    redirect_url = notification.url if notification.url else 'dashboard'
    return redirect(redirect_url)

@login_required
def mark_notification_read(request, notification_id):
    """
    Marque une notification spécifique comme lue pour les requêtes AJAX
    avec une réponse JSON appropriée
    """
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    
    if not notification.read:
        notification.read = True
        notification.save()
    
    # Si la requête est AJAX, retourner une réponse JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': 'Notification marquée comme lue'
        })
    
    # Sinon, rediriger vers l'URL associée à la notification ou vers le tableau de bord
    redirect_url = notification.url if notification.url else 'dashboard'
    return redirect(redirect_url)

@login_required
def mark_all_as_read(request):
    """
    Marque toutes les notifications non lues de l'utilisateur comme lues
    """
    unread_notifications = Notification.objects.filter(
        user=request.user,
        read=False
    )
    
    for notification in unread_notifications:
        notification.read = True
        notification.save()
    
    # Si la requête est AJAX, renvoyer une réponse JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'message': 'Toutes les notifications ont été marquées comme lues'})
    
    # Sinon, rediriger vers la page précédente
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

@login_required
def mark_all_read(request):
    """
    Fonction pour marquer toutes les notifications non lues comme lues
    avec prise en charge spécifique des requêtes AJAX
    """
    unread_notifications = Notification.objects.filter(
        user=request.user,
        read=False
    )
    
    for notification in unread_notifications:
        notification.read = True
        notification.save()
    
    # Si la requête est AJAX, renvoyer une réponse JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True, 
            'message': 'Toutes les notifications ont été marquées comme lues'
        })
    
    # Sinon, rediriger vers la page précédente
    return redirect(request.META.get('HTTP_REFERER', 'dashboard'))

@login_required
def notifications_page(request):
    """
    Affiche toutes les notifications de l'utilisateur sur une page dédiée
    """
    # Filtrage des notifications
    filter_type = request.GET.get('filter', 'all')
    
    if filter_type == 'unread':
        notifications = Notification.objects.filter(
            user=request.user, 
            read=False
        ).order_by('-created_at')
    else:  # 'all' par défaut
        notifications = Notification.objects.filter(
            user=request.user
        ).order_by('-created_at')
    
    # Calcul des statistiques pour le template
    all_notifications = Notification.objects.filter(user=request.user)
    stats = {
        'total': all_notifications.count(),
        'unread': all_notifications.filter(read=False).count(),
        'read': all_notifications.filter(read=True).count()
    }
    
    context = {
        'notifications': notifications,
        'current_filter': filter_type,
        'stats': stats
    }
    
    return render(request, 'rh_management/notifications.html', context)

@login_required
def notifications_view(request):
    """
    Vue principale pour afficher la page des notifications
    Alias de notifications_page pour maintenir la compatibilité
    """
    return notifications_page(request)

@login_required
def delete_notification(request, notification_id):
    """
    Supprime une notification spécifique
    """
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.delete()
    
    # Si la requête est AJAX, renvoyer une réponse JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'message': 'Notification supprimée avec succès'})
    
    # Sinon, rediriger vers la page précédente ou la page de notifications
    next_page = request.META.get('HTTP_REFERER')
    if next_page:
        return redirect(next_page)
    else:
        return redirect('notifications_page')

@login_required
def delete_all_read(request):
    """
    Supprime toutes les notifications lues de l'utilisateur
    """
    # Supprimer uniquement les notifications lues
    deleted_count = Notification.objects.filter(user=request.user, read=True).delete()[0]
    
    # Si la requête est AJAX, renvoyer une réponse JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success', 
            'message': f'{deleted_count} notification(s) supprimée(s) avec succès',
            'deleted_count': deleted_count
        })
    
    # Sinon, rediriger avec un message
    messages.success(request, f'{deleted_count} notification(s) supprimée(s) avec succès')
    
    # Rediriger vers la page précédente ou vers la page de notifications
    next_page = request.META.get('HTTP_REFERER')
    if next_page:
        return redirect(next_page)
    else:
        return redirect('notifications_page')

@login_required
def get_notifications_count(request):
    """
    Retourne uniquement le nombre de notifications non lues
    Plus léger que get_notifications pour un chargement rapide
    """
    unread_count = Notification.objects.filter(user=request.user, read=False).count()
    return JsonResponse({'count': unread_count})

def _get_time_since(timestamp):
    """
    Fonction d'assistance pour calculer le temps écoulé depuis une date
    en format lisible (ex: "il y a 5 minutes", "il y a 2 heures")
    avec gestion des erreurs améliorée
    """
    try:
        now = timezone.now()
        
        # Vérifier si timestamp est un objet datetime valide
        if not timestamp:
            return "Date inconnue"
        
        diff = now - timestamp
        
        seconds = diff.total_seconds()
        if seconds < 60:
            return "À l'instant"
        
        minutes = seconds // 60
        if minutes < 60:
            return f"il y a {int(minutes)} min"
        
        hours = minutes // 60
        if hours < 24:
            return f"il y a {int(hours)} h"
        
        days = hours // 24
        if days < 7:
            return f"il y a {int(days)} jours"
        
        weeks = days // 7
        if weeks < 4:
            return f"il y a {int(weeks)} semaines"
        
        months = days // 30
        if months < 12:
            return f"il y a {int(months)} mois"
        
        years = days // 365
        return f"il y a {int(years)} ans"
    except Exception:
        # En cas d'erreur, retourner une valeur par défaut
        return "Date inconnue"

def get_notifications_count(user):
    """
    Retourne le nombre de notifications non lues pour un utilisateur donné
    Fonction utilitaire utilisée par d'autres vues
    """
    return Notification.objects.filter(user=user, read=False).count()
