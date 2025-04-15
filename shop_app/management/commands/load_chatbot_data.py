from django.core.management.base import BaseCommand
from shop_app.chatbot_models import ChatbotFAQ

class Command(BaseCommand):
    help = 'Carga preguntas frecuentes predefinidas para el chatbot'

    def handle(self, *args, **options):
        # Lista de FAQs predefinidas
        faqs = [
            {
                'question': '¿Cómo realizo una compra?',
                'keywords': 'compra,comprar,adquirir,proceso,cómo,como,realizar',
                'answer': 'Para realizar una compra sigue estos pasos:\n1. Navega por nuestro catálogo y elige los productos que deseas.\n2. Haz clic en "Añadir al carrito".\n3. Cuando estés listo, haz clic en el ícono del carrito en la esquina superior derecha.\n4. Revisa tu pedido y haz clic en "Proceder a la compra".\n5. Inicia sesión o regístrate si aún no lo has hecho.\n6. Introduce la información de envío y pago.\n7. Confirma tu pedido y ¡listo!',
                'category': 'Compras'
            },
            {
                'question': '¿Cuáles son los métodos de pago disponibles?',
                'keywords': 'pago,métodos,formas,tarjeta,crédito,débito,paypal,epayco',
                'answer': 'En Shoppit aceptamos los siguientes métodos de pago:\n- PayPal\n- ePayco (tarjetas de crédito y débito)\n\nTodas las transacciones son seguras y encriptadas para garantizar la protección de tu información bancaria.',
                'category': 'Pagos'
            },
            {
                'question': '¿Cómo puedo seguir el estado de mi pedido?',
                'keywords': 'seguir,tracking,pedido,orden,estado,entrega',
                'answer': 'Para seguir el estado de tu pedido, inicia sesión en tu cuenta y ve a la sección "Mi Perfil". Allí encontrarás el "Historial de órdenes" donde podrás ver todos tus pedidos y su estado actual.',
                'category': 'Pedidos'
            },
            {
                'question': '¿Cuánto tiempo tarda en llegar mi pedido?',
                'keywords': 'tiempo,entrega,envío,tarda,recibir,llegada,shipping',
                'answer': 'El tiempo de entrega estándar es de 3-5 días hábiles para la mayoría de las ciudades principales. Para zonas rurales o alejadas, el tiempo puede extenderse hasta 7-10 días hábiles. Una vez procesado tu pedido, recibirás un correo electrónico con la información de seguimiento.',
                'category': 'Envíos'
            },
            {
                'question': '¿Cómo puedo cambiar o cancelar mi pedido?',
                'keywords': 'cambiar,modificar,cancelar,pedido,orden,devolución',
                'answer': 'Si necesitas cambiar o cancelar tu pedido, debes contactarnos lo antes posible a través de nuestro correo electrónico soporte@shoppit.com. Ten en cuenta que solo podemos modificar o cancelar pedidos que aún no hayan sido procesados para envío.',
                'category': 'Pedidos'
            },
            {
                'question': '¿Tienen política de devoluciones?',
                'keywords': 'devolución,devolver,cambio,reembolso,garantía',
                'answer': 'Sí, contamos con una política de devoluciones. Tienes 14 días desde la recepción del producto para solicitar una devolución. El producto debe estar en su embalaje original y en perfectas condiciones. Para iniciar un proceso de devolución, ve a "Mi Perfil" > "Mis Pedidos" y selecciona la opción "Solicitar Devolución".',
                'category': 'Devoluciones'
            },
            {
                'question': '¿Cómo puedo crear una cuenta?',
                'keywords': 'cuenta,crear,registro,registrar,usuario',
                'answer': 'Para crear una cuenta en Shoppit, haz clic en "Registrarse" en la esquina superior derecha de la página. Completa el formulario con tu información personal y credenciales. Recibirás un correo electrónico de confirmación para verificar tu cuenta.',
                'category': 'Cuenta'
            },
            {
                'question': '¿Cómo puedo cambiar mi contraseña?',
                'keywords': 'contraseña,clave,cambiar,olvidé,recuperar,password',
                'answer': 'Para cambiar tu contraseña, inicia sesión en tu cuenta y ve a "Mi Perfil" > "Cambiar contraseña". Si has olvidado tu contraseña, haz clic en "¿Olvidó su contraseña?" en la página de inicio de sesión y sigue las instrucciones enviadas a tu correo electrónico.',
                'category': 'Cuenta'
            },
            {
                'question': '¿Puedo modificar mis datos personales?',
                'keywords': 'datos,personales,modificar,editar,actualizar,información',
                'answer': 'Sí, puedes modificar tus datos personales. Inicia sesión en tu cuenta, ve a "Mi Perfil" y haz clic en "Editar Perfil". Allí podrás actualizar tu nombre, dirección, número de teléfono y otros datos personales.',
                'category': 'Cuenta'
            },
            {
                'question': '¿Qué hago si un producto llega dañado?',
                'keywords': 'dañado,defectuoso,roto,malo,problema,producto',
                'answer': 'Si recibes un producto dañado o defectuoso, contáctanos dentro de las 48 horas posteriores a la recepción a través de soporte@shoppit.com. Adjunta fotos del producto dañado y del embalaje. Organizaremos la devolución y el reemplazo sin costo adicional para ti.',
                'category': 'Problemas'
            },
            {
                'question': '¿Tienen servicio al cliente?',
                'keywords': 'servicio,cliente,atención,contacto,ayuda,soporte',
                'answer': 'Sí, contamos con servicio al cliente disponible de lunes a viernes de 9:00 a 18:00 horas. Puedes contactarnos a través de soporte@shoppit.com o utilizando el chat en línea en nuestra página web.',
                'category': 'Contacto'
            },
            {
                'question': '¿Realizan envíos internacionales?',
                'keywords': 'internacional,extranjero,fuera,otro,país,envio',
                'answer': 'Actualmente solo realizamos envíos dentro del territorio nacional. Estamos trabajando para expandir nuestros servicios a nivel internacional en un futuro próximo.',
                'category': 'Envíos'
            },
            {
                'question': '¿Cómo encuentro productos específicos?',
                'keywords': 'buscar,encontrar,búsqueda,producto,específico,categoría',
                'answer': 'Puedes utilizar la barra de búsqueda ubicada en la parte superior de nuestra página web para buscar productos específicos. También puedes navegar por categorías haciendo clic en las opciones del menú principal o filtrar los resultados por precio, popularidad o novedades.',
                'category': 'Navegación'
            },
            {
                'question': '¿Tienen descuentos o promociones?',
                'keywords': 'descuento,promoción,oferta,cupón,código,rebaja',
                'answer': 'Sí, regularmente ofrecemos descuentos y promociones especiales. Te recomendamos suscribirte a nuestro boletín de noticias para ser el primero en enterarte de nuestras ofertas. También puedes seguirnos en redes sociales donde anunciamos promociones exclusivas.',
                'category': 'Promociones'
            },
            {
                'question': '¿Puedo comprar sin crear una cuenta?',
                'keywords': 'comprar,sin,cuenta,registro,invitado,anónimo',
                'answer': 'Para garantizar la seguridad de las transacciones y permitir el seguimiento adecuado de los pedidos, es necesario tener una cuenta para realizar compras en Shoppit. El proceso de registro es rápido y sencillo, solo necesitas un correo electrónico válido.',
                'category': 'Compras'
            }
        ]
        
        # Contador para FAQs creadas y actualizadas
        created_count = 0
        updated_count = 0
        
        for faq_data in faqs:
            # Intentar encontrar FAQ existente con la misma pregunta
            faq, created = ChatbotFAQ.objects.update_or_create(
                question=faq_data['question'],
                defaults={
                    'keywords': faq_data['keywords'],
                    'answer': faq_data['answer'],
                    'category': faq_data['category'],
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
            else:
                updated_count += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'Carga de datos completada: {created_count} FAQs creadas, {updated_count} FAQs actualizadas.'
        ))