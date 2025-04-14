from django.shortcuts import redirect, render
from rest_framework.decorators import api_view, permission_classes
from shoppit import settings
from .models import Product, Cart, CartItem, Transaction
from .serializers import ProductSerializer, DetailedProductSerializer, CartItemSerializer, SimpleCartSerializer, CartSerializer
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import UserSerializer
import json
from decimal import Decimal
import uuid
import paypalrestsdk
 
BASE_URL = "http://localhost:5173"

paypalrestsdk.configure({
    "mode": settings.PAYPAL_MODE,  # "sandbox" or "live"
    "client_id": settings.PAYPAL_CLIENT_ID,
    "client_secret": settings.PAYPAL_CLIENT_SECRET
})

# Create your views here.

@api_view(["GET"])
def products(request):
    products = Product.objects.all()
    serializer = ProductSerializer(products, many=True)
    return Response(serializer.data)

@api_view(["GET"])
def product_detail(request, slug):
    product = Product.objects.get(slug=slug)
    serializer = DetailedProductSerializer(product)
    return Response(serializer.data)

@api_view(["POST"])
def add_item(request):
    try:
        cart_code = request.data.get("cart_code")
        product_id = request.data.get("product_id")

        cart, created = Cart.objects.get_or_create(cart_code=cart_code)
        product = Product.objects.get(id=product_id)

        cartitem, created = CartItem.objects.get_or_create(cart=cart, product=product)
        cartitem.quantity = 1
        cartitem.save()

        serializer = CartItemSerializer(cartitem)

        return Response({"datat": serializer.data, "message": "Cartitem created successfully"}, status=201)
    except Exception as e:
        return Response({"error": str(e)}, status=400)
    

@api_view(['GET'])
def product_in_cart(request):
    cart_code = request.query_params.get("cart_code")
    product_id = request.query_params.get("product_id")

    cart = Cart.objects.get(cart_code=cart_code)
    product = Product.objects.get(id=product_id)

    product_exists_in_cart = CartItem.objects.filter(cart=cart, product=product).exists()

    return Response({'product_in_cart': product_exists_in_cart})


@api_view(['GET'])
def get_cart_stat(request):
    cart_code = request.query_params.get("cart_code")
    cart = Cart.objects.get(cart_code=cart_code, paid=False)
    serializer = SimpleCartSerializer(cart)
    return Response(serializer.data)


@api_view(['GET'])
def get_cart(request):
    cart_code = request.query_params.get("cart_code")
    cart = Cart.objects.get(cart_code=cart_code, paid=False)
    serializer = CartSerializer(cart)
    return Response(serializer.data)


@api_view(['PATCH'])
def update_quantity(request):
    try:
        cartitem_id = request.data.get("item_id")
        quantity = request.data.get("quantity")
        quantity = int(quantity)
        cartitem = CartItem.objects.get(id=cartitem_id)
        cartitem.quantity = quantity
        cartitem.save()
        serializer = CartItemSerializer(cartitem)
        return Response({"data": serializer.data, "message": "Cartitem updated successfully!"})
    except Exception as e:
        return Response({'error': str(e)}, status=400)
    

