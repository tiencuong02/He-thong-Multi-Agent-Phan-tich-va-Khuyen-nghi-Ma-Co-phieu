import asyncio
import os
from dotenv import load_dotenv
from app.db.mongodb import connect_to_mongo, db_instance
from app.repositories.user_repository import UserRepository

load_dotenv()

async def check_user():
    await connect_to_mongo()
    db = db_instance.db

    repo = UserRepository(db)

    print("Checking user 'admin' in database...\n")

    try:
        # Find user by username
        user = await repo.get_by_username("admin")

        if user:
            print(f"[+] User found!")
            print(f"    ID: {user.id}")
            print(f"    Username: {user.username}")
            print(f"    Role: {user.role}")
            print(f"    Full data: {user}")
        else:
            print(f"[-] User 'admin' not found in database")

            # List all users
            print("\nAll users in database:")
            all_users = await db["users"].find().to_list(None)
            for u in all_users:
                print(f"    - {u.get('username')}: role={u.get('role')}, id={u.get('_id')}")

    except Exception as e:
        print(f"[-] Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_user())
