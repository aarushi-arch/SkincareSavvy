from django.shortcuts import render, redirect, get_object_or_404 
from django.contrib import messages
from django.views import View
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.decorators import login_required

from .forms import RegisterForm, LoginForm, UserUpdateForm, ProfileUpdateForm
from .models import Profile, ShelfItem
from recommendations.models import Product

from django.contrib.auth import logout


def logout_user(request):
    logout(request)
    return redirect("users-home") 

def home(request):
    return render(request, 'users/home.html')


class RegisterView(View):
    form_class = RegisterForm
    initial = {'key': 'value'}
    template_name = 'users/register.html'

    def get(self, request, *args, **kwargs):
        form = self.form_class(initial=self.initial)
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)

        if form.is_valid():
            form.save()

            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}')

            return redirect(to='/')

        return render(request, self.template_name, {'form': form})


# Class based view that extends from the built in login view to add a remember me functionality
class CustomLoginView(LoginView):
    form_class = LoginForm

    def form_valid(self, form):
        remember_me = form.cleaned_data.get('remember_me')

        if not remember_me:
            # set session expiry to 0 seconds. So it will automatically close the session after the browser is closed.
            self.request.session.set_expiry(0)

            # Set session as modified to force data updates/cookie to be saved.
            self.request.session.modified = True

        # else browser session will be as long as the session cookie time "SESSION_COOKIE_AGE" defined in settings.py
        return super(CustomLoginView, self).form_valid(form)


# Class based view for logout
class CustomLogoutView(LogoutView):
    template_name = 'users/logout.html'


# Profile view
@login_required
def profile(request):
    # Get or create profile if it doesn't exist
    profile, created = Profile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST,
                                   request.FILES,
                                   instance=profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, f'Your account has been updated!')
            return redirect('profile')

    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=profile)

    context = {
        'u_form': u_form,
        'p_form': p_form
    }

    return render(request, 'users/profile.html', context)


@login_required
def my_shelf(request):
    """View to display user's shelf items."""
    shelf_items = ShelfItem.objects.filter(user=request.user)
    context = {
        'shelf_items': shelf_items,
        'page_title': 'My Shelf'
    }
    return render(request, 'users/my_shelf.html', context)


@login_required
def add_to_shelf(request, product_id):
    """View to add a product to user's shelf."""
    product = get_object_or_404(Product, id=product_id)
    
    # Check if item already exists
    shelf_item, created = ShelfItem.objects.get_or_create(
        user=request.user, 
        product=product
    )
    
    if created:
        messages.success(request, f'{product.name} added to your shelf!')
    else:
        messages.info(request, f'{product.name} is already in your shelf.')
        
    # Redirect back to the previous page or my_shelf
    next_url = request.META.get('HTTP_REFERER')
    if next_url:
        return redirect(next_url)
    return redirect('my_shelf')


@login_required
def remove_from_shelf(request, product_id):
    """View to remove a product from user's shelf."""
    product = get_object_or_404(Product, id=product_id)
    
    deleted_count, _ = ShelfItem.objects.filter(user=request.user, product=product).delete()
    
    if deleted_count > 0:
        messages.success(request, f'{product.name} removed from your shelf.')
    else:
        messages.warning(request, f'{product.name} was not found in your shelf.')
        
    return redirect('my_shelf')
