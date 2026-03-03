from django import template

register = template.Library()


@register.filter
def format_duration(seconds):
    """Convert a float of total seconds into a human-readable string like '1h 23m 45s'."""
    try:
        total = int(float(seconds))
    except (TypeError, ValueError):
        return "0s"

    if total <= 0:
        return "0s"

    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)

    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")

    return " ".join(parts)
