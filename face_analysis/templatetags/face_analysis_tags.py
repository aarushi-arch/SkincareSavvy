from django import template

register = template.Library()

@register.filter
def dict_get(prediction_list, class_name):
    """
    Finds a prediction by class name in a list of predictions.
    Usage: {{ analysis_result.skin_concerns.predictions|dict_get:'wrinkles' }}
    """
    if not isinstance(prediction_list, list):
        return None
    for pred in prediction_list:
        if pred.get('class', '').lower() == class_name.lower():
            return pred
    return None

@register.filter
def default_confidence(prediction, default_val=85):
    """
    Returns formatted confidence score or a default value if prediction is missing.
    """
    if not prediction or not isinstance(prediction, dict):
        return default_val
    conf = prediction.get('confidence', 0)
    return int(conf * 100)

@register.filter
def multiply(value, arg):
    """Multiplies the value by the argument."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ""

@register.filter
def split(value, arg):
    """Splits a string by the given argument."""
    if not isinstance(value, str):
        return value
    return value.split(arg)

@register.filter
def strip(value):
    """Strips whitespace from a string."""
    if not isinstance(value, str):
        return value
    return value.strip()
