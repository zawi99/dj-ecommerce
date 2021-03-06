from django.db import models
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.urls import reverse

from math import fsum

from addresses.models import Address
from billing.models import BillingProfile
from ecommerce.utils import unique_order_id_generator
from carts.models import Cart


class OrderManagerQuerySet(models.QuerySet):
    def by_request(self, request):
        billing_profile, created = BillingProfile.objects.new_or_get(request)
        return self.filter(billing_profile=billing_profile)

    def not_created(self):
        return self.exclude(status='CREATED')


class OrderManager(models.Manager):
    def get_queryset(self):
        return OrderManagerQuerySet(self.model, using=self._db)

    def by_request(self, request):
        return self.get_queryset().by_request(request)

    def new_or_get(self, billing_profile, cart_obj):
        created = False
        qs = self.get_queryset().filter(billing_profile=billing_profile,
                                        cart=cart_obj,
                                        active=True,
                                        status='CREATED'
                                        )
        if qs.count() == 1:
            obj = qs.first()
        else:
            obj = self.model.objects.create(billing_profile=billing_profile, cart=cart_obj)
            created = True
        return obj, created


class Order(models.Model):
    ORDER_STATUS_CHOICES = (
        ('CREATED', 'Created'),
        ('SHIPPED', 'Shipped'),
        ('CANCELLED', 'Cancelled'),
        ('PAID', 'Paid')
    )

    order_id = models.CharField(max_length=120, blank=True)
    cart = models.ForeignKey(Cart)
    billing_profile = models.ForeignKey(BillingProfile, null=True, blank=True, related_name='orders')
    shipping_address = models.ForeignKey(Address, related_name='shipping_address', null=True, blank=True)
    billing_address = models.ForeignKey(Address, related_name='billing_address', null=True, blank=True)
    status = models.CharField(max_length=12, choices=ORDER_STATUS_CHOICES, default='CREATED')
    shipping_total = models.DecimalField(default=9.99, max_digits=10, decimal_places=2)
    total = models.DecimalField(default=0.00, max_digits=10, decimal_places=2)
    active = models.BooleanField(default=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    objects = OrderManager()

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return self.order_id

    def get_absolute_url(self):
        return reverse('orders:order-detail', kwargs={'order_id': self.order_id})

    def get_status(self):
        if self.status == 'CANCELLED':
            return 'Cancelled'
        elif self.status == 'SHIPPED':
            return 'Shipped'
        else:
            return 'Shipping soon'

    def update_total(self):
        cart_total = self.cart.total
        shipping_total = self.shipping_total
        new_total = fsum([cart_total, shipping_total])
        self.total = new_total
        self.save()
        return new_total

    def check_order_done(self):
        billing_profile = self.billing_profile
        shipping_address = self.shipping_address
        billing_address = self.billing_address
        total = self.total
        if billing_profile and shipping_address and billing_address and total > 0:
            return True
        return False

    def mark_paid(self):
        if self.check_order_done():
            self.status = 'PAID'
            self.save()
        return self.status


@receiver(pre_save, sender=Order)
def pre_save_order_id_receiver(sender, instance, *args, **kwargs):
    if not instance.order_id:
        instance.order_id = unique_order_id_generator(instance)
    qs = Order.objects.exclude(billing_profile=instance.billing_profile).filter(active=True)
    if qs.exists():
        qs.update(active=False)


@receiver(post_save, sender=Cart)
def post_save_cart_total(sender, instance, created, *args, **kwargs):
    if not created:
        cart_obj = instance
        cart_id = cart_obj.id
        qs = Order.objects.filter(cart__id=cart_id)
        if qs.count() == 1:
            order_obj = qs.first()
            order_obj.update_total()


@receiver(post_save, sender=Order)
def post_save_order(sender, instance, created, *args, **kwargs):
    if created:
        instance.update_total()
