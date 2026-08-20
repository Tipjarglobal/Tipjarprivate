class StripeCheckout:
    def __init__(self, *a, **k): pass
    async def create_checkout_session(self, *a, **k): return {"url": "/checkout-disabled"}
    async def get_checkout_status(self, *a, **k): return {"status": "disabled"}

class CheckoutSessionResponse:
    pass
class CheckoutStatusResponse:
    pass
class CheckoutSessionRequest:
    pass
