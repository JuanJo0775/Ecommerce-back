from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from .hybrid_langchain_service import HybridLangChainService  # Importar el servicio híbrido
from .chatbot_models import ChatbotConversation, ChatbotMessage
from .chatbot_serializers import (
    ChatbotMessageInputSerializer, 
    ChatbotResponseSerializer,
    ChatbotConversationSerializer
)
from django.utils import timezone
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar el servicio híbrido
hybrid_service = HybridLangChainService()

@api_view(['POST'])
@permission_classes([AllowAny])
def chatbot_message(request):
    """Endpoint para procesar mensajes del chatbot."""
    serializer = ChatbotMessageInputSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    user_message = serializer.validated_data['message']
    session_id = serializer.validated_data.get('session_id')
    
    logger.info(f"Mensaje recibido: '{user_message}' para sesión {session_id}")
    
    try:
        # Obtener respuesta usando el servicio híbrido
        chatbot_response = hybrid_service.process_message(user_message, session_id)
        
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
            logger.error(f"Error de serialización: {response_serializer.errors}")
            return Response(response_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        logger.error(f"Error al procesar mensaje: {e}")
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