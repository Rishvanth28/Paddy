from rest_framework import serializers
from paddy_app.models import AdminTable, CustomerTable, Subscription

class AdminProfileSerializer(serializers.ModelSerializer):
    """Serializer for admin profiles (including superadmin)"""
    user_type = serializers.SerializerMethodField()
    
    class Meta:
        model = AdminTable
        fields = ['admin_id', 'first_name', 'last_name', 'email', 'phone_number', 'user_type']
    
    def get_user_type(self, obj):
        if obj.is_superadmin:
            return 'Super Admin'
        else:
            return 'Admin'


class CustomerProfileSerializer(serializers.ModelSerializer):
    """Serializer for customer profiles"""
    user_type = serializers.ReadOnlyField(default='Customer')
    admin_name = serializers.SerializerMethodField()
    subscription_status = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomerTable
        fields = ['customer_id', 'first_name', 'last_name', 'email', 'phone_number', 
                 'user_type', 'admin_id', 'admin_name', 'subscription_status']
    
    def get_admin_name(self, obj):
        if obj.admin:
            return f"{obj.admin.first_name} {obj.admin.last_name}"
        return None
    
    def get_subscription_status(self, obj):
        try:
            subscription = Subscription.objects.get(customer=obj)
            return {
                'is_active': subscription.is_active,
                'expires_on': subscription.expires_on,
                'total_amount': subscription.total_amount,
                'amount_paid': subscription.amount_paid
            }
        except Subscription.DoesNotExist:
            return None
