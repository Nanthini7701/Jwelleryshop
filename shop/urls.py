
from django.urls import path, include
from . import views
from django.contrib.auth import views as auth_views

app_name = 'shop'

urlpatterns = [
    path('', views.product_list, name='product_list'),
        path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
     path('subscribe/', views.subscribe, name='subscribe'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('wishlist/', views.view_wishlist, name='view_wishlist'),
 
    path('wishlist/toggle/<int:product_id>/', views.toggle_wishlist, name='toggle_wishlist'),
    path('checkout/', views.checkout, name='checkout'),
    path('payment_success/', views.payment_success, name='payment_success'),
    path('razorpay_webhook/', views.razorpay_webhook, name='razorpay_webhook'),
      path('logout-then-login/', views.logout_and_show_login, name='logout_then_login'),
       path('signup/', views.signup, name='signup'),
         path('terms/', views.terms, name='terms'),
           path('accounts/login/',
         auth_views.LoginView.as_view(template_name='shop/login.html'),
         name='login'),
    path('accounts/', include('django.contrib.auth.urls')),
]
