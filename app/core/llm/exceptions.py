class LLMClientError(Exception):
    pass

class ConfigurationError(LLMClientError):
    pass

class ConnectionError(LLMClientError):
    pass