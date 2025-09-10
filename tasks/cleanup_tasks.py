from datetime import datetime, timedelta
from models import db, CaptchaSession
import logging

logger = logging.getLogger(__name__)

class CleanupTasks:
    """Background tasks for cleaning up expired data"""
    
    def __init__(self):
        pass
    
    def cleanup_expired_captcha_sessions(self):
        """Remove expired captcha sessions from database"""
        try:
            # Find expired sessions
            expired_sessions = CaptchaSession.query.filter(
                CaptchaSession.expires_at < datetime.utcnow()
            ).all()
            
            count = len(expired_sessions)
            
            if count > 0:
                logger.info(f"Cleaning up {count} expired captcha sessions")
                
                # Delete expired sessions
                for session in expired_sessions:
                    db.session.delete(session)
                
                db.session.commit()
                logger.info(f"Successfully cleaned up {count} expired captcha sessions")
            else:
                logger.debug("No expired captcha sessions to clean up")
            
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired captcha sessions: {e}")
            db.session.rollback()
            return 0
    
    def cleanup_old_captcha_sessions(self, days_old=7):
        """Remove old captcha sessions (completed or not) after specified days"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            old_sessions = CaptchaSession.query.filter(
                CaptchaSession.created_at < cutoff_date
            ).all()
            
            count = len(old_sessions)
            
            if count > 0:
                logger.info(f"Cleaning up {count} old captcha sessions (older than {days_old} days)")
                
                for session in old_sessions:
                    db.session.delete(session)
                
                db.session.commit()
                logger.info(f"Successfully cleaned up {count} old captcha sessions")
            else:
                logger.debug(f"No old captcha sessions to clean up (older than {days_old} days)")
            
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up old captcha sessions: {e}")
            db.session.rollback()
            return 0
    
    def get_cleanup_stats(self):
        """Get statistics about data that can be cleaned up"""
        try:
            now = datetime.utcnow()
            
            # Count expired sessions
            expired_count = CaptchaSession.query.filter(
                CaptchaSession.expires_at < now
            ).count()
            
            # Count old sessions (7+ days)
            old_cutoff = now - timedelta(days=7)
            old_count = CaptchaSession.query.filter(
                CaptchaSession.created_at < old_cutoff
            ).count()
            
            # Count total sessions
            total_sessions = CaptchaSession.query.count()
            
            # Count active sessions
            active_sessions = CaptchaSession.query.filter(
                CaptchaSession.expires_at > now,
                CaptchaSession.completed == False
            ).count()
            
            return {
                'total_captcha_sessions': total_sessions,
                'active_captcha_sessions': active_sessions,
                'expired_captcha_sessions': expired_count,
                'old_captcha_sessions': old_count,
                'cleanup_recommended': expired_count > 0 or old_count > 0
            }
            
        except Exception as e:
            logger.error(f"Error getting cleanup stats: {e}")
            return {
                'error': str(e)
            }
    
    def run_all_cleanup_tasks(self):
        """Run all cleanup tasks"""
        results = {
            'expired_sessions_cleaned': 0,
            'old_sessions_cleaned': 0,
            'total_cleaned': 0,
            'errors': []
        }
        
        try:
            # Cleanup expired sessions
            expired_cleaned = self.cleanup_expired_captcha_sessions()
            results['expired_sessions_cleaned'] = expired_cleaned
            
            # Cleanup old sessions
            old_cleaned = self.cleanup_old_captcha_sessions()
            results['old_sessions_cleaned'] = old_cleaned
            
            results['total_cleaned'] = expired_cleaned + old_cleaned
            
            logger.info(f"Cleanup completed: {results['total_cleaned']} sessions cleaned")
            
        except Exception as e:
            error_msg = f"Error during cleanup tasks: {e}"
            logger.error(error_msg)
            results['errors'].append(error_msg)
        
        return results

# Global instance
cleanup_tasks = CleanupTasks()

# Convenience functions
def cleanup_expired_sessions():
    """Cleanup expired captcha sessions"""
    return cleanup_tasks.cleanup_expired_captcha_sessions()

def cleanup_old_sessions(days_old=7):
    """Cleanup old captcha sessions"""
    return cleanup_tasks.cleanup_old_captcha_sessions(days_old)

def run_cleanup():
    """Run all cleanup tasks"""
    return cleanup_tasks.run_all_cleanup_tasks()

