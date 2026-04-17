from django.db.models.signals import post_save
from django.dispatch import receiver

from businesses.models import Business, BusinessWebsitePayload
from subscriptions.trial_subscription import create_trial_subscription_for_new_business


@receiver(post_save, sender=Business)
def grant_trial_on_new_business(sender, instance, created, **kwargs):
    if created:
        BusinessWebsitePayload.objects.get_or_create(
            business=instance,
            defaults={"website_theme": {}, "website_content": {}},
        )
        create_trial_subscription_for_new_business(instance)
