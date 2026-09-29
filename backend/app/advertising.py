"""Advertising field taxonomy used by the explainable local LSA model."""

ADVERTISING_FIELDS = {
    "Beauty & personal care": "skincare makeup cosmetics beauty haircare fragrance personal care grooming routines product reviews",
    "Food & beverage": "food cooking recipes restaurants nutrition coffee snacks beverages kitchen culinary dining",
    "Fashion & accessories": "fashion clothing outfits apparel style accessories footwear jewelry trends wardrobe",
    "Travel & hospitality": "travel destinations tourism hotels hospitality flights adventures local guides vacations",
    "Fitness & wellness": "fitness workouts exercise health wellness yoga supplements running training mental wellbeing",
    "Technology & gaming": "technology consumer electronics software apps gaming game streaming computers gadgets reviews",
    "Home & lifestyle": "home interiors decor furniture organization gardening household lifestyle renovation",
    "Education & finance": "education learning books career personal finance investing budgeting business productivity",
    "Parenting & family": "parenting family children baby childcare toys family activities household parenting advice",
    "Pets & animals": "pets dogs cats animal care pet food training veterinary products animal lifestyle",
    "Sustainability & outdoors": "sustainability environment eco friendly climate nature camping outdoors conservation ethical products",
}


def creator_document(creator, accounts) -> str:
    parts = [
        creator.display_name or "",
        creator.bio or "",
        creator.niche or "",
        creator.country or "",
        creator.city or "",
        " ".join(account.platform for account in accounts),
    ]
    return " ".join(part for part in parts if part).strip()
