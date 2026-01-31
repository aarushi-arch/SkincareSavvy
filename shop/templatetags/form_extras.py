from django import template

register = template.Library()


@register.filter(name="add_class")
def add_class(bound_field, css_class):
    """Minimal `add_class` filter used in templates.

    - Accepts a BoundField (e.g. `form.email`) and returns the field
      rendered with the extra CSS class applied.
    - Silently returns the original field if rendering fails so templates
      don't raise TemplateSyntaxError during tests.
    """
    try:
        return bound_field.as_widget(attrs={"class": css_class})
    except Exception:
        # Best-effort: fall back to the unmodified field (prevents template errors)
        return bound_field
