from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
try:
    from .ChatbotService import ChatbotService
    # Inicializar el servicio de chatbot
    chatbot_service = ChatbotService()
except ImportError as e:
    from django.utils.module_loading import import_string
    import logging
    logging.basicConfig(level=logging.ERROR)
    logger = logging.getLogger(__name__)
    logger.error(f"Error importando servicio de chatbot: {e}")
    # Definir un servicio mínimo de respaldo
    class MinimalChatService:
        def process_message(self, message, session_id=None):
            return {
                'response': "Lo siento, el servicio de chatbot no está completamente configurado. Por favor contacta al administrador.",
                'session_id': session_id or 'error_session',
                'suggested_products': []
            }
        def find_products(self, query):
            return []
    chatbot_service = MinimalChatService()

from .chatbot_models import ChatbotConversation, ChatbotMessage
from .chatbot_serializers import (
    ChatbotMessageInputSerializer, 
    ChatbotResponseSerializer,
    ChatbotConversationSerializer
)
from django.utils import timezone

@api_view(['POST'])
@permission_classes([AllowAny])
def chatbot_message(request):
    """Endpoint para procesar mensajes del chatbot con lenguaje natural."""
    serializer = ChatbotMessageInputSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    user_message = serializer.validated_data['message']
    session_id = serializer.validated_data.get('session_id')
    
    try:
        # Procesar el mensaje con el servicio de chatbot
        chatbot_response = chatbot_service.process_message(
            user_message, 
            session_id=session_id
        )
        
        # Guardar conversación en la base de datos
        conversation, created = ChatbotConversation.objects.get_or_create(
            session_id=chatbot_response['session_id'],
            defaults={'started_at': timezone.now()}
        )
        
        # Guardar mensaje del usuario
        ChatbotMessage.objects.create(
            conversation=conversation,
            sender='user',
            message=user_message
        )
        
        # Guardar respuesta del bot
        ChatbotMessage.objects.create(
            conversation=conversation,
            sender='bot',
            message=chatbot_response['response']
        )
        
        # Asociar usuario si está autenticado
        if request.user.is_authenticated and not conversation.user:
            conversation.user = request.user
            conversation.save()
        
        # Serializar y retornar la respuesta
        response_serializer = ChatbotResponseSerializer(data=chatbot_response)
        if response_serializer.is_valid():
            return Response(response_serializer.data)
        else:
            return Response(response_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        import traceback
        logger.error(f"Error en chatbot_message: {e}\n{traceback.format_exc()}")
        return Response({
            'response': 'Lo siento, estoy teniendo problemas para responder en este momento. Por favor, intenta de nuevo más tarde.',
            'session_id': session_id or 'error_session',
            'suggested_products': []
        })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chatbot_history(request):
    """
    Obtiene el historial de conversaciones del usuario autenticado.
    """
    # Obtener las conversaciones del usuario ordenadas por fecha
    conversations = ChatbotConversation.objects.filter(
        user=request.user
    ).order_by('-started_at')
    
    serializer = ChatbotConversationSerializer(conversations, many=True)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chatbot_feedback(request, conversation_id):
    """
    Guarda el feedback del usuario sobre una conversación.
    """
    # Verificar que la conversación pertenece al usuario
    try:
        conversation = ChatbotConversation.objects.get(
            id=conversation_id, 
            user=request.user
        )
    except ChatbotConversation.DoesNotExist:
        return Response(
            {'error': 'Conversación no encontrada'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Obtener calificación del request
    feedback = request.data.get('feedback')
    
    if not feedback or not isinstance(feedback, int) or feedback < 1 or feedback > 5:
        return Response(
            {'error': 'Se requiere una calificación válida del 1 al 5'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Guardar feedback
    conversation.feedback = feedback
    conversation.save()
    
    return Response({'message': 'Feedback guardado correctamente'})

@api_view(['POST'])
@permission_classes([AllowAny])
def product_query(request):
    """
    Endpoint específico para consultar productos en lenguaje natural.
    """
    query = request.data.get('query', '')
    
    if not query or len(query) < 3:
        return Response({
            'products': [],
            'message': 'La consulta es demasiado corta'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Utilizamos el mismo servicio para encontrar productos
        products = chatbot_service.find_products(query)
        
        # Serializar los resultados para devolverlos
        from .serializers import ProductSerializer
        serializer = ProductSerializer(products, many=True)
        
        # Crear una respuesta contextual
        if products:
            if len(products) == 1:
                message = f"He encontrado este producto que coincide con tu búsqueda: {products[0].name}"
            else:
                message = f"He encontrado {len(products)} productos que coinciden con tu búsqueda."
        else:
            message = "No he encontrado productos que coincidan con esa descripción. Intenta con otros términos."
        
        return Response({
            'products': serializer.data,
            'count': len(products),
            'message': message,
            'query': query
        })
    except Exception as e:
        logger.error(f"Error en product_query: {e}")
        return Response({
            'error': 'Error al procesar la consulta de productos',
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)