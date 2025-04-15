import re
import uuid
import string
import difflib
from .chatbot_models import ChatbotFAQ, ChatbotConversation, ChatbotMessage
from .models import Product
from django.utils import timezone
from django.db.models import Q

class ChatbotService:
    """Servicio para gestionar la lógica del chatbot."""
    
    def __init__(self):
        # Respuestas predeterminadas
        self.default_responses = {
            'greeting': '¡Hola! Soy el asistente virtual de Shoppit. ¿En qué puedo ayudarte hoy?',
            'farewell': 'Gracias por contactarnos. ¡Que tengas un buen día!',
            'not_understood': 'Lo siento, no he entendido tu pregunta. ¿Podrías reformularla?',
            'ask_for_more': '¿Hay algo más en lo que pueda ayudarte?',
            'product_not_found': 'Lo siento, no he podido encontrar un producto que coincida con tu descripción.'
        }
        
        # Patrones comunes
        self.patterns = {
            'greeting': r'\b(hola|saludos|buenos días|buenas tardes|buenas noches)\b',
            'farewell': r'\b(adiós|chao|hasta luego|nos vemos)\b',
            'gratitude': r'\b(gracias|te agradezco|agradecido)\b',
            'price_inquiry': r'\b(precio|costo|valor|cuánto cuesta|cuánto vale)\b',
            'product_inquiry': r'\b(producto|artículo|item)\b',
            'shipping': r'\b(envío|enviar|shipping|entrega)\b',
            'payment': r'\b(pago|pagar|método de pago|tarjeta)\b',
            'help': r'\b(ayuda|ayúdame|necesito ayuda)\b',
            'order': r'\b(orden|pedido|compra|status)\b'
        }

    def preprocess_text(self, text):
        """Preprocesa el texto para análisis."""
        if not text:
            return ""
            
        # Convertir a minúsculas
        text = text.lower()
        
        # Eliminar signos de puntuación
        translator = str.maketrans('', '', string.punctuation)
        text = text.translate(translator)
        
        return text
    
    def find_best_faq_match(self, processed_text):
        """Encuentra la mejor coincidencia de FAQ para un texto dado."""
        if not processed_text:
            return None
            
        # Obtener todas las FAQs activas
        faqs = ChatbotFAQ.objects.filter(is_active=True)
        
        if not faqs:
            return None
        
        best_match = None
        highest_similarity = 0.5  # Umbral mínimo de similitud
        
        # Dividir la consulta en palabras para buscar keywords
        query_words = processed_text.split()
        
        for faq in faqs:
            # Verificar coincidencia por palabras clave
            keywords = faq.get_keywords_list()
            keyword_matches = sum(1 for word in query_words if word in keywords)
            
            # Si hay al menos una coincidencia de palabra clave
            if keyword_matches > 0:
                # Calcular similitud de texto completo
                similarity = difflib.SequenceMatcher(
                    None, 
                    processed_text, 
                    self.preprocess_text(faq.question)
                ).ratio()
                
                # Dar más peso a la coincidencia de palabras clave
                adjusted_similarity = similarity + (keyword_matches * 0.1)
                
                if adjusted_similarity > highest_similarity:
                    highest_similarity = adjusted_similarity
                    best_match = faq
        
        return best_match
    
    def detect_intent(self, text):
        """Detecta la intención del mensaje del usuario."""
        processed_text = self.preprocess_text(text)
        
        # Verificar patrones
        for intent, pattern in self.patterns.items():
            if re.search(pattern, processed_text):
                return intent
                
        # Si no hay un patrón claro, buscar en las FAQs
        faq_match = self.find_best_faq_match(processed_text)
        if faq_match:
            return 'faq', faq_match
            
        return 'unknown'
    
    def find_product_by_name(self, product_name):
        """Busca productos por nombre o descripción."""
        if not product_name:
            return []
            
        processed_name = self.preprocess_text(product_name)
        words = processed_name.split()
        
        # Filtro base para la búsqueda
        query = None
        
        # Construir consulta OR dinámica
        for word in words:
            if len(word) < 3:  # Ignorar palabras muy cortas
                continue
                
            if query is None:
                query = Q(name__icontains=word) | Q(description__icontains=word)
            else:
                query |= Q(name__icontains=word) | Q(description__icontains=word)
        
        if query is None:
            return []
            
        # Buscar productos
        products = Product.objects.filter(query)[:5]  # Limitar a 5 resultados
        return products
    
    def get_product_info(self, product_name):
        """Obtiene información sobre productos."""
        products = self.find_product_by_name(product_name)
        
        if not products:
            return self.default_responses['product_not_found']
            
        # Formar respuesta con los productos encontrados
        response = "He encontrado estos productos:\n\n"
        
        for product in products:
            response += f"- {product.name}: ${product.price}\n"
        
        response += "\n¿Deseas más información sobre alguno de estos productos?"
        return response, [p.id for p in products]
    
    def generate_response(self, user_message, session_id=None):
        """Genera una respuesta al mensaje del usuario."""
        # Asegurar que tenemos un session_id
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Detectar la intención
        intent_result = self.detect_intent(user_message)
        
        # Preparar respuesta
        response = ""
        suggested_products = []
        
        # Manejar diferentes intenciones
        if isinstance(intent_result, tuple) and intent_result[0] == 'faq':
            # Responder con la FAQ
            response = intent_result[1].answer
        elif intent_result == 'greeting':
            response = self.default_responses['greeting']
        elif intent_result == 'farewell':
            response = self.default_responses['farewell']
        elif intent_result == 'gratitude':
            response = "¡De nada! Estoy aquí para ayudarte. ¿Necesitas algo más?"
        elif intent_result == 'price_inquiry':
            # Extraer posible nombre de producto
            processed = self.preprocess_text(user_message)
            words = processed.split()
            # Buscar palabras que podrían ser productos (excluyendo palabras comunes)
            common_words = ['precio', 'costo', 'cuanto', 'vale', 'cuesta', 'del', 'de', 'la', 'el', 'los', 'las']
            product_words = [word for word in words if word not in common_words and len(word) > 3]
            
            if product_words:
                product_name = ' '.join(product_words)
                product_response, product_ids = self.get_product_info(product_name)
                response = product_response
                suggested_products = product_ids
            else:
                response = "¿Sobre qué producto te gustaría conocer el precio?"
        elif intent_result == 'product_inquiry':
            # Similar al caso anterior, extraer posible nombre de producto
            processed = self.preprocess_text(user_message)
            words = processed.split()
            common_words = ['producto', 'articulo', 'item', 'tienen', 'venden', 'hay']
            product_words = [word for word in words if word not in common_words and len(word) > 3]
            
            if product_words:
                product_name = ' '.join(product_words)
                product_response, product_ids = self.get_product_info(product_name)
                response = product_response
                suggested_products = product_ids
            else:
                response = "¿Qué producto estás buscando? Puedes decirme el nombre o el tipo de producto."
        elif intent_result == 'shipping':
            response = "Realizamos envíos a todo el país. El costo del envío depende de la ubicación y se calcula en el checkout. Los tiempos de entrega son de 3-5 días hábiles para la mayoría de las ciudades."
        elif intent_result == 'payment':
            response = "Aceptamos pagos con PayPal y ePayco, lo que te permite pagar con tarjeta de crédito, débito y otros métodos online. Todas las transacciones son seguras y encriptadas."
        elif intent_result == 'help':
            response = "Estoy aquí para ayudarte. Puedo brindarte información sobre nuestros productos, precios, métodos de pago, envíos o asistirte con tu proceso de compra. ¿En qué puedo ayudarte específicamente?"
        elif intent_result == 'order':
            response = "Para consultar el estado de tu pedido, puedes ir a la sección 'Mi Perfil' y luego a 'Historial de Órdenes'. Allí encontrarás todos los detalles de tus compras anteriores."
        else:
            response = self.default_responses['not_understood']
        
        # Guardar la conversación en la base de datos
        self._save_conversation(user_message, response, session_id)
        
        return {
            'response': response,
            'session_id': session_id,
            'suggested_products': suggested_products
        }
    
    def _save_conversation(self, user_message, bot_response, session_id):
        """Guarda la conversación en la base de datos."""
        # Buscar o crear conversación
        conversation, created = ChatbotConversation.objects.get_or_create(
            session_id=session_id,
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
            message=bot_response
        )
        
        # Actualizar timestamp de la conversación
        conversation.save()