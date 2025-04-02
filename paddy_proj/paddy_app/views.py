from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.hashers import make_password
from .models import AdminTable, CustomerTable, Orders, Payments, Subscription
from .serializers import AdminSerializer, CustomerSerializer, OrdersSerializer, PaymentsSerializer, SubscriptionSerializer

# ✅ Admin Views
@api_view(['GET', 'POST'])
def admin_list(request):
    if request.method == 'GET':
        admins = AdminTable.objects.all()
        serializer = AdminSerializer(admins, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        data = request.data.copy()
        data['password'] = make_password(data['password'])  # Hash password
        serializer = AdminSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
def admin_detail(request, admin_id):
    try:
        admin = AdminTable.objects.get(id=admin_id)
    except AdminTable.DoesNotExist:
        return Response({'error': 'Admin not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = AdminSerializer(admin)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = AdminSerializer(admin, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        admin.delete()
        return Response({'message': 'Admin deleted successfully'}, status=status.HTTP_204_NO_CONTENT)

# ✅ Customer Views
@api_view(['GET', 'POST'])
def customer_list(request):
    if request.method == 'GET':
        customers = CustomerTable.objects.all()
        serializer = CustomerSerializer(customers, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = CustomerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ✅ Order Views
@api_view(['GET', 'POST'])
def order_list(request):
    if request.method == 'GET':
        orders = Orders.objects.all()
        serializer = OrdersSerializer(orders, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = OrdersSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ✅ Payment Views
@api_view(['GET', 'POST'])
def payment_list(request):
    if request.method == 'GET':
        payments = Payments.objects.all()
        serializer = PaymentsSerializer(payments, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = PaymentsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ✅ Subscription Views
@api_view(['GET', 'POST'])
def subscription_list(request):
    if request.method == 'GET':
        subscriptions = Subscription.objects.all()
        serializer = SubscriptionSerializer(subscriptions, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = SubscriptionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
