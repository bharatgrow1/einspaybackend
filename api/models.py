from django.db import models

class SignUPRequest(models.Model):
    first_name = models.CharField(max_length=200, blank=True)
    last_name = models.CharField(max_length=200, blank=True)
    email = models.EmailField(max_length=200, blank=True)
    mobile = models.CharField(max_length=14, blank=True)
    pan_no = models.CharField(max_length=10, blank=True)
    
    admin = models.BooleanField(default=False)
    superadmin = models.BooleanField(default=False)
    master = models.BooleanField(default=False)
    dealer = models.BooleanField(default=False)
    retailer = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"