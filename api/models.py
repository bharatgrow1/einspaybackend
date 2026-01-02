from django.db import models
from users.models import User

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
    

class HelpDeskTicket(models.Model):

    STATUS_CHOICES = (
        ("OPEN", "Open"),
        ("SOLVED", "Solved"),
    )

    created_by = models.ForeignKey(User,on_delete=models.CASCADE,related_name="helpdesk_tickets")
    service = models.CharField(max_length=100)
    description = models.TextField()
    attachment = models.FileField(upload_to="helpdesk/",null=True,blank=True)
    status = models.CharField(max_length=10,choices=STATUS_CHOICES,default="OPEN")
    solved_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True,blank=True,related_name="solved_helpdesk_tickets")
    solved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"TICKET-{self.id} ({self.status})"