@api_view(['POST'])  # Acepta POST
def delete_cartitem(request):
    cartitem_id = request.data.get("item_id")
    try:
        cartitem = CartItem.objects.get(id=cartitem_id)
        cartitem.delete()
        return Response({"message": "Item deleted successfully"}, status=status.HTTP_200_OK)
    except CartItem.DoesNotExist:
        return Response({"error": "Item not found"}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
def verify_cart(request):
    """
    Verifica si un carrito está asociado al usuario actual.
    """
    if not request.user.is_authenticated:
        return Response({'error': 'User not authenticated'}, status=401)
    
    cart_code = request.data.get('cart_code')
    if not cart_code:
        return Response({'error': 'Cart code is required'}, status=400)
    
    try:
        # Intentar encontrar el carrito asociado al usuario actual
        cart = Cart.objects.get(cart_code=cart_code, user=request.user, paid=False)
        return Response({'valid': True, 'message': 'Cart is valid and associated with user'})
    except Cart.DoesNotExist:
        # Verificar si el carrito existe pero no está asociado
        cart_exists = Cart.objects.filter(cart_code=cart_code, paid=False).exists()
        if cart_exists:
            return Response({'valid': False, 'error': 'Cart exists but not associated with user'}, status=400)
        else:
            return Response({'valid': False, 'error': 'Cart not found'}, status=404)

@api_view(['POST'])
def associate_cart_to_user(request):
    if not request.user.is_authenticated:
        return Response({'error': 'User not authenticated'}, status=401)
    
    cart_code = request.data.get('cart_code')
    if not cart_code:
        return Response({'error': 'Cart code is required'}, status=400)
    
    try:
        # Buscar el carrito por código (sin importar el usuario)
        cart = Cart.objects.get(cart_code=cart_code, paid=False)
        
        # Asociar al usuario actual
        cart.user = request.user
        cart.save()
        
        return Response({'message': 'Cart associated with user successfully'})
    except Cart.DoesNotExist:
        return Response({'error': 'Cart not found'}, status=404)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_username(request):
    user = request.user
    return Response({"username": user.username})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_info(request):
    user = request.user
    serializer = UserSerializer(user)
    return Response(serializer.data)






@api_view(['POST'])
def initiate_paypal_payment(request):
    if request.method == 'POST' and request.user.is_authenticated:
        tx_ref = str(uuid.uuid4())
        user = request.user
        cart_code = request.data.get('cart_code')
        
        try:
            # Primero intentar encontrar el carrito exacto
            cart = Cart.objects.get(cart_code=cart_code, user=user)
        except Cart.DoesNotExist:
            try:
                # Si no existe con ese usuario, buscar por código y verificar que no esté pagado
                cart = Cart.objects.get(cart_code=cart_code, paid=False)
                
                # Asociar al usuario actual
                cart.user = user
                cart.save()
                print(f"Carrito {cart_code} asociado automáticamente al usuario {user.username}")
            except Cart.DoesNotExist:
                return Response({'error': 'Invalid cart code'}, status=400)

        # Verificar que el carrito tenga productos
        if not cart.items.exists():
            return Response({'error': 'Cart is empty'}, status=400)
            
        total_amount = sum(item.product.price * item.quantity for item in cart.items.all())

        # Usar BASE_URL directamente en lugar de settings.BASE_URL
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": f"{BASE_URL}/payment-status?paymentStatus=success&ref={tx_ref}",
                "cancel_url": f"{BASE_URL}/payment-status?paymentStatus=cancel",
            },
            "transactions": [
                {
                    "item_list": {
                        "items": [
                            {
                                "name": "Cart Items",
                                "sku": "cart",
                                "price": f"{total_amount:.2f}",
                                "currency": "USD",
                                "quantity": 1
                            }
                        ]
                    },
                    "amount": {
                        "total": f"{total_amount:.2f}",
                        "currency": "USD"  
                    },
                    "description": "Payment for cart items.",
                }
            ]
        })


        if payment.create():
            print("pay_id", payment.id)  

            transaction, created = Transaction.objects.get_or_create(
                ref=tx_ref,
                defaults={
                    'cart': cart,
                    'amount': total_amount,
                    'currency': "USD",  
                    'user': user,
                    'status': 'pending',  
                    # 'paypal_payment_id': payment.id  
                }
            )

            approval_url = None
            for link in payment.links:
                if link.rel == "approval_url":
                    approval_url = str(link.href)
                    return Response({"approval_url": approval_url})
            else:
                return Response({"error": "Failed to retrieve approval URL from PayPal"}, status=500)
        else:
            return Response({"error": payment.error}, status=400)
    return Response({'error': 'Invalid request'}, status=400)



@api_view(['POST'])
def paypal_payment_callback(request):
    payment_id = request.query_params.get('paymentId')
    payer_id = request.query_params.get('PayerID')
    ref = request.query_params.get('ref')

    user = request.user
    print(f"ref from callback: {ref}")

    try:
        transaction = Transaction.objects.get(ref=ref)
    except Transaction.DoesNotExist:
        return Response({'error': 'Transaction not found'}, status=404)

    if payment_id and payer_id:

        try:
            payment = paypalrestsdk.Payment.find(payment_id)
        except paypalrestsdk.exceptions.PayPalError as e:
            print(f"PayPal API error during payment retrieval: {e}")
            transaction.status = 'failed'
            transaction.save()
            return Response({'error': f'Error retrieving payment details from PayPal: {e}'}, status=500)

        if payment.state == "approved":
            try:
                if payment.execute({"payer_id": payer_id}):
                    transaction.status = 'completed'
                    transaction.paypal_payment_id = payment.id  
                    transaction.save()
                    cart = transaction.cart
                    cart.paid = True
                    cart.user = user 
                    cart.save()
                    return Response({'message': 'Payment successful', 'subMessage': 'You have successfully made payment for the items you purchased.'})
                else:
                    print(payment.error)
                    transaction.status = 'failed'
                    transaction.save()
                    return Response({'error': 'Payment execution failed'}, status=400)
            except paypalrestsdk.exceptions.PayPalError as e:
                print(f"PayPal API error during payment execution: {e}")
                transaction.status = 'failed'
                transaction.save()
                return Response({'error': f'Error executing payment: {e}'}, status=500)
        else:
            transaction.status = 'failed'
            transaction.save()
            return Response({'error': 'Payment not approved by PayPal'}, status=400)
    else:
        transaction.status = 'cancelled'  
        transaction.save()
        return Response({'error': 'Invalid payment details'}, status=400)