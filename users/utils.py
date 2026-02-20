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



class EkoAnalyzer:

    SUCCESS = [2, '2', 'SUCCESS']
    FAILED  = [1, '1', 'FAILED']

    @classmethod
    def analyze(cls, response):

        if not response:
            return "admin_review"

        status = (
            response.get("txstatus")
            or response.get("tx_status")
            or response.get("response_status")
            or response.get("status_code")
        )

        if status in cls.SUCCESS:
            return "success"

        if status in cls.FAILED:
            return "failed"

        return "admin_review"
