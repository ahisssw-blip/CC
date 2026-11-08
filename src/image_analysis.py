"""
Image analysis module using OpenRouter API.
Provides functionality to analyze images using AI models.
"""
import os
import logging
import base64
import requests
from typing import Optional, Dict, Any

from src.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, OPENROUTER_MODEL, OPENROUTER_TIMEOUT

logger = logging.getLogger(__name__)

def encode_image_to_base64(image_path: str) -> str:
    """
    Encode an image file to base64 string.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Base64 encoded string of the image
    """
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def get_image_mime_type(image_path: str) -> str:
    """
    Get the MIME type of an image based on its file extension.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        MIME type string (e.g., 'image/jpeg', 'image/png')
    """
    extension = os.path.splitext(image_path)[1].lower()
    mime_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.bmp': 'image/bmp'
    }
    return mime_types.get(extension, 'image/jpeg')

def analyze_image_with_openrouter(image_path: str, prompt: str = None) -> Dict[str, Any]:
    """
    Analyze an image using OpenRouter API with GPT-4 Vision.
    
    Args:
        image_path: Path to the image file
        prompt: Optional custom prompt for analysis
        
    Returns:
        Dict containing analysis result or error information
    """
    # Reload environment variables to catch any updates
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv('OPENROUTER_API_KEY')
    
    if not api_key:
        return {
            'success': False,
            'error': 'OpenRouter API key not configured. Please set OPENROUTER_API_KEY environment variable.'
        }
    
    if not os.path.exists(image_path):
        return {
            'success': False,
            'error': f'Image file not found: {image_path}'
        }
    
    try:
        # Encode image to base64
        base64_image = encode_image_to_base64(image_path)
        mime_type = get_image_mime_type(image_path)
        data_url = f"data:{mime_type};base64,{base64_image}"
        
        # Default prompt for image analysis
        if prompt is None:
            prompt = ("Describe what you see in this image in detail. "
                     "Include objects, people, text, colors, setting, and any other relevant details. "
                     "If there is text in the image, transcribe it. "
                     "Keep the description concise but comprehensive.")
        
        # Prepare the request
        url = f"{OPENROUTER_BASE_URL}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": data_url
                        }
                    }
                ]
            }
        ]
        
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": messages,
            "max_tokens": 1000
        }
        
        logger.info(f"Analyzing image: {image_path}")
        response = requests.post(url, headers=headers, json=payload, timeout=OPENROUTER_TIMEOUT)
        
        if response.status_code == 200:
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                analysis = result['choices'][0]['message']['content']
                logger.info(f"Image analysis completed successfully for: {image_path}")
                
                return {
                    'success': True,
                    'analysis': analysis,
                    'model': OPENROUTER_MODEL,
                    'image_path': image_path,
                    'usage': result.get('usage', {})
                }
            else:
                logger.error(f"No analysis content in response: {result}")
                return {
                    'success': False,
                    'error': 'No analysis content received from API'
                }
        else:
            logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
            return {
                'success': False,
                'error': f'API request failed with status {response.status_code}: {response.text}'
            }
            
    except requests.exceptions.Timeout:
        logger.error(f"Timeout while analyzing image: {image_path}")
        return {
            'success': False,
            'error': 'Request timed out while analyzing image'
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while analyzing image: {image_path} - {str(e)}")
        return {
            'success': False,
            'error': f'Network error: {str(e)}'
        }
    except Exception as e:
        logger.error(f"Unexpected error analyzing image: {image_path} - {str(e)}")
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }

def analyze_multiple_images(image_paths: list, prompt: str = None) -> Dict[str, Any]:
    """
    Analyze multiple images that belong to the same media group.
    
    Args:
        image_paths: List of image file paths
        prompt: Optional custom prompt for analysis
        
    Returns:
        Dict containing analysis result or error information
    """
    # Reload environment variables to catch any updates
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv('OPENROUTER_API_KEY')
    
    if not api_key:
        return {
            'success': False,
            'error': 'OpenRouter API key not configured. Please set OPENROUTER_API_KEY environment variable.'
        }
    
    # Filter out non-existent files
    existing_images = [path for path in image_paths if os.path.exists(path)]
    if not existing_images:
        return {
            'success': False,
            'error': 'No valid image files found'
        }
    
    try:
        # Default prompt for multiple images
        if prompt is None:
            prompt = ("Describe what you see in these images. "
                     "These images are part of the same message or media group. "
                     "Describe each image and explain how they relate to each other. "
                     "Include objects, people, text, colors, setting, and any other relevant details. "
                     "If there is text in any image, transcribe it. "
                     "Keep the description concise but comprehensive.")
        
        # Prepare the request
        url = f"{OPENROUTER_BASE_URL}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Build content array with text and all images
        content = [
            {
                "type": "text",
                "text": prompt
            }
        ]
        
        # Add each image to the content
        for image_path in existing_images:
            base64_image = encode_image_to_base64(image_path)
            mime_type = get_image_mime_type(image_path)
            data_url = f"data:{mime_type};base64,{base64_image}"
            
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": data_url
                }
            })
        
        messages = [
            {
                "role": "user",
                "content": content
            }
        ]
        
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": messages,
            "max_tokens": 1500  # Increased for multiple images
        }
        
        logger.info(f"Analyzing {len(existing_images)} images as media group")
        response = requests.post(url, headers=headers, json=payload, timeout=OPENROUTER_TIMEOUT)
        
        if response.status_code == 200:
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                analysis = result['choices'][0]['message']['content']
                logger.info(f"Media group analysis completed successfully for {len(existing_images)} images")
                
                return {
                    'success': True,
                    'analysis': analysis,
                    'model': OPENROUTER_MODEL,
                    'image_paths': existing_images,
                    'image_count': len(existing_images),
                    'usage': result.get('usage', {})
                }
            else:
                logger.error(f"No analysis content in response: {result}")
                return {
                    'success': False,
                    'error': 'No analysis content received from API'
                }
        else:
            logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
            return {
                'success': False,
                'error': f'API request failed with status {response.status_code}: {response.text}'
            }
            
    except requests.exceptions.Timeout:
        logger.error(f"Timeout while analyzing media group")
        return {
            'success': False,
            'error': 'Request timed out while analyzing images'
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error while analyzing media group: {str(e)}")
        return {
            'success': False,
            'error': f'Network error: {str(e)}'
        }
    except Exception as e:
        logger.error(f"Unexpected error analyzing media group: {str(e)}")
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }