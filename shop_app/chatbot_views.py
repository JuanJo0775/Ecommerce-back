from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from .chatbot_service import ChatbotService
from .chatbot_models import ChatbotFAQ, ChatbotConversation, ChatbotMessage
from .chatbot_serializers import (
    ChatbotMessageInputSerializer, 
    ChatbotResponseSerializer,
    ChatbotConversationSerializer
)
import requests
from django.conf import settings


chatbot_service = ChatbotService()

from rest_framework.decorators import api_view
from rest_framework.response import Response
import requests
from django.conf import settings

def find_relevant_products(self, query_text):
    """Busca productos relevantes basados en la consulta del usuario."""
    if not query_text:
        return []
    
    # Importar lo necesario dentro de la función
    from django.db.models import Q
    from .models import Product  # Asegúrate de que la ruta de importación sea correcta

    processed_text = self.preprocess_text(query_text)
    words = processed_text.split()
    
    # Ignorar palabras muy comunes y cortas
    common_words = ['el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 
                   'y', 'o', 'de', 'del', 'para', 'por', 'con', 'sin']
    
    search_words = [word for word in words 
                   if word not in common_words and len(word) > 3]
    
    if not search_words:
        return []
    
    # Construir consulta dinámica
    query_filter = None
    
    for word in search_words:
        if query_filter is None:
            query_filter = Q(name__icontains=word) | Q(description__icontains=word)
        else:
            query_filter |= Q(name__icontains=word) | Q(description__icontains=word)
    
    # Si no hay palabras de búsqueda válidas, retornar lista vacía
    if query_filter is None:
        return []
    
    # Realizar búsqueda limitada a 5 productos
    products = Product.objects.filter(query_filter).distinct()[:5]
    
    return list(products)

@api_view(['POST'])
def chatbot_message(request):
    user_message = request.data.get('message')
    session_id = request.data.get('session_id')
    
    # Intentar usar Rasa si está configurado
    try:
        if hasattr(settings, 'RASA_API_URL'):
            rasa_response = requests.post(
                f"{settings.RASA_API_URL}/webhooks/rest/webhook",
                json={"sender": session_id, "message": user_message}
            ).json()
            
            response_text = rasa_response[0]['text'] if rasa_response else None
        else:
            response_text = None
    except Exception as e:
        print(f"Error al comunicarse con Rasa: {e}")
        response_text = None
    
    # Si Rasa no está disponible o falla, usar nuestro chatbot básico
    if not response_text:
        # Usar tu servicio de chatbot existente
        from .chatbot_service import chatbot_service
        chatbot_response = chatbot_service.generate_response(user_message, session_id)
        response_text = chatbot_response['response']
    
    # Buscar productos relevantes basados en la consulta
    products = []
    if "producto" in user_message.lower() or "busco" in user_message.lower():
        products = find_relevant_products(user_message)
    
    return Response({
        "response": response_text,
        "session_id": session_id,
        "suggested_products": [p.id for p in products]
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