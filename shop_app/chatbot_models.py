from django.db import models

class ChatbotFAQ(models.Model):
    """
    Modelo para almacenar preguntas frecuentes y sus respuestas.
    """
    question = models.CharField(max_length=255, verbose_name="Pregunta")
    keywords = models.TextField(verbose_name="Palabras clave", 
                          help_text="Palabras clave separadas por comas que ayudan a identificar esta pregunta")
    answer = models.TextField(verbose_name="Respuesta")
    category = models.CharField(max_length=100, blank=True, null=True, verbose_name="Categoría")
    is_active = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Pregunta frecuente"
        verbose_name_plural = "Preguntas frecuentes"
        
    def __str__(self):
        return self.question
        
    def get_keywords_list(self):
        """Retorna una lista de las palabras clave limpias."""
        if not self.keywords:
            return []
        return [keyword.strip().lower() for keyword in self.keywords.split(',')]


class ChatbotConversation(models.Model):
    """
    Modelo para almacenar conversaciones con el chatbot.
    """
    user = models.ForeignKey('core.CustomUser', on_delete=models.CASCADE, 
                            blank=True, null=True, related_name='chatbot_conversations')
    session_id = models.CharField(max_length=100, verbose_name="ID de sesión")
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(blank=True, null=True)
    feedback = models.IntegerField(blank=True, null=True, 
                                 help_text="Calificación del usuario (1-5)")
    
    class Meta:
        verbose_name = "Conversación"
        verbose_name_plural = "Conversaciones"
        
    def __str__(self):
        return f"Conversación {self.id} - {self.session_id[:10]}"


class ChatbotMessage(models.Model):
    """
    Modelo para almacenar mensajes individuales de las conversaciones.
    """
    SENDER_CHOICES = (
        ('user', 'Usuario'),
        ('bot', 'Chatbot'),
    )
    
    conversation = models.ForeignKey(ChatbotConversation, on_delete=models.CASCADE, 
                                    related_name='messages')
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Mensaje"
        verbose_name_plural = "Mensajes"
        ordering = ['timestamp']
        
    def __str__(self):
        return f"{self.sender}: {self.message[:30]}..."