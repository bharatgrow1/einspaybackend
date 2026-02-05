ROLE_ORDER = {
    "superadmin": 0,
    "admin": 1,
    "master": 2,
    "dealer": 3,
    "retailer": 4,
}

ROLE_CHAIN = {
    "admin": [],
    "master": ["admin"],
    "dealer": ["admin", "master"],
    "retailer": ["admin", "master", "dealer"],
}
