from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from datetime import timedelta
import json

User = get_user_model()

class Command(BaseCommand):
    help = 'Create a permanent test token for development'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='testadmin',
            help='Username for test user (default: testadmin)'
        )
        parser.add_argument(
            '--email',
            type=str,
            default='priteshrao3@gmail.com',
            help='Email for test user'
        )
        parser.add_argument(
            '--password', 
            type=str,
            default='test@123',
            help='Password for test user'
        )
        parser.add_argument(
            '--role',
            type=str,
            choices=['superadmin', 'admin', 'master', 'dealer', 'retailer'],
            default='admin',
            help='Role for test user (default: admin)'
        )

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']
        role = options['role']

        # Delete existing user if exists to ensure clean creation
        User.objects.filter(username=username).delete()
        
        # Create new user with specified role
        user = User.objects.create(
            username=username,
            email=email,
            is_staff=True,
            is_superuser=(role == 'superadmin'),
            role=role
        )
        
        user.set_password(password)
        user.save()
        
        self.stdout.write(self.style.SUCCESS(f'✅ Created {role} user: {username}'))
        
        # Generate token with very long expiry
        refresh = RefreshToken.for_user(user)
        refresh.access_token.set_exp(lifetime=timedelta(days=365))
        
        token_data = {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user_id': user.id,
            'username': user.username,
            'role': user.role,
            'email': user.email,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser
        }
        
        self.stdout.write(self.style.SUCCESS('🔑 Permanent Admin Test Token Created:'))
        self.stdout.write("")
        self.stdout.write("ACCESS TOKEN:")
        self.stdout.write(token_data['access'])
        self.stdout.write("")
        self.stdout.write("FULL TOKEN DATA:")
        self.stdout.write(json.dumps(token_data, indent=2))
        
        # Save to file
        with open('admin_test_token.json', 'w') as f:
            json.dump(token_data, f, indent=2)
        
        self.stdout.write(self.style.SUCCESS('💾 Token saved to admin_test_token.json'))
        
        # Print usage examples
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS('🚀 Usage Examples:'))
        self.stdout.write("")
        self.stdout.write(f"Role: {role} | Staff: {user.is_staff} | Superuser: {user.is_superuser}")