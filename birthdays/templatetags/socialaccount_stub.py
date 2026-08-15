"""No-op socialaccount tags for optional allauth templates.

The project does not enable allauth.socialaccount. django-compressor still
discovers allauth's optional templates during offline compression, so those
templates need a library that can parse and render them as empty provider
sections. If social login is enabled later, remove this mapping and install
allauth.socialaccount normally.
"""

from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def get_providers(context):
    return []


@register.simple_tag(takes_context=True)
def provider_login_url(context, provider, **params):
    return "#"


@register.simple_tag(takes_context=True)
def providers_media_js(context):
    return ""


@register.simple_tag
def get_social_accounts(user):
    return {}
