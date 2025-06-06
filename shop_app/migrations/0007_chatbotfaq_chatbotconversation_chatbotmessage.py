# Generated by Django 5.1.7 on 2025-04-15 07:22

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop_app', '0006_transaction_epayco_id_transaction_payment_method_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ChatbotFAQ',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.CharField(max_length=255, verbose_name='Pregunta')),
                ('keywords', models.TextField(help_text='Palabras clave separadas por comas que ayudan a identificar esta pregunta', verbose_name='Palabras clave')),
                ('answer', models.TextField(verbose_name='Respuesta')),
                ('category', models.CharField(blank=True, max_length=100, null=True, verbose_name='Categoría')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activo')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Pregunta frecuente',
                'verbose_name_plural': 'Preguntas frecuentes',
            },
        ),
        migrations.CreateModel(
            name='ChatbotConversation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_id', models.CharField(max_length=100, verbose_name='ID de sesión')),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('ended_at', models.DateTimeField(blank=True, null=True)),
                ('feedback', models.IntegerField(blank=True, help_text='Calificación del usuario (1-5)', null=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='chatbot_conversations', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Conversación',
                'verbose_name_plural': 'Conversaciones',
            },
        ),
        migrations.CreateModel(
            name='ChatbotMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sender', models.CharField(choices=[('user', 'Usuario'), ('bot', 'Chatbot')], max_length=10)),
                ('message', models.TextField()),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('conversation', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='messages', to='shop_app.chatbotconversation')),
            ],
            options={
                'verbose_name': 'Mensaje',
                'verbose_name_plural': 'Mensajes',
                'ordering': ['timestamp'],
            },
        ),
    ]
