
class UserMessage:
    def __init__(self, text="", **kwargs): self.text=text
class ImageContent:
    def __init__(self, *a, **kw): pass
class LlmChat:
    def __init__(self, *a, **kw): pass
    def with_model(self, p,m): return self
    async def send_message(self, msg):
        return type("o",(),{"text":"Mock LLM"})()
