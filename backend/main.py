"""
University Chatbot Flask Application Entry Point
"""

from http.client import HTTPException
from app import create_app
import logging


logging.basicConfig(
    level=logging.INFO,  # Changed to INFO
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('backend.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    # Create Flask app
    app = create_app()
    
    # Run the application
    app.run(
        host='0.0.0.0',
        port=5000,
        debug= True
    )
    
 
# Health check endpoint
@app.get("/")
async def root():
    """Return a basic health check message."""
    logger.info("Health check endpoint accessed")
    try:
      
        return {"message": "UNI Tool API is running"}
    except Exception as e:
        logger.error(f"MongoDB health check failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Database connection error")