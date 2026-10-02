
class StripeCheckout:
    def __init__(self, api_key=None, webhook_url=None, **kw): pass
    async def create_checkout_session(self, *a, **kw):
        return type("o",(),{"url":"https://example.com/mock","session_id":"mock_123","id":"mock_123"})()
    async def get_checkout_status(self, *a, **kw):
        return type("o",(),{"status":"complete","payment_status":"paid"})()

class CheckoutSessionResponse: pass
class CheckoutStatusResponse: pass

def __getattr__(name):
    return StripeCheckout
