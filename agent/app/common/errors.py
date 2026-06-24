class AgentNotFoundError(KeyError):
    """Raised when a requested agent does not exist in the registry."""


class KnowledgeConfigError(ValueError):
    """Support loading exactly one knowledge base from knowledge.json by default"""