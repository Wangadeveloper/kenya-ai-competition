import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-fallback-sacco-key')
    
    # SQL Database Configuration (Switched fallback to SQLite)
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///agrifinance.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Neo4j Graph Database Configuration
    NEO4J_URI = os.getenv('NEO4J_URI')
    NEO4J_USER = os.getenv('NEO4J_USERNAME')     
    NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')
    NEO4J_DATABASE = os.getenv('NEO4J_DATABASE', 'neo4j')
    
    # External APIs
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    AFRICASTALKING_USERNAME = os.getenv('AFRICASTALKING_USERNAME', 'sandbox')
    AFRICASTALKING_API_KEY = os.getenv('AFRICASTALKING_API_KEY')
    WHATSAPP_TOKEN = os.getenv('WHATSAPP_TOKEN')
    WHATSAPP_PHONE_NUMBER_ID = os.getenv('WHATSAPP_PHONE_NUMBER_ID')