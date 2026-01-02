from rest_framework import serializers
from api.models import SignUPRequest, HelpDeskTicket


class SignUPRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = SignUPRequest
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class HelpDeskTicketSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField(read_only=True)
    solved_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = HelpDeskTicket
        fields = "__all__"
        read_only_fields = ["id", "status", "created_by", "solved_by", "solved_at", "created_at",]