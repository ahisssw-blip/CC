"""
Channel management module.
Handles operations related to Telegram channels and groups.
"""
import logging
from datetime import datetime

from src.database import save_database

logger = logging.getLogger(__name__)

async def list_channels(client):
    """
    List all channels/groups user is subscribed to
    
    Args:
        client: Telegram client
        
    Returns:
        list: List of channel information
    """
    try:
        dialogs = await client.get_dialogs()
        channels = []
        
        # Collect channel info
        for i, dialog in enumerate(dialogs, 1):
            if dialog.is_channel or dialog.is_group:
                entity = dialog.entity
                
                # Store channel info
                channel_info = {
                    'id': entity.id,
                    'title': entity.title,
                    'username': getattr(entity, 'username', None),
                    'participants_count': getattr(entity, 'participants_count', 0),
                    'type': 'Channel' if dialog.is_channel else 'Group',
                    'index': i
                }
                channels.append(channel_info)
        
        # Sort channels by member count (descending)
        channels.sort(key=lambda x: x['participants_count'] or 0, reverse=True)
        
        # Update indices after sorting
        for i, channel in enumerate(channels, 1):
            channel['index'] = i
        
        return channels
    except Exception as e:
        logger.error(f"Error listing channels: {e}")
        return []

def display_channels(channels):
    """
    Display channels in a tabular format
    
    Args:
        channels: List of channel information
    """
    if not channels:
        print("\nNo channels/groups found!")
        return
        
    # Print header
    print("\nAvailable Channels and Groups:")
    print(f"{'#':>3} | {'Members':>7} | {'Type':^7} | {'Title':<30} | {'Username':<15}")
    print("-" * 70)
    
    # Print each channel on one line
    for channel in channels:
        # Format members count
        members = f"{channel['participants_count']:,}" if channel['participants_count'] else 'N/A'
        members = members[:7]  # Limit length
        
        # Format username
        username = f"@{channel['username']}" if channel['username'] else '-'
        username = username[:15]  # Limit length
        
        # Format title (with ellipsis if too long)
        title = channel['title']
        if len(title) > 30:
            title = title[:27] + "..."
        
        print(f"{channel['index']:3} | {members:>7} | {channel['type']:<7} | {title:<30} | {username:<15}")
    
    print("-" * 70)
    print(f"Total: {len(channels)} channels/groups")

async def select_active_channel(client, db, db_path):
    """
    Select active channel/group
    
    Args:
        client: Telegram client
        db: Database
        db_path: Path to database file
        
    Returns:
        bool: True if channel selected, False otherwise
    """
    channels = await list_channels(client)
    display_channels(channels)
    
    if not channels:
        print("\nNo channels/groups found!")
        return False
    
    while True:
        try:
            choice = input("\nEnter channel number to select (or 0 to cancel): ")
            if choice == '0':
                return False
            
            index = int(choice)
            selected = next((c for c in channels if c['index'] == index), None)
            
            if selected:
                # Update active channel in database
                db['active_channel'] = selected
                save_database(db_path, db)
                print(f"\nSelected channel: {selected['title']}")
                return True
            else:
                print("\nInvalid channel number!")
        except ValueError:
            print("\nPlease enter a valid number!")

def get_active_channel(db):
    """
    Get currently active channel from database
    
    Args:
        db: Database
        
    Returns:
        dict: Active channel information
    """
    return db.get('active_channel')

async def show_active_channel(client, db):
    """
    Display information about active channel
    
    Args:
        client: Telegram client
        db: Database
    """
    active = get_active_channel(db)
    if active:
        print("\nActive Channel/Group:")
        print("--------------------")
        print(f"Title: {active['title']}")
        print(f"Type: {active['type']}")
        if active['username']:
            print(f"Username: @{active['username']}")
        print(f"ID: {active['id']}")
        print(f"Members: {active['participants_count']}")
        
        # Get message count information
        try:
            channel_id = str(active['id'])
            
            # Check if we have messages saved in DB
            saved_count = 0
            if 'messages' in db and channel_id in db.get('messages', {}):
                saved_count = len(db['messages'][channel_id])
            
            print(f"Saved Messages: {saved_count}")
            
            # Get total message count from the server
            print("Fetching total message count from server...")
            # Get first message (oldest)
            first_message = None
            last_message = None
            async for msg in client.iter_messages(active['id'], limit=1, reverse=True):
                first_message = msg
            
            # Get last message (newest) 
            async for msg in client.iter_messages(active['id'], limit=1):
                last_message = msg
                
            if first_message and last_message:
                total = last_message.id - first_message.id + 1
                print(f"Total Messages (estimate): {total}")
                print(f"First Message ID: {first_message.id}")
                print(f"Last Message ID: {last_message.id}")
                
                # Get video counts
                saved_videos_count = 0
                if 'videos' in db and channel_id in db.get('videos', {}):
                    saved_videos_count = len(db['videos'][channel_id])
                
                print(f"Saved Videos: {saved_videos_count}")
                
                # Check for media in saved messages
                media_count = 0
                if 'messages' in db and channel_id in db.get('messages', {}):
                    media_count = sum(1 for msg in db['messages'][channel_id].values() 
                                    if msg.get('has_media'))
                
                print(f"Messages with Media: {media_count}")
            else:
                print("Unable to determine total message count.")
            
        except Exception as e:
            logger.error(f"Error getting message count: {e}")
            print("Unable to determine message count.")
    else:
        print("\nNo active channel selected!") 