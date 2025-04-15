from django.contrib import admin
from .models import Product, Cart, CartItem, Transaction

# Importar configuración admin del chatbot
from .chatbot_admin import ChatbotFAQAdmin, ChatbotConversationAdmin

# Register your models here.
admin.site.register([Product, Cart, CartItem, Transaction])