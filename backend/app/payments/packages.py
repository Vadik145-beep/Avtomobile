PACKAGES: dict[str, dict] = {
    "10":  {"limits": 10,  "price_rub": 990},
    "50":  {"limits": 50,  "price_rub": 3990},
    "100": {"limits": 100, "price_rub": 6990},
}


def get_package_limits(package_id: str) -> int:
    """Return number of limits for the given package_id. Raises KeyError if unknown."""
    return PACKAGES[package_id]["limits"]
