from django import template
from django.utils.html import format_html

register = template.Library()

# Category and account-type values -> icon names in _icons.html. Anything unknown gets 'dots'.
ICONS = {
    'dining': 'food', 'groceries': 'cart', 'transport': 'transport', 'phone': 'phone', 'bills': 'bills',
    'subscriptions': 'repeat', 'shopping': 'bag', 'fun': 'fun', 'health': 'health', 'fees': 'percent',
    'salary': 'briefcase', 'bonus': 'gift', 'freelance': 'laptop', 'commission': 'percent', 'business': 'store',
    'side_hustle': 'zap', 'allowance': 'wallet', 'gift': 'gift', 'refund': 'refund', 'cashback': 'coins',
    'interest': 'invest', 'dividend': 'budget', 'rental': 'home', 'transfer': 'swap',
    'bank': 'bank', 'wallet': 'phone', 'cash': 'cash', 'credit': 'card',
}


@register.simple_tag
def icon(name, label=''):
    """<svg> pointing at a symbol in _icons.html. Decorative unless a label is given."""
    if label:
        return format_html('<svg class="i" role="img" aria-label="{}"><use href="#i-{}"/></svg>', label, name)
    return format_html('<svg class="i" aria-hidden="true"><use href="#i-{}"/></svg>', name)


@register.filter
def icon_for(value):
    return ICONS.get(value, 'dots')
