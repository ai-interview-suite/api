from uuid import UUID, uuid4


class User:
    def __init__(
        self,
        email: str,
        password_hash: str,
    ):
        self.id = uuid4()
        self.email = email
        self.password_hash = password_hash


_users: dict[UUID, User] = {}


def create_user(
    email: str,
    password_hash: str,
) -> User:

    user = User(
        email=email,
        password_hash=password_hash,
    )

    _users[user.id] = user

    return user


def get_user_by_email(
    email: str,
) -> User | None:

    for user in _users.values():
        if user.email == email:
            return user

    return None


def get_user_by_id(
    user_id: UUID,
) -> User | None:

    return _users.get(user_id)