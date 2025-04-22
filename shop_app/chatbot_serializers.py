from rest_framework import serializers
from .chatbot_models import ChatbotFAQ, ChatbotConversation, ChatbotMessage
from .models import Product

class ChatbotMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatbotMessage
        fields = ['id', 'sender', 'message', 'timestamp']


class ChatbotConversationSerializer(serializers.ModelSerializer):
    messages = ChatbotMessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = ChatbotConversation
        fields = ['id', 'session_id', 'started_at', 'ended_at', 'messages']


class ChatbotFAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatbotFAQ
        fields = ['id', 'question', 'answer', 'category', 'keywords']
        

class ChatbotMessageInputSerializer(serializers.Serializer):
    message = serializers.CharField(required=True)
    session_id = serializers.CharField(required=False)
    use_ai = serializers.BooleanField(required=False, default=True)
    

class ChatbotResponseSerializer(serializers.Serializer):
    response = serializers.CharField()
    session_id = serializers.CharField()
    suggested_products = serializers.ListField(required=False, child=serializers.IntegerField())