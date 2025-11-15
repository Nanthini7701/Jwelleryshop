from django.shortcuts import render, get_object_or_404, redirect
from .models import Product, Category, CartItem, WishlistItem, Order
from .forms import AddToCartForm, CheckoutForm
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib.auth import logout
from django.db.models import Q
from django.conf import settings
import razorpay
from django.db import IntegrityError, transaction
from .forms import SignUpForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, authenticate
from decimal import Decimal
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
import hmac
import hashlib
from django.contrib import messages
import json
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

def about(request):
    return render(request, 'shop/about.html')
def home(request):
    return render(request, 'shop/base.html')

@require_http_methods(["POST"])
def subscribe(request):
    email = request.POST.get("email")
    if email:
        # TODO: save email to a model or send to mailing service
        # For now we'll just show a success message
        messages.success(request, "Thanks — you've been subscribed.")
    else:
        messages.error(request, "Please provide a valid email address.")
    # redirect back to the page where the form was submitted
    # if you prefer to render a template, change to render(...)
    return redirect(request.META.get("HTTP_REFERER", "/"))
@require_http_methods(["GET", "POST"])
def terms(request):
    """
    Simple terms & conditions page used by templates.
    """
    return render(request, 'shop/terms.html')
def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            try:
                # atomic to avoid race conditions
                with transaction.atomic():
                    user = form.save()
                # optionally auto-login
                username = form.cleaned_data.get("username")
                raw_password = form.cleaned_data.get("password1")
                user = authenticate(request, username=username, password=raw_password)
                if user:
                    login(request, user)
                messages.success(request, "Account created successfully.")
                return redirect('shop:product_list')  # change to desired redirect
            except IntegrityError:
                # in case of a race where another request just created same username
                form.add_error('username', "This username was just taken. Please pick another.")
        # if form invalid, fall through to re-render with errors
    else:
        form = SignUpForm()
    return render(request, 'shop/signup.html', {'form': form})
def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()  # saves and hashes password
            # optional: set user first/last name or email if you extended form
            # log the user in
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            if user:
                login(request, user)
            messages.success(request, "Account created and logged in.")
            # redirect to shop home or product list
            return redirect(reverse('shop:product_list'))
        else:
            # form invalid — show errors in modal or page
            messages.error(request, "Please fix the errors below.")
    else:
        form = UserCreationForm()

    # If you want to render a page (not modal), create signup.html
    return render(request, 'shop/signup.html', {'form': form})
def contact(request):
    if request.method == "POST":
        # very small example: you can expand to save messages or send email
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        # optionally add a success message via messages framework or pass context
        return render(request, 'shop/contact.html', {'success': True})
    return render(request, 'shop/contact.html')
def product_list(request):
    qs = Product.objects.filter(is_active=True)
    category = request.GET.get('category')
    q = request.GET.get('q')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    if category:
        qs = qs.filter(category__id=category)
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
    if min_price:
        try:
            qs = qs.filter(price__gte=Decimal(min_price))
        except:
            pass
    if max_price:
        try:
            qs = qs.filter(price__lte=Decimal(max_price))
        except:
            pass

    categories = Category.objects.all()
    context = {'products': qs, 'categories': categories}
    return render(request, 'shop/product_list.html', context)

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    form = AddToCartForm()
    return render(request, 'shop/product_detail.html', {'product': product, 'form': form})

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    quantity = int(request.POST.get('quantity', 1))
    item, created = CartItem.objects.get_or_create(user=request.user, product=product)
    if not created:
        item.quantity += quantity
    else:
        item.quantity = quantity
    item.save()
    return redirect('shop:view_cart')

@login_required
def view_cart(request):
    items = CartItem.objects.filter(user=request.user).select_related('product')
    total = sum([item.subtotal() for item in items])
    return render(request, 'shop/cart.html', {'items': items, 'total': total})

