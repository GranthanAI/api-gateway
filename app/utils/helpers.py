import uuid

def generate_uuid() -> str:
    """Generates a random UUIDv4 string."""
    return str(uuid.uuid4())
