class LlmChat:
    def __init__(self, api_key=None, session_id=None, system_message=None, **kwargs):
        self.api_key = api_key
        self.session_id = session_id
    async def send_message(self, *args, **kwargs):
        return "AI disabled - JarDex runs without Emergent"
    def with_model(self, *a, **k):
        return self

class UserMessage:
    def __init__(self, text="", **k):
        self.text = text

class ImageContent:
    def __init__(self, *a, **k):
        pass
