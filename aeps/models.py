from django.db import models

class AEPSMerchant(models.Model):
    user_code = models.CharField(max_length=20, unique=True)
    merchant_name = models.CharField(max_length=255)
    shop_name = models.CharField(max_length=255)
    mobile = models.CharField(max_length=15)
    email = models.EmailField()
    pan_number = models.CharField(max_length=10)
    address_line = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    district = models.CharField(max_length=100, blank=True, null=True)
    area = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.merchant_name} ({self.user_code})"
