from django.shortcuts import redirect, render
from rest_framework.decorators import api_view, permission_classes
from shoppit import settings
from .models import Product, Cart, CartItem, Transaction
from .serializers import ProductSerializer, DetailedProductSerializer, CartItemSerializer, SimpleCartSerializer, CartSerializer
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
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
def register_user(request):
    """
    Registra un nuevo usuario en el sistema.
    """
    User = get_user_model()
    
    # Datos requeridos
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    first_name = request.data.get('first_name', '')
    last_name = request.data.get('last_name', '')
    
    # Validaciones básicas
    if not username or not email or not password:
        return Response(
            {'error': 'Se requieren username, email y password'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verificar si el usuario ya existe
    if User.objects.filter(username=username).exists():
        return Response(
            {'username': 'Este nombre de usuario ya está en uso'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verificar si el email ya existe
    if User.objects.filter(email=email).exists():
        return Response(
            {'email': 'Este correo electrónico ya está registrado'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validar la contraseña
    try:
        validate_password(password)
    except ValidationError as e:
        return Response(
            {'password': e.messages},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Crear el usuario
    try:
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        return Response(
            {'message': 'Usuario registrado correctamente'},
            status=status.HTTP_201_CREATED
        )
    except Exception as e:
        return Response(
            {'error': f'Error al crear el usuario: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# Función para actualizar el perfil del usuario
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """
    Actualiza la información del perfil del usuario actual.
    """
    user = request.user
    
    # Campos que se pueden actualizar
    updateable_fields = [
        'first_name', 
        'last_name', 
        'email', 
        'city', 
        'state', 
        'address', 
        'phone'
    ]
    
    # Actualizar sólo los campos que vienen en la petición
    for field in updateable_fields:
        if field in request.data:
            # Para email, verificar que no exista ya
            if field == 'email' and request.data[field] != user.email:
                User = get_user_model()
                if User.objects.filter(email=request.data[field]).exists():
                    return Response(
                        {'email': 'Este correo electrónico ya está registrado por otro usuario'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Actualizar el campo
            setattr(user, field, request.data[field])
    
    # Guardar los cambios
    try:
        user.save()
        return Response(
            {'message': 'Perfil actualizado correctamente'},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {'error': f'Error al actualizar el perfil: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# Función para cambiar la contraseña
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    Cambia la contraseña del usuario actual.
    """
    user = request.user
    
    current_password = request.data.get('current_password')
    new_password = request.data.get('new_password')
    
    if not current_password or not new_password:
        return Response(
            {'error': 'Se requieren la contraseña actual y la nueva'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verificar la contraseña actual
    if not user.check_password(current_password):
        return Response(
            {'detail': 'La contraseña actual es incorrecta'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validar la nueva contraseña
    try:
        validate_password(new_password, user)
    except ValidationError as e:
        return Response(
            {'error': e.messages},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Cambiar la contraseña
    user.set_password(new_password)
    user.save()
    
    return Response(
        {'message': 'Contraseña cambiada correctamente'},
        status=status.HTTP_200_OK
    )



import uuid
import json
from decimal import Decimal
from django.conf import settings


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initiate_epayco_payment(request):
    """
    Inicia un proceso de pago con ePayco usando el SDK de checkout.
    """
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
            
        # Calcular el total
        total_amount = sum(item.product.price * item.quantity for item in cart.items.all())
        
        # Crear una transacción en nuestra base de datos
        transaction, created = Transaction.objects.get_or_create(
            ref=tx_ref,
            defaults={
                'cart': cart,
                'amount': total_amount,
                'currency': "COP",
                'user': user,
                'status': 'pending',
                'payment_method': 'epayco'
            }
        )
        
        # URLs de retorno y confirmación
        BASE_URL = "http://localhost:5173"  # Ajusta según tu entorno
        return_url = f"{BASE_URL}/payment-status?ref={tx_ref}&method=epayco"
        confirmation_url = f"{request.build_absolute_uri('/').rstrip('/')}/epayco_callback/"
        
        # Preparar datos para el checkout de ePayco
        checkout_data = {
            'ref': tx_ref,
            'public_key': settings.EPAYCO_CONFIG['public_key'],
            'amount': str(total_amount),
            'tax': 0.00,  # Ajusta según tus necesidades
            'tax_base': str(total_amount),
            'currency': 'COP',  # Ajusta según tu moneda
            'description': f'Compra en Shoppit - Carrito {cart_code}',
            'country': 'co',  # País de facturación
            'test': settings.EPAYCO_CONFIG['test'],
            'external': 'false',  # Para usar el checkout dentro de la página
            'response': return_url,
            'confirmation': confirmation_url,
            
            # Datos del cliente
            'name': user.first_name or user.username,
            'last_name': user.last_name or '',
            'email': user.email,
            'cell_phone': user.phone or '',
            'address': user.address or 'Dirección no especificada',
            'city': user.city or 'Ciudad no especificada',
            
            # Datos adicionales
            'extra1': cart_code,  # Guardamos el código del carrito como referencia
            'invoice': cart_code,  # ID de factura
        }
        
        return Response(checkout_data)
    
    return Response({'error': 'Invalid request'}, status=400)

@api_view(['POST'])
def verify_epayco_payment(request):
    """
    Verifica el estado de un pago con ePayco.
    """
    ref = request.data.get('ref')
    
    if not ref:
        return Response({'error': 'Se requiere la referencia del pago'}, status=400)
    
    try:
        # Buscar la transacción en la base de datos
        transaction = Transaction.objects.get(ref=ref)
        
        # Verificar el estado actual
        if transaction.status == 'completed':
            return Response({
                'success': True,
                'status': 'completed',
                'message': 'Pago completado correctamente'
            })
        elif transaction.status == 'failed':
            return Response({
                'success': False,
                'status': 'failed',
                'message': 'El pago ha fallado'
            })
        else:
            # El pago está pendiente, podríamos consultar a ePayco por el estado actual
            # Para este ejemplo, simplemente devolvemos el estado actual
            return Response({
                'success': False,
                'status': 'pending',
                'message': 'El pago está pendiente de confirmación'
            })
    except Transaction.DoesNotExist:
        return Response({
            'success': False,
            'status': 'not_found',
            'message': 'No se encontró la transacción'
        }, status=404)
    except Exception as e:
        return Response({
            'success': False,
            'status': 'error',
            'message': str(e)
        }, status=500)

@api_view(['POST'])
def epayco_callback(request):
    """
    Callback para recibir confirmación de pago de ePayco.
    """
    # ePayco envía datos en el cuerpo de la solicitud
    data = request.data
    ref = data.get('x_ref_payco') or data.get('ref_payco')
    
    if not ref:
        return Response({'error': 'Missing reference'}, status=400)
    
    try:
        # Aquí normalmente verificarías la firma para asegurar que la respuesta es de ePayco
        # Pero por simplicidad, asumiremos que es válida
        
        transaction = Transaction.objects.get(ref=ref)
        status = data.get('x_transaction_state') or data.get('transaction_state')
        
        # Actualizar el estado de la transacción según la respuesta de ePayco
        if status == 'Aceptada':
            transaction.status = 'completed'
            transaction.save()
            
            # Marcar el carrito como pagado
            cart = transaction.cart
            cart.paid = True
            cart.save()
            
            return Response({'message': 'Payment confirmed'})
        else:
            transaction.status = 'failed'
            transaction.save()
            return Response({'error': 'Payment not accepted'}, status=400)
            
    except Transaction.DoesNotExist:
        return Response({'error': 'Transaction not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

# Actualizar la vista existente de PaymentStatusPage para manejar también ePayco
# En el frontend, necesitarás modificar esta parte

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
    

@api_view(["GET"])
def product_detail_by_id(request, product_id):
    try:
        product = Product.objects.get(id=product_id)
        serializer = ProductSerializer(product)
        return Response(serializer.data)
    except Product.DoesNotExist:
        return Response({"error": "Producto no encontrado"}, status=404)