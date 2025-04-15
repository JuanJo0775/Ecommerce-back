from django.contrib import admin
from .chatbot_models import ChatbotFAQ, ChatbotConversation, ChatbotMessage

class ChatbotMessageInline(admin.TabularInline):
    model = ChatbotMessage
    extra = 0
    readonly_fields = ['sender', 'message', 'timestamp']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(ChatbotConversation)
class ChatbotConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'session_id', 'started_at', 'ended_at', 'feedback']
    list_filter = ['feedback', 'started_at']
    search_fields = ['user__username', 'session_id']
    readonly_fields = ['user', 'session_id', 'started_at']
    inlines = [ChatbotMessageInline]

@admin.register(ChatbotFAQ)
class ChatbotFAQAdmin(admin.ModelAdmin):
    list_display = ['question', 'category', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['question', 'answer', 'keywords']
    fieldsets = (
        (None, {
            'fields': ('question', 'answer', 'is_active')
        }),
        ('Clasificación', {
            'fields': ('category', 'keywords'),
            'description': 'Palabras clave separadas por comas que ayudan a identificar esta pregunta'
        }),
    )