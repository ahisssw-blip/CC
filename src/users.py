"""
Users management module.
Handles operations related to Telegram channel users.
"""
import logging
from datetime import datetime

from src.channels import get_active_channel
from src.database import save_database

logger = logging.getLogger(__name__)

async def save_channel_users(client, db, db_path):
    """
    Save all users from active channel to database
    
    Args:
        client: Telegram client
        db: Database
        db_path: Path to database file
        
    Returns:
        bool: True if successful, False otherwise
    """
    active = get_active_channel(db)
    if not active:
        print("\nNo active channel selected!")
        return False
        
    try:
        print(f"\nFetching users from {active['title']}...")
        
        # Initialize channel users dict if doesn't exist
        channel_id = str(active['id'])
        if 'users' not in db:
            db['users'] = {}
        if channel_id not in db['users']:
            db['users'][channel_id] = {}
        
        # Get all participants
        participants = await client.get_participants(active['id'])
        
        # Counter for progress
        total = len(participants)
        saved = 0
        updated = 0
        
        print(f"\nProcessing {total} users...")
        
        for user in participants:
            user_dict = {
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'phone': getattr(user, 'phone', None),
                'bot': user.bot,
                'scam': user.scam,
                'fake': user.fake,
                'premium': user.premium,
                'verified': user.verified,
                'restricted': user.restricted,
                'last_seen': str(datetime.now())
            }
            
            user_id = str(user.id)
            if user_id in db['users'][channel_id]:
                # Update existing user
                user_dict['first_seen'] = db['users'][channel_id][user_id]['first_seen']
                db['users'][channel_id][user_id].update(user_dict)
                updated += 1
            else:
                # Add new user
                user_dict['first_seen'] = str(datetime.now())
                db['users'][channel_id][user_id] = user_dict
                saved += 1
            
            # Show progress every 10 users
            if (saved + updated) % 10 == 0:
                print(f"Progress: {saved + updated}/{total}")
        
        save_database(db_path, db)
        print(f"\nOperation completed!")
        print(f"New users saved: {saved}")
        print(f"Users updated: {updated}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving channel users: {e}")
        print(f"\nError saving users: {str(e)}")
        return False

async def show_channel_users_stats(db):
    """
    Show statistics about saved users in active channel
    
    Args:
        db: Database
    """
    active = get_active_channel(db)
    if not active:
        print("\nNo active channel selected!")
        return
        
    channel_id = str(active['id'])
    if channel_id not in db.get('users', {}):
        print("\nNo saved users for this channel!")
        return
        
    users = db['users'][channel_id]
    total = len(users)
    bots = sum(1 for u in users.values() if u['bot'])
    premium = sum(1 for u in users.values() if u['premium'])
    verified = sum(1 for u in users.values() if u['verified'])
    
    print(f"\nChannel Users Statistics:")
    print(f"------------------------")
    print(f"Total users saved: {total}")
    print(f"Bots: {bots}")
    print(f"Premium users: {premium}")
    print(f"Verified users: {verified}")
    print(f"\nLast update: {max(u['last_seen'] for u in users.values())}")

async def list_saved_users(db):
    """
    List users saved from active channel
    
    Args:
        db: Database
    """
    active = get_active_channel(db)
    if not active:
        print("\nNo active channel selected!")
        return
        
    channel_id = str(active['id'])
    if channel_id not in db.get('users', {}):
        print("\nNo saved users for this channel!")
        return
        
    users = db['users'][channel_id]
    if not users:
        print("\nNo users found!")
        return
        
    print("\nSaved Users:")
    print("-" * 80)
    print(f"{'ID':<12} | {'Username':<15} | {'Name':<20} | {'Type':<8} | {'Status'}")
    print("-" * 80)
    
    for user_id, user in sorted(users.items(), key=lambda x: x[1].get('username') or ''):
        username = f"@{user['username']}" if user['username'] else '-'
        name = f"{user['first_name'] or ''} {user['last_name'] or ''}".strip() or '-'
        user_type = 'Bot' if user['bot'] else 'User'
        
        status = []
        if user['premium']: status.append('Premium')
        if user['verified']: status.append('Verified')
        if user['scam']: status.append('Scam')
        if user['fake']: status.append('Fake')
        if user['restricted']: status.append('Restricted')
        
        status_str = ', '.join(status) if status else '-'
        
        print(f"{user_id:<12} | {username:<15} | {name[:20]:<20} | {user_type:<8} | {status_str}")
    
    print("-" * 80)
    print(f"Total Users: {len(users)}") 