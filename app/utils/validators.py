import uuid

def is_valid_uuid(uuid_to_test: str) -> bool:
    """Verifies that a string is a valid RFC 4122 UUID."""
    try:
        uuid.UUID(str(uuid_to_test))
        return True
    except ValueError:
        return False
