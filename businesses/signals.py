from django.db.models.signals import post_save
from django.dispatch import receiver

from businesses.models import Business
from subscriptions.trial_subscription import create_trial_subscription_for_new_business


@receiver(post_save, sender=Business)
def grant_trial_on_new_business(sender, instance, created, **kwargs):
    if created:
        create_trial_subscription_for_new_business(instance)
