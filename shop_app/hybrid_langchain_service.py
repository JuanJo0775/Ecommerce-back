import os
import uuid
import logging
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from .models import Product
from django.db.models import Q

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

class HybridLangChainService:
    """Servicio híbrido para manejar conversaciones con LangChain/OpenAI o sistema de reglas."""
    
    def __init__(self):
        # Flag para indicar si OpenAI está disponible
        self.openai_available = True
        
        try:
            # Inicializar el modelo de lenguaje
            self.llm = ChatOpenAI(
                api_key=os.getenv("OPENAI_API_KEY"),
                model_name="gpt-3.5-turbo",
                temperature=0.7
            )
            logger.info("OpenAI inicializado correctamente")
        except Exception as e:
            logger.warning(f"Error al inicializar OpenAI: {e}")
            self.openai_available = False
        
        # Cargar FAQs desde la base de datos
        self.faqs = self._load_faqs()
        
        # Plantilla para el prompt
        self.template = f"""
        Eres un asistente virtual amigable para la tienda online 'Shoppit'. 
        Tu objetivo es ayudar a los clientes con información sobre productos, 
        proceso de compra, envíos, devoluciones y cualquier otra consulta relacionada con la tienda.

        Contexto sobre Shoppit:
        - Es una tienda online de productos electrónicos, ropa y abarrotes
        - Ofrece envíos a todo el país con tiempos de entrega de 3-5 días hábiles
        - Acepta pagos con PayPal y ePayco
        - Tiene una política de devoluciones de 14 días

        Preguntas frecuentes:
        {self.faqs}

        Responde siempre en español, de manera concisa y amigable.

        Historial de la conversación:
        {{history}}
        
        Consulta actual: {{input}}
        
        Respuesta amigable:
        """
        
        # Crear prompt
        self.prompt = PromptTemplate.from_template(self.template)
        
        # Diccionario para almacenar memorias por sesión
        self.session_memories = {}
    
    def _load_faqs(self):
        """Carga las preguntas frecuentes de la base de datos."""
        try:
            from .chatbot_models import ChatbotFAQ
            
            faqs = ChatbotFAQ.objects.filter(is_active=True)
            faqs_text = ""
            
            for faq in faqs:
                faqs_text += f"P: {faq.question}\nR: {faq.answer}\n\n"
            
            return faqs_text
        except Exception as e:
            logger.error(f"Error al cargar FAQs: {e}")
            return ""
    
    def get_conversation_chain(self, session_id):
        """Obtener o crear una cadena de conversación para una sesión específica."""
        if not self.openai_available:
            return None
            
        if session_id not in self.session_memories:
            try:
                # Crear nueva memoria para esta sesión
                memory = ConversationBufferMemory(return_messages=True)
                
                # Crear cadena con esta memoria
                conversation = ConversationChain(
                    llm=self.llm,
                    memory=memory,
                    prompt=self.prompt,
                    verbose=True
                )
                
                self.session_memories[session_id] = conversation
            except Exception as e:
                logger.error(f"Error al crear conversación: {e}")
                self.openai_available = False
                return None
        
        return self.session_memories[session_id]
    
    def find_products(self, query):
        """Busca productos en la base de datos según la consulta."""
        if not query or len(query) < 3:
            return []
            
        words = query.lower().split()
        
        # Filtrar palabras comunes
        common_words = ['el', 'la', 'los', 'las', 'un', 'una', 'de', 'que', 'es', 'en', 'para']
        search_words = [word for word in words if word not in common_words and len(word) > 3]
        
        if not search_words:
            return []
            
        # Construir consulta
        query_filter = None
        for word in search_words:
            if query_filter is None:
                query_filter = Q(name__icontains=word) | Q(description__icontains=word)
            else:
                query_filter |= Q(name__icontains=word) | Q(description__icontains=word)
                
        if not query_filter:
            return []
            
        # Obtener productos
        try:
            products = Product.objects.filter(query_filter)[:5]
            return list(products)
        except Exception as e:
            logger.error(f"Error al buscar productos: {e}")
            return []
    
    def get_rule_based_response(self, message, related_products):
        """Genera respuestas basadas en reglas simples cuando OpenAI no está disponible."""
        message_lower = message.lower()
        
        # Respuestas para saludos
        if any(greeting in message_lower for greeting in ['hola', 'buenos días', 'buenas tardes', 'buenas noches', 'saludos']):
            return "¡Hola! Soy el asistente de Shoppit. ¿En qué puedo ayudarte hoy?"
        
        # Respuestas para despedidas
        if any(farewell in message_lower for farewell in ['adiós', 'chao', 'hasta luego', 'nos vemos']):
            return "¡Gracias por tu visita! Vuelve pronto a Shoppit."
        
        # Respuestas sobre productos
        if any(product_query in message_lower for product_query in ['productos', 'qué venden', 'qué tienen', 'catálogo']):
            if related_products:
                products_text = "\n".join([f"- {p.name}: ${p.price}" for p in related_products])
                return f"En Shoppit ofrecemos una variedad de productos. Basado en tu consulta, te muestro estos:\n\n{products_text}\n\n¿Te gustaría saber más sobre alguno de ellos?"
            else:
                return "En Shoppit ofrecemos una variedad de productos electrónicos, ropa y abarrotes. Puedes navegar por nuestro catálogo en la página principal. ¿Buscas algo en particular?"
        
        # Respuestas sobre envíos
        if any(shipping in message_lower for shipping in ['envío', 'enviar', 'shipping', 'entrega']):
            return "Realizamos envíos a todo el país con tiempos de entrega de 3-5 días hábiles para la mayoría de las ciudades. El costo de envío depende de la ubicación y se calcula al finalizar tu compra."
        
        # Respuestas sobre pagos
        if any(payment in message_lower for payment in ['pago', 'pagar', 'tarjeta', 'método de pago']):
            return "Aceptamos pagos con PayPal y ePayco, lo que te permite pagar con tarjeta de crédito, débito y otros métodos online. Todas las transacciones son seguras y encriptadas."
        
        # Respuestas sobre devoluciones
        if any(return_query in message_lower for return_query in ['devolución', 'devolver', 'reembolso']):
            return "Nuestra política de devoluciones te permite devolver productos dentro de los 14 días posteriores a la recepción. El producto debe estar en su embalaje original y en perfectas condiciones."
        
        # Respuesta sobre productos relacionados
        if related_products:
            products_text = "\n".join([f"- {p.name}: ${p.price}" for p in related_products])
            return f"He encontrado algunos productos que podrían interesarte:\n\n{products_text}\n\n¿Quieres saber más detalles sobre alguno de ellos?"
        
        # Respuesta por defecto
        return "Estoy aquí para ayudarte con información sobre productos, compras, envíos, devoluciones y más. ¿Podrías ser más específico sobre lo que necesitas?"
    
    def process_message(self, message, session_id=None):
        """Procesa un mensaje usando modelo de OpenAI o reglas según disponibilidad."""
        if not session_id:
            session_id = f"session_{uuid.uuid4()}"
        
        # Buscar productos relacionados
        related_products = self.find_products(message)
        product_ids = [p.id for p in related_products]
        
        # Inicialmente intentamos usar OpenAI
        if self.openai_available:
            try:
                # Obtener la cadena para esta sesión
                conversation = self.get_conversation_chain(session_id)
                
                if conversation:
                    # Añadir información de productos al contexto si hay productos relacionados
                    product_context = ""
                    if related_products:
                        product_context = "Productos relacionados con tu consulta:\n"
                        for product in related_products:
                            product_context += f"- {product.name}: ${product.price}"
                            if product.description:
                                product_context += f" - {product.description[:100]}..."
                            product_context += "\n"
                    
                    # Obtener respuesta incluyendo contexto de productos
                    if product_context:
                        response = conversation.predict(input=f"{message}\n\nContexto adicional: {product_context}")
                    else:
                        response = conversation.predict(input=message)
                    
                    logger.info(f"Respuesta generada por OpenAI para sesión {session_id}")
                    
                    return {
                        'response': response,
                        'session_id': session_id,
                        'suggested_products': product_ids
                    }
            except Exception as e:
                logger.warning(f"Error al usar OpenAI: {e}")
                logger.info("Cambiando a respuestas basadas en reglas")
                self.openai_available = False
        
        # Si OpenAI no está disponible o falló, usar sistema basado en reglas
        response = self.get_rule_based_response(message, related_products)
        logger.info(f"Respuesta generada por reglas para sesión {session_id}")
        
        return {
            'response': response,
            'session_id': session_id,
            'suggested_products': product_ids
        }