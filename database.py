from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "survey_generator")

class Database:
    client: AsyncIOMotorClient = None
    
db = Database()

async def get_database():
    if db.client is None:
        raise Exception("Database not connected. Please check MongoDB connection settings.")
    return db.client[DATABASE_NAME]

async def connect_to_mongo():
    """Connect to MongoDB and create indexes"""
    try:
        # Create client with shorter timeout for faster failure detection
        db.client = AsyncIOMotorClient(
            MONGODB_URL,
            serverSelectionTimeoutMS=5000,  # 5 second timeout
            connectTimeoutMS=5000
        )
        database = db.client[DATABASE_NAME]
        
        # Test the connection
        await db.client.admin.command('ping')
        print(f"✓ Connected to MongoDB successfully")
        
        # Create indexes for better performance
        surveys_collection = database["surveys"]
        await surveys_collection.create_index("surveyId", unique=True)
        await surveys_collection.create_index("createdAt")
        await surveys_collection.create_index("versions.version")
        
        print(f"✓ Database indexes created successfully")
    except Exception as e:
        print(f"✗ Failed to connect to MongoDB: {e}")
        print(f"⚠ Server will start but database operations will fail")
        print(f"⚠ Please check:")
        print(f"  1. MongoDB Atlas IP whitelist (add 0.0.0.0/0 or your IP)")
        print(f"  2. Network/firewall settings")
        print(f"  3. MongoDB Atlas cluster is running")
        # Don't raise - allow server to start
        db.client = None

async def close_mongo_connection():
    """Close MongoDB connection"""
    if db.client:
        db.client.close()
        print("Closed MongoDB connection")
