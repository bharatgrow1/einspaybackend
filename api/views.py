from rest_framework import viewsets
from api.models import SignUPRequest
from api.serializers import SignUPRequestSerializer
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import HelpDeskTicket
from .serializers import HelpDeskTicketSerializer
from api.utils import get_all_child_users
from django.utils import timezone
from api.models import SignUPRequest, HelpDeskTicket
from api.serializers import (SignUPRequestSerializer, HelpDeskTicketSerializer)


class SignUPRequestViewSet(viewsets.ModelViewSet):
    queryset = SignUPRequest.objects.all().order_by('-created_at')
    serializer_class = SignUPRequestSerializer


class HelpDeskViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"])
    def create_ticket(self, request):
        serializer = HelpDeskTicketSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ticket = serializer.save(created_by=request.user)

        return Response({
            "success": True,
            "message": "Ticket created successfully",
            "ticket_id": ticket.id
        })

    @action(detail=False, methods=["get"])
    def list_tickets(self, request):
        allowed_users = get_all_child_users(request.user)

        tickets = HelpDeskTicket.objects.filter(
            created_by__in=allowed_users
        ).order_by("-created_at")

        serializer = HelpDeskTicketSerializer(tickets, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def solve(self, request, pk=None):

        if request.user.role not in ["admin", "superadmin"]:
            return Response(
                {"error": "Permission denied"},
                status=403
            )

        ticket = HelpDeskTicket.objects.get(pk=pk)

        if ticket.status == "SOLVED":
            return Response({
                "message": "Ticket already solved"
            })

        ticket.status = "SOLVED"
        ticket.solved_by = request.user
        ticket.solved_at = timezone.now()
        ticket.save()

        return Response({
            "success": True,
            "message": "Ticket marked as solved"
        })
