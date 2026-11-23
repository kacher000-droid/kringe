from database.models import User
from database.session import SessionLocal


async def get_or_create_user(
    tg_id: int,
    username: str | None,
    first_name: str,
    referrer_id: int | None = None,
) -> tuple[User, bool]:
    async with SessionLocal() as session:
        user = await session.get(User, tg_id)
        created = False

        if user is None:
            ref_id = None
            if referrer_id and referrer_id != tg_id:
                referrer = await session.get(User, referrer_id)
                if referrer is not None:
                    referrer.invited_count += 1
                    ref_id = referrer_id

            name = (first_name or username or f"Игрок {tg_id % 10000}")[:32]
            user = User(
                id=tg_id,
                username=username,
                first_name=first_name or "",
                display_name=name,
                referrer_id=ref_id,
            )
            session.add(user)
            created = True
        else:
            user.username = username
            user.first_name = first_name or ""

        await session.commit()
        return user, created
