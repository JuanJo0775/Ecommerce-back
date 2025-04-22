import logging
import re
import uuid
from django.db.models import Q
from .models import Product

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatbotService:
    """
    Servicio de chatbot con capacidad de procesamiento de lenguaje natural
    y búsqueda inteligente de productos sin dependencias externas.
    """
    
    def __init__(self):
        # Diccionario de sinónimos para mejorar la búsqueda
        self.synonym_dict = {
            'camisa': ['camiseta', 'playera', 'remera', 'polo', 'blusa', 'franela'],
            'camiseta': ['camisa', 'playera', 'remera', 'polo', 'blusa', 'franela'],
            'pantalon': ['pantalones', 'jeans', 'vaqueros', 'mezclilla', 'pants', 'leggins'],
            'zapato': ['zapatos', 'calzado', 'tenis', 'zapatillas', 'sneakers', 'deportivos'],
            'telefono': ['celular', 'movil', 'smartphone', 'iphone', 'android', 'telefono'],
            'computadora': ['computador', 'laptop', 'ordenador', 'portatil', 'pc', 'notebook'],
            'television': ['tv', 'tele', 'televisor', 'pantalla', 'smart tv', 'led'],
            'auricular': ['audifonos', 'cascos', 'headphones', 'auriculares', 'earbuds', 'audifonos']
        }
        
        # Categorías conocidas para búsqueda contextual
        self.categories = {
            'electronica': ['telefono', 'computadora', 'television', 'laptop', 'celular', 'auricular', 
                           'tablet', 'smartwatch', 'reloj', 'camara', 'bluetooth', 'parlante', 'usb'],
            'ropa': ['camisa', 'camiseta', 'pantalon', 'vestido', 'falda', 'short', 'zapato', 'chaqueta', 
                    'abrigo', 'sudadera', 'bufanda', 'sombrero', 'gorra', 'calcetines', 'ropa interior'],
            'hogar': ['silla', 'mesa', 'sofa', 'cama', 'almohada', 'cortina', 'cocina', 'plato', 
                     'vaso', 'cuchillo', 'tenedor', 'cuchara', 'microondas', 'refrigerador', 'horno']
        }
        
        # Diccionario para características de productos
        self.product_attributes = {
            'colores': ['rojo', 'azul', 'verde', 'amarillo', 'negro', 'blanco', 'gris', 'morado', 
                      'rosa', 'naranja', 'marron', 'celeste', 'dorado', 'plateado'],
            'materiales': ['algodon', 'poliester', 'lana', 'nylon', 'seda', 'cuero', 'piel', 'metal', 
                         'plastico', 'madera', 'vidrio', 'ceramica', 'acero', 'aluminio'],
            'tallas': ['xs', 's', 'm', 'l', 'xl', 'xxl', 'grande', 'mediano', 'pequeño', 
                      'chico', 'extragrande'],
            'marcas': ['samsung', 'apple', 'xiaomi', 'sony', 'lg', 'hp', 'dell', 'lenovo', 'asus', 
                     'acer', 'nike', 'adidas', 'puma', 'reebok', 'zara']
        }
        
        # Patrones de intención para detectar búsquedas de productos
        self.product_intent_patterns = [
            r'(?:busco|buscando|quiero|necesito|tienen|hay|donde|encuentro|vende[ns]?)\s+(?:un|una|unos|unas)?\s+([^?.,!;]+)',
            r'(?:me puedes|puede|podria[ns]?)\s+(?:mostrar|enseñar|dar|indicar)\s+(?:un|una|unos|unas)?\s+([^?.,!;]+)',
            r'estoy interesado en (?:un|una|unos|unas)?\s+([^?.,!;]+)',
            r'(?:me gustaria|quisiera|me encantaria)\s+(?:ver|comprar)\s+(?:un|una|unos|unas)?\s+([^?.,!;]+)'
        ]
        
        # Cargar FAQs desde la base de datos
        self.faqs = self._load_faqs()
        
        # Diccionario para almacenar historiales de conversación por sesión
        self.conversations = {}
    
    def _load_faqs(self):
        """Carga las preguntas frecuentes de la base de datos."""
        try:
            from .chatbot_models import ChatbotFAQ
            
            faqs = ChatbotFAQ.objects.filter(is_active=True)
            faq_dict = {}
            
            for faq in faqs:
                # Normalizar pregunta para búsqueda
                norm_question = self._normalize_text(faq.question)
                # Añadir palabras clave normalizadas
                keywords = [self._normalize_text(kw.strip()) for kw in faq.keywords.split(',') if kw.strip()]
                
                faq_dict[norm_question] = {
                    'answer': faq.answer,
                    'keywords': keywords,
                    'category': faq.category
                }
            
            return faq_dict
        except Exception as e:
            logger.error(f"Error al cargar FAQs: {e}")
            return {}
    
    def _normalize_text(self, text):
        """Normaliza el texto para búsquedas (simplificado)"""
        if not text:
            return ""
        # Convertir a minúsculas
        normalized = text.lower()
        # Reemplazar caracteres con acentos (versión simplificada)
        accent_map = {
            'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 
            'ü': 'u', 'ñ': 'n', 'ç': 'c'
        }
        for accent, replace in accent_map.items():
            normalized = normalized.replace(accent, replace)
        # Eliminar caracteres especiales excepto letras, números y espacios
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        # Reemplazar múltiples espacios con uno solo
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized
    
    def _extract_product_attributes(self, query):
        """
        Extrae atributos de productos de la consulta (color, material, talla, etc.)
        """
        normalized_query = self._normalize_text(query)
        attributes = {}
        
        # Buscar atributos en la consulta
        for attr_type, values in self.product_attributes.items():
            found_values = []
            for value in values:
                if value in normalized_query.split():
                    found_values.append(value)
            
            if found_values:
                attributes[attr_type] = found_values
        
        return attributes
    
    def _extract_product_query(self, message):
        """
        Extrae consultas de productos del mensaje usando patrones de intención.
        Retorna la parte del mensaje que contiene la descripción del producto.
        """
        normalized_message = self._normalize_text(message)
        
        for pattern in self.product_intent_patterns:
            match = re.search(pattern, normalized_message)
            if match:
                return match.group(1).strip()
        
        # Si no hay un patrón explícito pero contiene términos de productos
        for category, terms in self.categories.items():
            for term in terms:
                if term in normalized_message.split():
                    # Buscar qué está pidiendo alrededor de este término
                    parts = normalized_message.split()
                    idx = parts.index(term)
                    start = max(0, idx - 3)
                    end = min(len(parts), idx + 4)
                    return ' '.join(parts[start:end])
        
        # Si no se detecta nada, devolver None
        return None
    
    def _expand_search_terms(self, terms):
        """Expande los términos de búsqueda con sinónimos"""
        expanded_terms = []
        
        for term in terms:
            expanded_terms.append(term)
            
            # Buscar en el diccionario de sinónimos
            for key, synonyms in self.synonym_dict.items():
                # Si el término está en los sinónimos de esta palabra clave
                if term in synonyms:
                    expanded_terms.append(key)
                # O si el término es la palabra clave, añadir sus sinónimos
                elif term == key:
                    expanded_terms.extend(synonyms)
        
        return list(set(expanded_terms))  # Eliminar duplicados
    
    def _identify_categories(self, query):
        """Identifica posibles categorías en la consulta"""
        normalized_query = self._normalize_text(query)
        words = normalized_query.split()
        
        potential_categories = []
        
        for word in words:
            for category, keywords in self.categories.items():
                if word in keywords or any(word in self._expand_search_terms([keyword]) for keyword in keywords):
                    potential_categories.append(category)
        
        return list(set(potential_categories))
    
    def find_products(self, query):
        """
        Búsqueda inteligente de productos que entiende lenguaje natural.
        """
        if not query or len(query) < 3:
            return []
            
        # Normalizar y dividir la consulta en palabras
        normalized_query = self._normalize_text(query)
        words = normalized_query.split()
        
        # Filtrar palabras comunes demasiado cortas
        common_words = ['el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'de', 'que', 'es', 'en', 'para', 'con', 'por', 'sin', 'como', 'mas', 'muy']
        search_words = [word for word in words if word not in common_words and len(word) > 2]
        
        if not search_words:
            return []
        
        # Extraer atributos específicos (color, talla, etc.)
        attributes = self._extract_product_attributes(query)
        
        # Expandir términos de búsqueda con sinónimos
        expanded_terms = self._expand_search_terms(search_words)
        
        # Identificar posibles categorías
        categories = self._identify_categories(query)
        
        # Construir consulta principal con términos expandidos
        query_filter = None
        for term in expanded_terms:
            if query_filter is None:
                query_filter = Q(name__icontains=term) | Q(description__icontains=term)
            else:
                query_filter |= Q(name__icontains=term) | Q(description__icontains=term)
        
        # Añadir filtro de categoría si se identificó alguna
        category_filter = None
        for category in categories:
            if category_filter is None:
                category_filter = Q(category__icontains=category)
            else:
                category_filter |= Q(category__icontains=category)
        
        # Añadir filtros por atributos específicos
        attr_filter = None
        for attr_type, values in attributes.items():
            for value in values:
                if attr_filter is None:
                    attr_filter = Q(name__icontains=value) | Q(description__icontains=value)
                else:
                    attr_filter |= Q(name__icontains=value) | Q(description__icontains=value)
        
        # Combinar todos los filtros
        combined_filter = query_filter
        
        if category_filter:
            if combined_filter:
                combined_filter = combined_filter & category_filter
            else:
                combined_filter = category_filter
        
        if attr_filter:
            if combined_filter:
                combined_filter = combined_filter & attr_filter
            else:
                combined_filter = attr_filter
        
        if not combined_filter:
            return []
            
        # Obtener productos
        try:
            # Intentar buscar con el filtro combinado
            products = list(Product.objects.filter(combined_filter)[:8])
            
            # Si no hay suficientes resultados, ampliar la búsqueda
            if len(products) < 3:
                # Buscar por categoría de manera más amplia
                if categories:
                    category_products = list(Product.objects.filter(category__icontains=categories[0])[:5])
                    # Añadir productos que no estén ya en la lista
                    for product in category_products:
                        if product not in products:
                            products.append(product)
                
                # Si todavía no hay suficientes, usar solo términos expandidos sin filtros adicionales
                if len(products) < 2:
                    expanded_filter = None
                    for term in expanded_terms:
                        if expanded_filter is None:
                            expanded_filter = Q(name__icontains=term) | Q(description__icontains=term)
                        else:
                            expanded_filter |= Q(name__icontains=term) | Q(description__icontains=term)
                    
                    if expanded_filter:
                        extra_products = list(Product.objects.filter(expanded_filter)[:8])
                        for product in extra_products:
                            if product not in products:
                                products.append(product)
            
            return products
        except Exception as e:
            logger.error(f"Error al buscar productos: {e}")
            return []
    
    def _find_matching_faq(self, message):
        """Busca una FAQ que coincida con el mensaje del usuario."""
        if not self.faqs:
            return None
            
        normalized_message = self._normalize_text(message)
        words = normalized_message.split()
        
        # Primera pasada: buscar preguntas que coincidan exactamente
        for q, faq_data in self.faqs.items():
            if normalized_message == q:
                return faq_data['answer']
        
        # Segunda pasada: búsqueda por palabras clave
        best_match = None
        max_score = 0
        
        for q, faq_data in self.faqs.items():
            score = 0
            
            # Puntuar coincidencias de palabras clave
            for keyword in faq_data['keywords']:
                if keyword in normalized_message:
                    score += 2
            
            # Puntuar coincidencias de palabras en la pregunta
            q_words = q.split()
            for word in words:
                if word in q_words and len(word) > 3:  # Palabras significativas
                    score += 1
            
            if score > max_score:
                max_score = score
                best_match = faq_data['answer']
        
        # Umbral mínimo para considerar una coincidencia
        if max_score >= 3:
            return best_match
        
        return None
    
    def _generate_product_response(self, products, query, attributes):
        """
        Genera una respuesta natural basada en los productos encontrados
        y las características especificadas.
        """
        # Si no hay productos
        if not products:
            if attributes:
                attr_str = ""
                for attr_type, values in attributes.items():
                    if attr_type == 'colores':
                        attr_str += f" {', '.join(values)} "
                    elif attr_type == 'materiales':
                        attr_str += f" de {', '.join(values)} "
                    elif attr_type == 'tallas':
                        attr_str += f" talla {', '.join(values)} "
                    elif attr_type == 'marcas':
                        attr_str += f" marca {', '.join(values)} "
                
                return f"Lo siento, no encontré productos{attr_str}que coincidan con '{query}'. ¿Podrías describir lo que buscas de otra manera o con otros detalles?"
            else:
                return f"No he encontrado productos que coincidan con '{query}'. ¿Podrías ser más específico o describir lo que buscas de otra manera?"
        
        # Si hay un solo producto
        if len(products) == 1:
            product = products[0]
            return f"He encontrado este producto que podría interesarte: {product.name} a ${product.price}. {product.description or ''} ¿Te gustaría más información sobre este artículo o ver productos similares?"
        
        # Si hay varios productos
        categories = set()
        for p in products:
            if hasattr(p, 'category') and p.category:
                categories.add(p.category)
        
        category_str = ""
        if len(categories) == 1:
            category_str = f" de {next(iter(categories))}"
        
        response = f"He encontrado {len(products)} productos{category_str} que podrían interesarte:\n\n"
        
        for i, product in enumerate(products[:5], 1):
            response += f"{i}. {product.name} - ${product.price}\n"
        
        if len(products) > 5:
            response += f"... y {len(products) - 5} más.\n"
        
        response += "\n¿Te gustaría más detalles sobre alguno de estos productos?"
        
        return response
    
    def _get_conversation_history(self, session_id, max_entries=5):
        """Obtiene el historial reciente de la conversación."""
        if session_id not in self.conversations:
            return []
        
        return self.conversations[session_id][-max_entries:]
    
    def _update_conversation(self, session_id, role, text):
        """Actualiza el historial de la conversación."""
        if session_id not in self.conversations:
            self.conversations[session_id] = []
        
        self.conversations[session_id].append({
            'role': role,
            'text': text
        })
        
        # Limitar el tamaño del historial
        if len(self.conversations[session_id]) > 20:
            self.conversations[session_id] = self.conversations[session_id][-20:]
    
    def process_message(self, message, session_id=None):
        """
        Procesa un mensaje del usuario y genera una respuesta natural.
        
        Args:
            message (str): El mensaje del usuario
            session_id (str, optional): ID de sesión para mantener contexto
        """
        if not session_id:
            session_id = f"session_{uuid.uuid4()}"
        
        # Actualizar historial con el mensaje del usuario
        self._update_conversation(session_id, 'user', message)
        
        # Normalizar mensaje para procesamiento
        normalized_message = self._normalize_text(message)
        
        # 1. Comprobar si es una pregunta frecuente
        faq_response = self._find_matching_faq(message)
        if faq_response:
            self._update_conversation(session_id, 'bot', faq_response)
            return {
                'response': faq_response,
                'session_id': session_id,
                'suggested_products': []
            }
        
        # 2. Detectar si es una búsqueda de producto
        product_query = self._extract_product_query(message)
        
        if product_query:
            # Extraer atributos específicos
            attributes = self._extract_product_attributes(message)
            
            # Buscar productos
            products = self.find_products(product_query)
            product_ids = [p.id for p in products]
            
            # Generar respuesta natural
            response = self._generate_product_response(products, product_query, attributes)
            
            self._update_conversation(session_id, 'bot', response)
            return {
                'response': response,
                'session_id': session_id,
                'suggested_products': product_ids
            }
        
        # 3. Respuestas basadas en el tipo de mensaje
        
        # Respuestas para saludos
        if any(greeting in normalized_message for greeting in ['hola', 'buenos dias', 'buenas tardes', 'buenas noches', 'saludos']):
            response = "¡Hola! Soy el asistente virtual de Shoppit. ¿En qué puedo ayudarte hoy? Puedo ayudarte a encontrar productos, darte información sobre envíos, métodos de pago y más."
            self._update_conversation(session_id, 'bot', response)
            return {
                'response': response,
                'session_id': session_id,
                'suggested_products': []
            }
        
        # Respuestas para despedidas
        if any(farewell in normalized_message for farewell in ['adios', 'chao', 'hasta luego', 'nos vemos', 'gracias']):
            response = "¡Gracias por visitarnos! Si necesitas ayuda en el futuro, no dudes en volver a contactarme. ¡Que tengas un excelente día!"
            self._update_conversation(session_id, 'bot', response)
            return {
                'response': response,
                'session_id': session_id,
                'suggested_products': []
            }
        
        # Respuestas sobre envíos
        if any(shipping in normalized_message for shipping in ['envio', 'enviar', 'shipping', 'entrega', 'llega', 'cuando']):
            response = "Realizamos envíos a todo el país con tiempos de entrega de 3-5 días hábiles para la mayoría de las ciudades. Para zonas más remotas, el tiempo de entrega puede ser de hasta 7 días. El costo de envío se calcula automáticamente al finalizar tu compra y depende de la ubicación y el peso del paquete. Para compras superiores a $50, el envío es gratuito."
            self._update_conversation(session_id, 'bot', response)
            return {
                'response': response,
                'session_id': session_id,
                'suggested_products': []
            }
        
        # Respuestas sobre pagos
        if any(payment in normalized_message for payment in ['pago', 'pagar', 'tarjeta', 'metodo de pago', 'paypal', 'epayco']):
            response = "Aceptamos varios métodos de pago para tu comodidad:\n\n1. PayPal: para pagos seguros con tu cuenta PayPal o tarjeta\n2. ePayco: que acepta tarjetas de crédito y débito de cualquier banco\n\nTodas nuestras transacciones están encriptadas y son 100% seguras. Si tienes problemas con tu pago, nuestro equipo de atención al cliente está disponible para ayudarte."
            self._update_conversation(session_id, 'bot', response)
            return {
                'response': response,
                'session_id': session_id,
                'suggested_products': []
            }
        
        # Respuestas sobre devoluciones
        if any(return_query in normalized_message for return_query in ['devolucion', 'devolver', 'reembolso', 'cambio', 'garantia']):
            response = "Nuestra política de devoluciones te permite:\n\n1. Devolver cualquier producto dentro de los 14 días posteriores a la recepción con reembolso completo\n2. Solicitar cambios por talla, color u otro modelo sin costo adicional durante los primeros 30 días\n\nEl producto debe estar en su embalaje original y en perfectas condiciones. Para iniciar una devolución, solo debes ingresar a tu cuenta y seleccionar la opción 'Solicitar Devolución' en tu historial de pedidos."
            self._update_conversation(session_id, 'bot', response)
            return {
                'response': response,
                'session_id': session_id,
                'suggested_products': []
            }
        
        # Respuestas sobre la cuenta
        if any(account_query in normalized_message for account_query in ['cuenta', 'perfil', 'registrar', 'login', 'iniciar sesion', 'contrasena']):
            response = "Para gestionar tu cuenta en Shoppit:\n\n1. Para crear una cuenta: haz clic en 'Registrarse' en la esquina superior derecha\n2. Para iniciar sesión: utiliza el botón 'Iniciar sesión' con tu nombre de usuario y contraseña\n3. Para cambiar tu contraseña: ve a 'Mi Perfil' > 'Cambiar contraseña'\n\nSi olvidaste tu contraseña, puedes restablecerla haciendo clic en '¿Olvidaste tu contraseña?' en la página de inicio de sesión."
            self._update_conversation(session_id, 'bot', response)
            return {
                'response': response,
                'session_id': session_id,
                'suggested_products': []
            }
        
        # Respuesta por defecto contextual basada en el historial
        history = self._get_conversation_history(session_id)
        if history and len(history) > 1:
            last_bot_message = next((msg['text'] for msg in reversed(history[:-1]) if msg['role'] == 'bot'), None)
            
            if last_bot_message and "producto" in last_bot_message.lower():
                # El bot había mencionado productos, intentar buscar
                products = self.find_products(message)
                product_ids = [p.id for p in products]
                
                if products:
                    response = self._generate_product_response(products, message, {})
                    self._update_conversation(session_id, 'bot', response)
                    return {
                        'response': response,
                        'session_id': session_id,
                        'suggested_products': product_ids
                    }
        
        # Respuesta por defecto
        response = "Estoy aquí para ayudarte a encontrar lo que necesitas. Puedes preguntarme por productos específicos como 'Busco una camiseta roja', obtener información sobre envíos, pagos o devoluciones, o consultar el estado de tu cuenta. ¿En qué puedo ayudarte hoy?"
        self._update_conversation(session_id, 'bot', response)
        return {
            'response': response,
            'session_id': session_id,
            'suggested_products': []
        }