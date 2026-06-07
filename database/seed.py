from sqlalchemy.orm import Session
from sqlalchemy import select, func
from models.user import User

def seed_users(db: Session):
    """Seed the database with initial users if the users table is empty."""
    count = db.scalar(select(func.count()).select_from(User))
    if count == 0:
        print("Seeding database with initial users...")
        users_to_add = []
        
        # 2 warehouse-managers
        for i in range(1, 3):
            users_to_add.append(User(
                username=f"manager_{i}",
                hashed_password=f"hash_manager_{i}",
                role="warehouse-manager"
            ))
            
        # 6 warehouse-operators
        for i in range(1, 7):
            users_to_add.append(User(
                username=f"operator_{i}",
                hashed_password=f"hash_operator_{i}",
                role="warehouse-operator"
            ))
            
        # 2 quality-assurance-managers
        for i in range(1, 3):
            users_to_add.append(User(
                username=f"qa_{i}",
                hashed_password=f"hash_qa_{i}",
                role="quality-assurance-manager"
            ))
            
        db.add_all(users_to_add)
        db.commit()
        print("Successfully seeded 10 users.")
    else:
        print(f"Database already contains {count} users. Skipping seed.")
