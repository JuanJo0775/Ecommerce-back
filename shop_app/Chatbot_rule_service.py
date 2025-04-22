import logging
import re
import uuid
import difflib
from django.db.models import Q
from .models import Product

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatbotService:
    """
    Servicio de chatbot con capacidad de procesamiento de lenguaje natural
    y búsqueda inteligente de productos mejorada con corrección ortográfica.
    """
    
    def __init__(self):
        # Diccionario de sinónimos para mejorar la búsqueda
        self.synonym_dict = {
            'camisa': ['camiseta', 'playera', 'remera', 'polo', 'blusa', 'franela', 'polera'],
            'camiseta': ['camisa', 'playera', 'remera', 'polo', 'blusa', 'franela', 'polera', 'camizeta'],
            'pantalon': ['pantalones', 'jeans', 'vaqueros', 'mezclilla', 'pants', 'leggins', 'pantalón', 'pantalonez'],
            'zapato': ['zapatos', 'calzado', 'tenis', 'zapatillas', 'sneakers', 'deportivos', 'sapato', 'sapatos'],
            'telefono': ['celular', 'movil', 'smartphone', 'iphone', 'android', 'telefono', 'teléfono', 'phone'],
            'computadora': ['computador', 'laptop', 'ordenador', 'portatil', 'pc', 'notebook', 'computacion', 'compu'],
            'television': ['tv', 'tele', 'televisor', 'pantalla', 'smart tv', 'led', 'television', 'televisión'],
            'auricular': ['audifonos', 'cascos', 'headphones', 'auriculares', 'earbuds', 'audifonos', 'audífonos']
        }
        
        # Diccionario de correcciones ortográficas comunes
        self.spelling_corrections = {
            'pantalon': ['pantalón', 'pantalones', 'pantalonez', 'pantaloons', 'pantallen'],
            'camisa': ['camiza', 'camsa', 'cmaisa', 'camsia', 'camia', 'camis'],
            'zapato': ['sapato', 'sapatos', 'zapatos', 'zapatoz', 'zapatto'],
            'telefono': ['telefono', 'teléfono', 'telephono', 'telefon', 'teleono', 'telofono'],
            'computadora': ['computador', 'computadorra', 'conputadora', 'computaora', 'cmputadora'],
            'televisor': ['television', 'televisión', 'tele', 'televicion', 'televisro', 'tevision'],
            'auricular': ['auriculares', 'auriculare', 'auricullar', 'auriclar', 'auicular'],
            'ropa': ['roppa', 'ropa', 'ropas', 'roppas', 'rope'],
            'camiseta': ['camisetta', 'camiseta', 'camizeta', 'camisetta', 'camisata', 'camieta'],
            'jeans': ['jins', 'jeans', 'jeanes', 'yins', 'gins', 'jens', 'jins']
        }
        
        # Lista plana de todas las palabras para búsqueda difusa
        self.all_product_terms = []
        for key, values in self.synonym_dict.items():
            self.all_product_terms.append(key)
            self.all_product_terms.extend(values)
        for key, values in self.spelling_corrections.items():
            if key not in self.all_product_terms:
                self.all_product_terms.append(key)
            for value in values:
                if value not in self.all_product_terms:
                    self.all_product_terms.append(value)
        
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
            r'(?:me gustaria|quisiera|me encantaria)\s+(?:ver|comprar)\s+(?:un|una|unos|unas)?\s+([^?.,!;]+)',
            r'(?:tienes?|tienen)\s+([^?.,!;]+)',
            r'(?:quiero ver|muestrame|enseñame)\s+([^?.,!;]+)',
            r'(?:buscame|encuentrame)\s+([^?.,!;]+)'
        ]
        
        # Patrones para detectar saludos
        self.greeting_patterns = [
            r'^hola',
            r'^buenos dias',
            r'^buenas tardes',
            r'^buenas noches',
            r'^saludos',
            r'^hey',
            r'^hi',
            r'^hello',
            r'^qué tal',
            r'^como estas',
            r'^buen día'
        ]
        
        # Patrones para detectar despedidas
        self.farewell_patterns = [
            r'adios',
            r'hasta luego',
            r'hasta pronto',
            r'chao',
            r'nos vemos',
            r'bye',
            r'hasta mañana',
            r'que tengas',
            r'me voy',
            r'me retiro'
        ]
        
        # Patrones para detectar agradecimientos
        self.gratitude_patterns = [
            r'gracias',
            r'te agradezco',
            r'muchas gracias',
            r'agradecido',
            r'thank you',
            r'thanks'
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
    
    def _find_similar_word(self, word, min_score=0.6):
        """
        Encuentra palabras similares usando coincidencia difusa.
        Útil para corregir errores ortográficos.
        """
        if len(word) <= 2:  # Ignorar palabras muy cortas
            return word
            
        # Primero verificar si es una palabra clave o ya conocida
        if word in self.all_product_terms:
            return word
            
        # Si está en el diccionario de correcciones, devolver la forma correcta
        for correct, misspelled in self.spelling_corrections.items():
            if word in misspelled:
                return correct
                
        # Usar difflib para encontrar palabras similares
        matches = difflib.get_close_matches(word, self.all_product_terms, n=1, cutoff=min_score)
        
        if matches:
            return matches[0]
            
        return word  # Si no hay coincidencias, devolver la palabra original
    
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
        words = normalized_message.split()
        corrected_words = [self._find_similar_word(word) for word in words]
        
        # Buscar en términos conocidos de productos
        for category, terms in self.categories.items():
            for term in terms:
                # Verificar original y correcciones
                if term in words or term in corrected_words:
                    # Buscar qué está pidiendo alrededor de este término
                    idx = corrected_words.index(term) if term in corrected_words else words.index(term)
                    start = max(0, idx - 3)
                    end = min(len(words), idx + 4)
                    return ' '.join(words[start:end])
        
        # Verificar si alguna palabra del mensaje es similar a una palabra clave de producto
        for word in words:
            similar = self._find_similar_word(word)
            if similar != word:  # Si se encontró una corrección
                # Es probable que esté buscando un producto
                start = max(0, words.index(word) - 2)
                end = min(len(words), words.index(word) + 3)
                return ' '.join(words[start:end])
        
        # Si no se detecta nada, devolver None
        return None
    
    def _expand_search_terms(self, terms):
        """Expande los términos de búsqueda con sinónimos y correcciones"""
        expanded_terms = []
        
        for term in terms:
            # Añadir el término original
            expanded_terms.append(term)
            
            # Añadir término corregido si es diferente
            corrected = self._find_similar_word(term)
            if corrected != term:
                expanded_terms.append(corrected)
            
            # Buscar en el diccionario de sinónimos
            for key, synonyms in self.synonym_dict.items():
                # Si el término o su corrección está en los sinónimos
                if term in synonyms or corrected in synonyms:
                    expanded_terms.append(key)
                    expanded_terms.extend(synonyms)
                # O si el término es la palabra clave, añadir sus sinónimos
                elif term == key or corrected == key:
                    expanded_terms.extend(synonyms)
        
        return list(set(expanded_terms))  # Eliminar duplicados
    
    def _identify_categories(self, query):
        """Identifica posibles categorías en la consulta"""
        normalized_query = self._normalize_text(query)
        words = normalized_query.split()
        
        # Corregir palabras mal escritas
        corrected_words = [self._find_similar_word(word) for word in words]
        
        potential_categories = []
        
        # Buscar coincidencias con palabras originales y corregidas
        all_words = set(words + corrected_words)
        for word in all_words:
            for category, keywords in self.categories.items():
                if word in keywords or any(word in self._expand_search_terms([keyword]) for keyword in keywords):
                    potential_categories.append(category)
        
        return list(set(potential_categories))
    
    def find_products(self, query):
        """
        Búsqueda inteligente de productos que entiende lenguaje natural
        y tolera errores ortográficos.
        """
        if not query or len(query) < 3:
            return []
            
        # Normalizar y dividir la consulta en palabras
        normalized_query = self._normalize_text(query)
        words = normalized_query.split()
        
        # Corregir palabras mal escritas
        corrected_words = [self._find_similar_word(word) for word in words]
        
        # Filtrar palabras comunes demasiado cortas
        common_words = ['el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 'de', 'que', 'es', 'en', 'para', 'con', 'por', 'sin', 'como', 'mas', 'muy']
        search_words = [word for word in words if word not in common_words and len(word) > 2]
        corrected_search_words = [word for word in corrected_words if word not in common_words and len(word) > 2]
        
        # Combinar palabras originales y corregidas
        all_search_words = list(set(search_words + corrected_search_words))
        
        if not all_search_words:
            return []
        
        # Extraer atributos específicos (color, talla, etc.)
        attributes = self._extract_product_attributes(query)
        
        # Expandir términos de búsqueda con sinónimos
        expanded_terms = self._expand_search_terms(all_search_words)
        
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
                # Dar prioridad a resultados que coinciden con la categoría
                # pero no limitar solo a ellos
                #combined_filter = combined_filter & category_filter
                combined_filter = combined_filter
            else:
                combined_filter = category_filter
        
        if attr_filter:
            if combined_filter:
                # También dar mayor relevancia a atributos pero no limitar solo a ellos
                #combined_filter = combined_filter & attr_filter
                combined_filter = combined_filter
            else:
                combined_filter = attr_filter
        
        if not combined_filter:
            return []
            
        # Obtener productos
        try:
            # Intentar buscar con el filtro combinado
            products = list(Product.objects.filter(combined_filter).distinct()[:12])
            
            # Si no hay suficientes resultados, ampliar la búsqueda
            if len(products) < 3:
                # Probar solo con palabras corregidas para una búsqueda más efectiva
                corrected_filter = None
                for term in corrected_search_words:
                    if corrected_filter is None:
                        corrected_filter = Q(name__icontains=term) | Q(description__icontains=term)
                    else:
                        corrected_filter |= Q(name__icontains=term) | Q(description__icontains=term)
                
                if corrected_filter:
                    corrected_products = list(Product.objects.filter(corrected_filter).distinct()[:8])
                    # Añadir productos que no estén ya en la lista
                    for product in corrected_products:
                        if product not in products:
                            products.append(product)
                
                # Si todavía no hay suficientes, buscar por categoría
                if len(products) < 3 and categories:
                    category_products = list(Product.objects.filter(category__icontains=categories[0])[:8])
                    # Añadir productos que no estén ya en la lista
                    for product in category_products:
                        if product not in products:
                            products.append(product)
            
            return products
        except Exception as e:
            logger.error(f"Error al buscar productos: {e}")
            return []
    
    def _format_products_nicely(self, products):
        """
        Formatea una lista de productos de una manera más presentable y organizada.
        Agrupa por categorías y presenta de manera más natural.
        """
        if not products:
            return "No he encontrado productos que coincidan con tu búsqueda."
        
        formatted_text = ""
        
        # Si hay pocos productos, mostrarlos todos con más detalles
        if len(products) <= 3:
            formatted_text = "He encontrado los siguientes productos:\n\n"
            for i, product in enumerate(products, 1):
                formatted_text += f"**{i}. {product.name}**\n"
                formatted_text += f"   Precio: ${product.price}\n"
                if hasattr(product, 'category') and product.category:
                    formatted_text += f"   Categoría: {product.category}\n"
                if product.description:
                    # Limitar descripción a 100 caracteres
                    short_desc = product.description[:100] + "..." if len(product.description) > 100 else product.description
                    formatted_text += f"   Descripción: {short_desc}\n"
                formatted_text += "\n"
        else:
            # Agrupar por categoría si hay muchos productos
            categories = {}
            uncategorized = []
            
            for product in products:
                if hasattr(product, 'category') and product.category:
                    if product.category not in categories:
                        categories[product.category] = []
                    categories[product.category].append(product)
                else:
                    uncategorized.append(product)
            
            # Primero mostrar productos agrupados por categoría
            if categories:
                formatted_text = "He encontrado productos en las siguientes categorías:\n\n"
                
                for category, cat_products in categories.items():
                    formatted_text += f"**{category.capitalize()}:**\n"
                    for i, product in enumerate(cat_products[:4], 1):  # Limitar a 4 por categoría
                        formatted_text += f"{i}. {product.name} - ${product.price}\n"
                    
                    if len(cat_products) > 4:
                        formatted_text += f"   Y {len(cat_products) - 4} productos más en esta categoría.\n"
                    
                    formatted_text += "\n"
            
            # Luego mostrar productos sin categoría
            if uncategorized:
                if not categories:  # Si solo hay productos sin categoría
                    formatted_text = "He encontrado los siguientes productos:\n\n"
                else:
                    formatted_text += "**Otros productos:**\n"
                
                for i, product in enumerate(uncategorized[:5], 1):
                    formatted_text += f"{i}. {product.name} - ${product.price}\n"
                
                if len(uncategorized) > 5:
                    formatted_text += f"Y {len(uncategorized) - 5} productos más.\n"
        
        formatted_text += "\n¿Te gustaría más información sobre alguno de estos productos?"
        return formatted_text
    
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
        
        # Formato mejorado para la presentación de productos
        return self._format_products_nicely(products)
    
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
    
    def _process_specific_product_query(self, message, session_id):
        """
        Procesa consultas sobre productos específicos basándose en el historial
        de la conversación. Por ejemplo, si el bot mostró una lista de productos
        y el usuario pregunta por el primero.
        """
        history = self._get_conversation_history(session_id)
        if not history or len(history) < 2:
            return None
            
        normalized_message = self._normalize_text(message)
        
        # Patrones para detectar preguntas sobre productos mencionados anteriormente
        specific_product_patterns = [
            r'(?:quiero|me interesa|dame|dime)?\s*(?:mas|más) (?:informacion|información|detalles|datos) (?:sobre|del|de la|acerca del?)?\s*(?:producto|articulo|artículo|item)?\s*(?:numero|número|#)?\s*(\d+)',
            r'(?:quiero|me interesa|dame|dime)?\s*(?:mas|más) (?:informacion|información|detalles|datos) (?:sobre|del|de la|acerca del?)?\s*(?:el|la|los|las)\s+(.+?)(?:\s+por favor|\s*\?|\s*\.|\s*$)',
            r'(?:háblame|cuentame|dime|explícame|muestrame|quiero saber) (?:mas|más) (?:sobre|del|de la|acerca de)?\s*(?:el|la|los|las)?\s*(.+?)(?:\s+por favor|\s*\?|\s*\.|\s*$)',
            r'(?:el|la) (?:producto|articulo|artículo|item) (?:numero|número|#)?\s*(\d+)',
            r'(?:me interesa|quiero) (?:el|la) (?:producto|articulo|artículo|item) (?:numero|número|#)?\s*(\d+)',
        ]
        
        last_bot_message = next((msg['text'] for msg in reversed(history[:-1]) if msg['role'] == 'bot'), None)
        if not last_bot_message:
            return None
            
        # Verificar si el último mensaje del bot contenía productos
        if "producto" not in last_bot_message.lower() and "encontrado" not in last_bot_message.lower():
            return None
            
        # Verificar si el usuario está preguntando por un producto específico por número
        for pattern in specific_product_patterns:
            match = re.search(pattern, normalized_message)
            if match:
                product_identifier = match.group(1)
                # Si es un número, podría ser el índice de un producto listado
                if product_identifier.isdigit():
                    product_index = int(product_identifier)
                    # Extraer productos mencionados en el último mensaje
                    products = []
                    lines = last_bot_message.split('\n')
                    for line in lines:
                        if re.match(r'^\d+\.', line.strip()):  # Línea que comienza con número
                            products.append(line)
                    
                    if 0 < product_index <= len(products):
                        selected_product = products[product_index - 1]
                        # Extraer nombre del producto (aproximado)
                        product_name_match = re.search(r'\d+\.\s+(.+?)(?:\s+-\s+\$|\s*$)', selected_product)
                        if product_name_match:
                            product_name = product_name_match.group(1).strip()
                            return f"Buscando más información sobre: {product_name}"
                else:
                    # Si no es un número, el usuario podría estar refiriéndose a un producto por nombre
                    product_name = product_identifier.strip()
                    if len(product_name) > 2:  # Si el nombre tiene suficiente longitud
                        return f"Buscando más información sobre: {product_name}"
        
        return None
    
    def _get_product_detail(self, product_name):
        """
        Busca un producto específico por nombre y devuelve información detallada.
        """
        normalized_name = self._normalize_text(product_name)
        words = normalized_name.split()
        
        # Crear filtro de búsqueda con todas las palabras
        query_filter = None
        for word in words:
            if len(word) > 2:  # Ignorar palabras muy cortas
                if query_filter is None:
                    query_filter = Q(name__icontains=word)
                else:
                    query_filter &= Q(name__icontains=word)
        
        if not query_filter:
            return None
            
        try:
            # Intentar encontrar productos que coincidan con todas las palabras
            products = Product.objects.filter(query_filter)[:3]
            
            if not products:
                # Si no hay resultados, buscar con coincidencia parcial
                partial_filter = None
                for word in words:
                    if len(word) > 2:
                        if partial_filter is None:
                            partial_filter = Q(name__icontains=word)
                        else:
                            partial_filter |= Q(name__icontains=word)
                
                products = Product.objects.filter(partial_filter)[:3]
            
            if products:
                # Formatear la respuesta con detalles del producto
                product = products[0]  # Usar el primer resultado
                response = f"**{product.name}**\n\n"
                response += f"**Precio:** ${product.price}\n"
                if product.description:
                    response += f"**Descripción:** {product.description}\n\n"
                if hasattr(product, 'category') and product.category:
                    response += f"**Categoría:** {product.category}\n"
                
                # Si hay más resultados, sugerirlos
                if len(products) > 1:
                    response += "\n**Productos similares:**\n"
                    for i, similar in enumerate(products[1:], 1):
                        response += f"{i}. {similar.name} - ${similar.price}\n"
                
                return response
            
            return None
        except Exception as e:
            logger.error(f"Error al buscar detalles del producto: {e}")
            return None
    
    def _check_pattern_match(self, text, patterns):
        """Verifica si el texto coincide con alguno de los patrones."""
        normalized = self._normalize_text(text)
        for pattern in patterns:
            if re.search(pattern, normalized):
                return True
        return False
    
    def _generate_greeting_response(self):
        """Genera una respuesta para saludos."""
        greetings = [
            "¡Hola! Soy el asistente virtual de Shoppit. ¿En qué puedo ayudarte hoy?",
            "¡Bienvenido/a a Shoppit! Estoy aquí para ayudarte a encontrar lo que necesitas.",
            "Hola, ¿cómo puedo asistirte hoy? Puedes preguntarme sobre productos, pedidos o formas de pago.",
            "¡Saludos! Soy el asistente de Shoppit. ¿Qué estás buscando hoy?",
            "Hola, ¿en qué puedo ayudarte? Puedes buscar productos o hacer preguntas sobre nuestra tienda."
        ]
        return greetings[hash(str(uuid.uuid4())) % len(greetings)]
    
    def _generate_farewell_response(self):
        """Genera una respuesta para despedidas."""
        farewells = [
            "¡Hasta pronto! Recuerda que estoy aquí para ayudarte cuando lo necesites.",
            "¡Adiós! Gracias por visitar Shoppit. ¡Te esperamos de nuevo!",
            "¡Que tengas un buen día! Estamos para servirte cuando nos necesites.",
            "¡Hasta luego! No dudes en volver si necesitas más información.",
            "¡Adiós! Ha sido un placer ayudarte. Vuelve pronto a Shoppit."
        ]
        return farewells[hash(str(uuid.uuid4())) % len(farewells)]
    
    def _generate_gratitude_response(self):
        """Genera una respuesta para agradecimientos."""
        gratitudes = [
            "¡De nada! Estoy aquí para ayudarte. ¿Necesitas algo más?",
            "¡Es un placer! ¿Hay algo más en lo que pueda asistirte?",
            "No hay de qué. Siempre es un gusto poder ayudarte. ¿Puedo hacer algo más por ti?",
            "Para eso estoy. ¿Hay algo más que quieras saber?",
            "¡Encantado de poder ayudarte! Si tienes más preguntas, no dudes en hacerlas."
        ]
        return gratitudes[hash(str(uuid.uuid4())) % len(gratitudes)]
    
    def _generate_help_message(self):
        """Genera un mensaje de ayuda con ejemplos de cosas que puede hacer el chatbot."""
        help_message = "Puedo ayudarte con varias cosas en Shoppit. Aquí tienes algunos ejemplos de lo que puedes preguntarme:\n\n"
        help_message += "**Búsqueda de productos:**\n"
        help_message += "- Busco una camiseta roja\n"
        help_message += "- ¿Tienes teléfonos Samsung?\n"
        help_message += "- Muéstrame zapatos deportivos\n\n"
        
        help_message += "**Información general:**\n"
        help_message += "- ¿Cómo funciona el envío?\n"
        help_message += "- ¿Cuáles son las formas de pago?\n"
        help_message += "- ¿Tienen política de devoluciones?\n\n"
        
        help_message += "- Para consultas más específicas, intenta describir lo que buscas con detalles como color, tamaño, marca o categoría."
        
        return help_message
    
    def process_message(self, message, session_id=None):
        """
        Método principal que procesa los mensajes del usuario y genera respuestas.
        """
        if not session_id:
            session_id = str(uuid.uuid4())
            
        # Normalizar mensaje
        normalized_message = self._normalize_text(message)
        
        # Guardar mensaje en el historial
        self._update_conversation(session_id, 'user', message)
        
        # Verificar si es un saludo
        if self._check_pattern_match(message, self.greeting_patterns):
            response = self._generate_greeting_response()
            self._update_conversation(session_id, 'bot', response)
            return {
                'response': response,
                'session_id': session_id,
                'suggested_products': []
            }
        
        # Verificar si es una despedida
        if self._check_pattern_match(message, self.farewell_patterns):
            response = self._generate_farewell_response()
            self._update_conversation(session_id, 'bot', response)
            return {
                'response': response,
                'session_id': session_id,
                'suggested_products': []
            }
        
        # Verificar si es un agradecimiento
        if self._check_pattern_match(message, self.gratitude_patterns):
            response = self._generate_gratitude_response()
            self._update_conversation(session_id, 'bot', response)
            return {
                'response': response,
                'session_id': session_id,
                'suggested_products': []
            }
        
        # Verificar si es una pregunta de ayuda general
        help_patterns = [
            r'(?:ayuda|ayudame|puedes ayudarme|como funciona|qué puedes hacer|que sabes hacer)',
            r'(?:qué puedo preguntar|ayuda|instrucciones|guía|tutorial)'
        ]
        if self._check_pattern_match(message, help_patterns):
            response = self._generate_help_message()
            self._update_conversation(session_id, 'bot', response)
            return {
                'response': response,
                'session_id': session_id,
                'suggested_products': []
            }
        
        # Verificar si es una pregunta sobre un producto específico
        specific_product_query = self._process_specific_product_query(message, session_id)
        if specific_product_query:
            # Extraer nombre del producto
            product_name = specific_product_query.replace("Buscando más información sobre: ", "")
            # Buscar información detallada
            product_detail = self._get_product_detail(product_name)
            
            if product_detail:
                self._update_conversation(session_id, 'bot', product_detail)
                return {
                    'response': product_detail,
                    'session_id': session_id,
                    'suggested_products': []  # Aquí se podrían incluir IDs de productos relacionados
                }
            else:
                # Si no se encuentra el producto específico, buscar similares
                similar_products = self.find_products(product_name)
                if similar_products:
                    response = f"No encontré exactamente '{product_name}', pero he encontrado estos productos similares:\n\n"
                    response += self._format_products_nicely(similar_products)
                else:
                    response = f"Lo siento, no he encontrado información del producto '{product_name}'. ¿Podrías describirlo de otra manera?"
                
                self._update_conversation(session_id, 'bot', response)
                product_ids = [p.id for p in similar_products] if similar_products else []
                return {
                    'response': response,
                    'session_id': session_id,
                    'suggested_products': product_ids
                }
        
        # Verificar si coincide con una FAQ
        faq_answer = self._find_matching_faq(message)
        if faq_answer:
            self._update_conversation(session_id, 'bot', faq_answer)
            return {
                'response': faq_answer,
                'session_id': session_id,
                'suggested_products': []
            }
        
        # Verificar si es una búsqueda de producto
        product_query = self._extract_product_query(message)
        if product_query:
            # Buscar productos
            products = self.find_products(product_query)
            # Extraer atributos para personalizar respuesta
            attributes = self._extract_product_attributes(message)
            # Generar respuesta
            response = self._generate_product_response(products, product_query, attributes)
            
            self._update_conversation(session_id, 'bot', response)
            product_ids = [p.id for p in products] if products else []
            return {
                'response': response,
                'session_id': session_id,
                'suggested_products': product_ids
            }
        
        # Si no coincide con ningún patrón conocido
        fallback_responses = [
            "Lo siento, no estoy seguro de entender tu consulta. ¿Podrías reformularla o ser más específico?",
            "No he podido procesar tu solicitud. Puedes preguntarme sobre productos, envíos, pagos o devoluciones.",
            "No he entendido lo que necesitas. ¿Estás buscando algún producto en particular o tienes alguna consulta sobre nuestra tienda?",
            "Disculpa, no he comprendido tu pregunta. ¿Te gustaría buscar algún producto específico?",
            "No estoy seguro de lo que estás preguntando. ¿Puedo ayudarte a encontrar algún producto o responder a alguna consulta sobre la tienda?"
        ]
        
        response = fallback_responses[hash(normalized_message) % len(fallback_responses)]
        self._update_conversation(session_id, 'bot', response)
        
        return {
            'response': response,
            'session_id': session_id,
            'suggested_products': []
        }