from django.urls import path
from . import views
from . import chatbot_views

urlpatterns = [
    path("products", views.products, name="products"),
    path("product_detail/<slug:slug>", views.product_detail, name="product_detail"),
    path("add_item/", views.add_item, name="add_item"),
    path("product_in_cart", views.product_in_cart, name="product_in_cart"),
    path("get_cart_stat", views.get_cart_stat, name="get_cart_stat"),
    path("get_cart", views.get_cart, name="get_cart"),
    path("update_quantity/", views.update_quantity, name="update_quantity"),
    path("delete_cartitem/", views.delete_cartitem, name="delete_cartitem"),
    path("get_username", views.get_username, name="get_username"),
    path("user_info/", views.user_info, name="user_info"),
    path('verify_cart/', views.verify_cart, name='verify_cart'),
    path('associate_cart_to_user/', views.associate_cart_to_user, name='associate_cart_to_user'),
    path("initiate_paypal_payment/", views.initiate_paypal_payment, name="initiate_paypal_payment"),
    path("paypal_payment_callback/", views.paypal_payment_callback, name="paypal_payment_callback"),
    path("register/", views.register_user, name="register_user"),
    path("update_profile/", views.update_profile, name="update_profile"),
    path("change_password/", views.change_password, name="change_password"),
    path("initiate_epayco_payment/", views.initiate_epayco_payment, name="initiate_epayco_payment"),
    path("epayco_callback/", views.epayco_callback, name="epayco_callback"),
    path("verify_epayco_payment/", views.verify_epayco_payment, name="verify_epayco_payment"),
     path("product_detail_by_id/<int:product_id>/", views.product_detail_by_id, name="product_detail_by_id"),
    
    # Rutas del chatbot
    path("chatbot/message/", chatbot_views.chatbot_message, name="chatbot_message"),
    path("chatbot/history/", chatbot_views.chatbot_history, name="chatbot_history"),
    path("chatbot/feedback/<int:conversation_id>/", chatbot_views.chatbot_feedback, name="chatbot_feedback"),
    path("chatbot/product_query/", chatbot_views.product_query, name="product_query"),
]