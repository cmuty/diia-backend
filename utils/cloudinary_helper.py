"""
Cloudinary Helper for uploading and managing photos
"""
import os
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()

# Configure Cloudinary from environment variables
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME", "djoszn8zc"),
    api_key=os.getenv("CLOUDINARY_API_KEY", "472899494355635"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET", "gGgIhXupY9im376HqlyCwNhZe-c")
)


async def upload_photo_to_cloudinary(file_path: str, user_id: int) -> str:
    """
    Upload photo to Cloudinary and return the URL
    
    Args:
        file_path: Path to the local photo file
        user_id: User ID for naming the photo
        
    Returns:
        URL of the uploaded photo on Cloudinary
    """
    try:
        # Upload photo to Cloudinary
        result = cloudinary.uploader.upload(
            file_path,
            folder="diia_photos",
            public_id=f"user_{user_id}",
            overwrite=True,
            resource_type="image"
        )
        
        # Return the secure URL
        return result.get('secure_url', result.get('url'))
        
    except Exception as e:
        print(f"Error uploading photo to Cloudinary: {e}")
        raise


async def delete_photo_from_cloudinary(user_id: int):
    """
    Delete photo from Cloudinary
    
    Args:
        user_id: User ID to identify the photo
    """
    try:
        public_id = f"diia_photos/user_{user_id}"
        cloudinary.uploader.destroy(public_id)
    except Exception as e:
        print(f"Error deleting photo from Cloudinary: {e}")


def get_photo_url(user_id: int) -> str:
    """
    Get Cloudinary URL for user photo
    
    Args:
        user_id: User ID
        
    Returns:
        Cloudinary URL for the photo
    """
    # Generate the URL directly from Cloudinary
    url = cloudinary.CloudinaryImage(f"diia_photos/user_{user_id}").build_url()
    return url

