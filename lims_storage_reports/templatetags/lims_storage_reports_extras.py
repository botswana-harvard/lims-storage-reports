from django import template

register = template.Library()

@register.filter
def get_item_total(dictionary, key):
    # Concatenate the key with '_total' and get the value from the dictionary
    total_key = f"{key}_total"
    return dictionary.get(total_key, 0)

@register.filter
def get_item_distinct(dictionary, key):
    # Concatenate the key with '_total' and get the value from the dictionary
    distinct_key = f"{key}_distinct"
    return dictionary.get(distinct_key, 0)