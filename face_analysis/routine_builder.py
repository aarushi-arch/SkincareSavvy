from recommendations.models import Product

def build_routine(clean_data):
    """
    Builds morning & night routine from clean skin data
    """

    skin_type = clean_data["skin_type"]
    skin_concerns = clean_data["skin_concerns"]

    routine = {
        "morning": {},
        "night": {}
    }

    # MORNING
    routine["morning"]["cleanser"] = Product.objects.filter(
        category="cleanser",
        skin_types__icontains=skin_type
    ).first()

    routine["morning"]["moisturizer"] = Product.objects.filter(
        category="moisturizer",
        skin_types__icontains=skin_type
    ).first()

    routine["morning"]["sunscreen"] = Product.objects.filter(
        category="sunscreen"
    ).first()

    # NIGHT
    routine["night"]["cleanser"] = routine["morning"]["cleanser"]

    routine["night"]["treatment"] = Product.objects.filter(
        category="treatment",
        skin_concerns__overlap=skin_concerns
    ).first()

    routine["night"]["moisturizer"] = routine["morning"]["moisturizer"]

    return routine

