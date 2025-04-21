# shop_app/langchain_service.py
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from .models import Product
from django.db.models import Q

# Cargar variables de entorno
load_dotenv()

class LangChainService:
    """Servicio para manejar conversaciones con LangChain y OpenAI."""
    
    def __init__(self):
        # Inicializar el modelo de lenguaje
        self.llm = ChatOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name="gpt-3.5-turbo",
            temperature=0.7
        )
        
        # Plantilla para el prompt
        self.template = """
        Eres un asistente virtual amigable para la tienda online 'La Tienda Incorrecta'. 
        Tu objetivo es ayudar a los clientes con información sobre productos, 
        proceso de compra, envíos, devoluciones y cualquier otra consulta relacionada con la tienda.

        Contexto sobre La Tienda Incorrecta:
        🐸 TIENDA DE COSAS FEAS A PROPÓSITO
        La estética de lo antiestético. Feo, raro, mal hecho... pero con estilo.
        Bienvenido a un universo donde el buen gusto es cuestionable, pero la actitud es impecable. Aquí celebramos lo roto, lo imperfecto, lo raro. Esta no es una tienda para todo el mundo. Es para los que miran algo y piensan: "esto es tan feo que es hermoso".

        🧷 CATEGORÍAS DE PRODUCTOS
        👕 Ropa Fea con Intención
        Descripción: Prendas hechas para incomodar al ojo tradicional, pero encantar a quien aprecia el caos.
        Productos destacados:

        Camisetas con costuras torcidas y etiquetas visibles como parte del diseño.

        Sweaters con agujeros “casuales” y mezclas de colores que “no combinan”.

        Faldas con doble cintura o tres cremalleras que no abren nada.

        Calcetines de diferentes pares vendidos así a propósito.

        Todo lo que tu madre diría que está mal hecho. Justo lo que querías.

        🏺 Arte Raro y Cerámica Feísta
        Descripción: Figuras, objetos y esculturas con formas toscas, bizarras o simplemente incómodas.
        Productos destacados:

        Vasijas que parecen derretidas.

        Figuritas con ojos mal puestos, manos de más o proporciones imposibles.

        Tazas que funcionan, pero parecen sacadas de un sueño febril.

        Platos “rompidos” y reconstruidos con oro falso (inspirados en el kintsugi… pero al revés).

        🖼️ Decoración Glitch y Visual Antiestético
        Descripción: Piezas gráficas y de decoración que exploran el error como arte.
        Productos destacados:

        Posters glitch con colores saturados y distorsión digital.

        Cuadros con frases que no tienen sentido o están mal escritas (intencional).

        Espejos deformados que reflejan realidades alternativas.

        Almohadas con patrones incómodos: caras mal impresas, ojos que te siguen, texturas visuales “molestas”.

        🎁 Accesorios de Mal Gusto Elegante
        Descripción: Pequeños objetos que la gente no sabe si odiar o amar.
        Productos destacados:

        Bolsos con forma de órganos (corazón, pulmón, etc.).

        Anillos de arcilla que parecen derretirse en tu dedo.

        Aretes con formas inexplicables: una llave, un diente, un pez sin ojo.

        Gafas con un lente redondo y otro cuadrado.

        Llaveros que chillan cuando los aprietas (sin razón alguna).

        Historial de la conversación:
        {history}
        
        Consulta actual: {input}
        
        Respuesta amigable:
        """
        
        # Memoria para la conversación
        self.memory = ConversationBufferMemory(return_messages=True)
        
        # Crear prompt
        self.prompt = PromptTemplate.from_template(self.template)
        
        # Crear cadena de conversación
        self.conversation = ConversationChain(
            llm=self.llm,
            memory=self.memory,
            prompt=self.prompt,
            verbose=True
        )
    
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
        products = Product.objects.filter(query_filter)[:5]
        return list(products)
    
    def process_message(self, message, session_id=None):
        """Procesa un mensaje del usuario y devuelve una respuesta."""
        # Obtener respuesta del modelo
        response = self.conversation.predict(input=message)
        
        # Buscar productos relacionados con la consulta
        related_products = self.find_products(message)
        product_ids = [p.id for p in related_products]
        
        return {
            'response': response,
            'session_id': session_id or 'new_session',
            'suggested_products': product_ids
        }