@login_required
def remove_from_cart(request, item_id):
    item = get_object_or_404(CartItem, pk=item_id, user=request.user)
    item.delete()
    return redirect('shop:view_cart')

@login_required
def view_wishlist(request):
    items = WishlistItem.objects.filter(user=request.user).select_related('product')
    return render(request, 'shop/wishlist.html', {'items': items})

@login_required
def toggle_wishlist(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    obj, created = WishlistItem.objects.get_or_create(user=request.user, product=product)
    if not created:
        obj.delete()
    return redirect('shop:view_wishlist')

@login_required
def checkout(request):
    items = CartItem.objects.filter(user=request.user).select_related('product')
    total = sum([item.subtotal() for item in items])
    order = None
    razor_order = None
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            amount_paisa = int(total * 100)
            razor_order = client.order.create(dict(amount=amount_paisa, currency='INR', payment_capture='1'))
            order = Order.objects.create(
                user=request.user,
                razorpay_order_id=razor_order['id'],
                amount=total,
            )
            context = {
                'order': order,
                'razorpay_order': razor_order,
                'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                'items': items,
                'total': total,
            }
            return render(request, 'shop/checkout.html', context)
    else:
        form = CheckoutForm()
    return render(request, 'shop/checkout.html', {'form': form, 'items': items, 'total': total})

@csrf_exempt
@require_POST
def payment_success(request):
    try:
        if request.content_type == 'application/json':
            payload = json.loads(request.body.decode('utf-8'))
        else:
            payload = request.POST
        payment_id = payload.get('razorpay_payment_id')
        razorpay_order_id = payload.get('razorpay_order_id')
        signature = payload.get('razorpay_signature')
        if not all([payment_id, razorpay_order_id, signature]):
            return HttpResponseBadRequest('Missing parameters')

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        params_dict = {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        }
        try:
            client.utility.verify_payment_signature(params_dict)
        except razorpay.errors.SignatureVerificationError:
            return HttpResponseForbidden('Signature verification failed')

        try:
            order = Order.objects.get(razorpay_order_id=razorpay_order_id)
            order.razorpay_payment_id = payment_id
            order.paid = True
            order.save()
            CartItem.objects.filter(user=order.user).delete()
            return JsonResponse({'status': 'ok', 'message': 'Payment verified and order completed', 'order_id': order.pk})
        except Order.DoesNotExist:
            return HttpResponseBadRequest('Order not found')

    except Exception as e:
        return HttpResponseBadRequest(str(e))

@csrf_exempt
@require_POST
def razorpay_webhook(request):
    webhook_secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', None)
    if not webhook_secret:
        return HttpResponseForbidden('Webhook secret not configured')

    body = request.body
    received_sig = request.META.get('HTTP_X_RAZORPAY_SIGNATURE')
    if received_sig is None:
        return HttpResponseForbidden('Missing signature header')

    expected_sig = hmac.new(webhook_secret.encode('utf-8'), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_sig, received_sig):
        return HttpResponseForbidden('Invalid webhook signature')

    try:
        event = json.loads(body.decode('utf-8'))
        event_type = event.get('event')
        payload = event.get('payload', {})

        if event_type == 'payment.captured':
            payment_entity = payload.get('payment', {}).get('entity', {})
            razorpay_payment_id = payment_entity.get('id')
            razorpay_order_id = payment_entity.get('order_id')
            try:
                order = Order.objects.get(razorpay_order_id=razorpay_order_id)
                order.razorpay_payment_id = razorpay_payment_id
                order.paid = True
                order.save()
            except Order.DoesNotExist:
                pass

        return HttpResponse(status=200)
    except Exception as e:
        return HttpResponseBadRequest(str(e))
def logout_and_show_login(request):
    """
    Logs out the user and redirects to home with a flag so the template can
    display the login form/modal: ?show_login=1
    """
    logout(request)
    # Redirect to home (product_list) with query param to show login UI
    return redirect(reverse('shop:product_list') + '?show_login=1')