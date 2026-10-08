from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import redirect, render

from .models import SupportTicket
from .serializers import SupportTicketSerializer


class SupportTicketListView(generics.ListCreateAPIView):
    serializer_class = SupportTicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SupportTicket.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@login_required(login_url='login')
def support_page_view(request):
    if request.method == 'POST':
        category = request.POST.get('category', 'AUTRE').strip() or 'AUTRE'
        message_text = request.POST.get('message', '').strip()
        screenshot = request.FILES.get('screenshot')
        if not message_text:
            messages.error(request, 'Décrivez votre demande avant de la soumettre.')
        elif request.POST.get('include_capture') and not screenshot:
            messages.error(request, 'Vous avez demandé une capture : choisissez un fichier avant de soumettre.')
        elif screenshot and (
            Path(screenshot.name).suffix.lower() not in {'.png', '.jpg', '.jpeg'}
            or screenshot.size > 5 * 1024 * 1024
        ):
            messages.error(request, 'La capture doit être une image PNG/JPG de 5 Mo maximum.')
        else:
            SupportTicket.objects.create(
                user=request.user,
                subject=category,
                message=message_text,
                screenshot=screenshot,
            )
            messages.success(request, 'Votre plainte a été enregistrée.')
        return redirect('support-page')

    tickets = SupportTicket.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'support/support_page.html', {'tickets': tickets})
