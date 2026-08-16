from pwdlib import PasswordHash


password_hash_service = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash_service.hash(password)


def verify_password(
    plain_password: str,
    stored_password_hash: str,
) -> bool:
    return password_hash_service.verify(
        plain_password,
        stored_password_hash,
    )