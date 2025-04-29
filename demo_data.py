import asyncio
from database import Database

async def populate_demo_data():
    db = Database()
    
    # Демо-пользователи
    demo_users = [
        {
            "telegram_id": 123456789,
            "username": "alex_dev",
            "full_name": "Александр Петров",
            "skills": ["Python", "JavaScript", "React", "Node.js"],
            "interests": ["Web Development", "AI", "Open Source"],
            "contact_info": {
                "email": "alex@example.com",
                "telegram": "@alex_dev",
                "github": "github.com/alex_dev"
            }
        },
        {
            "telegram_id": 987654321,
            "username": "maria_designer",
            "full_name": "Мария Иванова",
            "skills": ["UI/UX", "Figma", "Adobe Photoshop", "Prototyping"],
            "interests": ["Design Systems", "Mobile Design", "Typography"],
            "contact_info": {
                "email": "maria@example.com",
                "telegram": "@maria_designer",
                "behance": "behance.net/maria_designer"
            }
        },
        {
            "telegram_id": 456789123,
            "username": "dmitry_pm",
            "full_name": "Дмитрий Сидоров",
            "skills": ["Project Management", "Agile", "Scrum", "Team Leadership"],
            "interests": ["Product Development", "Team Building", "StartUps"],
            "contact_info": {
                "email": "dmitry@example.com",
                "telegram": "@dmitry_pm",
                "linkedin": "linkedin.com/in/dmitry_pm"
            }
        },
        {
            "telegram_id": 789123456,
            "username": "anna_marketing",
            "full_name": "Анна Козлова",
            "skills": ["Digital Marketing", "SMM", "Content Strategy", "Analytics"],
            "interests": ["Growth Hacking", "Brand Development", "Social Media"],
            "contact_info": {
                "email": "anna@example.com",
                "telegram": "@anna_marketing",
                "instagram": "@anna_marketing_pro"
            }
        }
    ]
    
    # Добавляем пользователей в базу
    for user in demo_users:
        success = await db.add_member(
            telegram_id=user["telegram_id"],
            username=user["username"],
            full_name=user["full_name"],
            skills=user["skills"],
            interests=user["interests"],
            contact_info=user["contact_info"]
        )
        if success:
            print(f"Добавлен пользователь: {user['full_name']}")
        else:
            print(f"Ошибка при добавлении пользователя: {user['full_name']}")

if __name__ == "__main__":
    asyncio.run(populate_demo_data()) 