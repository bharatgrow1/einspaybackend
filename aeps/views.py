from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status, viewsets
from decimal import Decimal
from users.models import Wallet
from rest_framework.permissions import IsAuthenticated
from aeps.serializers import (AEPSActivationSerializer, OTPRequestSerializer, OTPVerifySerializer, 
                              UserServiceEnquirySerializer, WalletBalanceSerializer, MCCCategorySerializer,
                              StateRequestSerializer)

from .serializers import OnboardMerchantSerializer
from .services.aeps_manager import AEPSManager

class AEPSMerchantViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"])
    def onboard(self, request):
        serializer = OnboardMerchantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        manager = AEPSManager()
        result = manager.onboard_merchant(serializer.validated_data)

        return Response(result, status=200 if result["success"] else 400)
    

    @action(detail=False, methods=["get"])
    def services(self, request):
        manager = AEPSManager()
        response = manager.get_available_services()
        return Response(response)
    


    @action(detail=False, methods=["post"])
    def activate(self, request):
        serializer = AEPSActivationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        manager = AEPSManager()
        result = manager.activate_aeps(serializer.validated_data)

        return Response(result)
    

    @action(detail=False, methods=["post"])
    def request_otp(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        mobile = serializer.validated_data["mobile"]

        manager = AEPSManager()
        result = manager.request_otp(mobile)

        return Response(result)


    @action(detail=False, methods=["post"])
    def verify_otp(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        mobile = serializer.validated_data["mobile"]
        otp = serializer.validated_data["otp"]

        manager = AEPSManager()
        result = manager.verify_mobile(mobile, otp)

        return Response(result)



    # @action(detail=False, methods=["post"])
    # def service_status(self, request):
    #     serializer = UserServiceEnquirySerializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)

    #     user_code = serializer.validated_data["user_code"]

    #     manager = AEPSManager()
    #     result = manager.user_services(user_code)

    #     return Response(result)



    @action(detail=False, methods=["post"])
    def wallet_balance(self, request):
        serializer = WalletBalanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        customer_id_type = serializer.validated_data["customer_id_type"]
        customer_id = serializer.validated_data["customer_id"]
        user_code = serializer.validated_data.get("user_code")

        manager = AEPSManager()
        result = manager.get_wallet_balance(customer_id_type, customer_id, user_code)

        return Response(result)


    # @action(detail=False, methods=["post"])
    # def wallet_balance(self, request):
    #     serializer = WalletBalanceSerializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)

    #     customer_id_type = serializer.validated_data["customer_id_type"]
    #     customer_id = serializer.validated_data["customer_id"]
    #     user_code = serializer.validated_data.get("user_code")

    #     manager = AEPSManager()
    #     result = manager.get_wallet_balance(customer_id_type, customer_id, user_code)

    #     if request.user.role == "superadmin" and result.get("status") == 0:
    #         try:
    #             eko_balance = Decimal(str(result["data"]["balance"]))

    #             wallet, _ = Wallet.objects.get_or_create(user=request.user)

    #             wallet.balance = eko_balance
    #             wallet.save()

    #         except Exception as e:
    #             print("EKO wallet sync error:", e)

    #     return Response(result)



    @action(detail=False, methods=["post"])
    def mcc_category(self, request):        
        serializer = MCCCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_code = serializer.validated_data["user_code"]

        manager = AEPSManager()
        result = manager.get_mcc_category(user_code)

        return Response(result)
    



    @action(detail=False, methods=["post"])
    def states(self, request):
        serializer = StateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_code = serializer.validated_data["user_code"]

        manager = AEPSManager()
        result = manager.get_states(user_code)

        return Response(result)