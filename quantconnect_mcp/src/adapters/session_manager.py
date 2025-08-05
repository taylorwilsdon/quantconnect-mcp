"""Session Manager for QuantConnect Research Sessions"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .research_session_lean_cli import ResearchSession, ResearchSessionError

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages multiple ResearchSession instances with lifecycle management,
    cleanup, and resource monitoring.
    """
    
    def __init__(
        self,
        max_sessions: int = 10,
        session_timeout: timedelta = timedelta(hours=1),
        cleanup_interval: int = 300,  # 5 minutes
    ):
        """
        Initialize the session manager.
        
        Args:
            max_sessions: Maximum number of concurrent sessions
            session_timeout: How long idle sessions are kept alive
            cleanup_interval: How often to run cleanup in seconds
        """
        self.max_sessions = max_sessions
        self.session_timeout = session_timeout
        self.cleanup_interval = cleanup_interval
        
        self._sessions: Dict[str, ResearchSession] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info(f"SessionManager initialized (max_sessions={max_sessions})")
    
    async def start(self) -> None:
        """Start the session manager and cleanup task."""
        if self._running:
            return
        
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("SessionManager started")
    
    async def stop(self) -> None:
        """Stop the session manager and clean up all sessions."""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Clean up all sessions
        await self.cleanup_all_sessions()
        logger.info("SessionManager stopped")
    
    async def get_or_create_session(
        self,
        session_id: str,
        **session_kwargs
    ) -> ResearchSession:
        """
        Get an existing session or create a new one.
        
        Args:
            session_id: Unique session identifier
            **session_kwargs: Additional arguments for ResearchSession
            
        Returns:
            ResearchSession instance
            
        Raises:
            ResearchSessionError: If max sessions exceeded or creation fails
        """
        # Check if session already exists
        if session_id in self._sessions:
            session = self._sessions[session_id]
            session.last_used = datetime.utcnow()
            logger.debug(f"Retrieved existing session {session_id}")
            return session
        
        # Check session limit
        if len(self._sessions) >= self.max_sessions:
            # Try to clean up expired sessions first
            await self._cleanup_expired_sessions()
            
            if len(self._sessions) >= self.max_sessions:
                raise ResearchSessionError(
                    f"Maximum number of sessions ({self.max_sessions}) reached. "
                    "Please close unused sessions or wait for them to expire."
                )
        
        # Create new session
        try:
            session = ResearchSession(session_id=session_id, **session_kwargs)
            await session.initialize()
            
            self._sessions[session_id] = session
            logger.info(f"Created new research session {session_id}")
            return session
        
        except Exception as e:
            logger.error(f"Failed to create session {session_id}: {e}")
            raise ResearchSessionError(f"Failed to create session: {e}")
    
    async def get_session(self, session_id: str) -> Optional[ResearchSession]:
        """
        Get an existing session without creating a new one.
        
        Args:
            session_id: Session identifier
            
        Returns:
            ResearchSession or None if not found
        """
        session = self._sessions.get(session_id)
        if session:
            session.last_used = datetime.utcnow()
        return session
    
    async def close_session(self, session_id: str) -> bool:
        """
        Close and remove a specific session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session was found and closed, False otherwise
        """
        session = self._sessions.pop(session_id, None)
        if session:
            await session.close()
            logger.info(f"Closed session {session_id}")
            return True
        return False
    
    async def cleanup_all_sessions(self) -> None:
        """Close and remove all sessions."""
        session_ids = list(self._sessions.keys())
        for session_id in session_ids:
            await self.close_session(session_id)
        
        logger.info(f"Cleaned up {len(session_ids)} sessions")
    
    def list_sessions(self) -> List[Dict[str, any]]:
        """
        Get information about all active sessions.
        
        Returns:
            List of session information dictionaries
        """
        return [
            {
                "session_id": session.session_id,
                "created_at": session.created_at.isoformat(),
                "last_used": getattr(session, 'last_used', session.created_at).isoformat(),
                "initialized": session._initialized,
                "workspace_dir": str(session.workspace_dir),
                "port": getattr(session, 'port', 8888),
            }
            for session in self._sessions.values()
        ]
    
    def get_session_count(self) -> Dict[str, int]:
        """Get session count information."""
        return {
            "active_sessions": len(self._sessions),
            "max_sessions": self.max_sessions,
            "available_slots": max(0, self.max_sessions - len(self._sessions)),
        }
    
    async def _cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions and return count of cleaned sessions."""
        expired_sessions = []
        now = datetime.utcnow()
        
        for session_id, session in self._sessions.items():
            if session.is_expired(self.session_timeout):
                expired_sessions.append(session_id)
        
        # Close expired sessions
        for session_id in expired_sessions:
            await self.close_session(session_id)
        
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
        
        return len(expired_sessions)
    
    async def _cleanup_loop(self) -> None:
        """Background task for periodic session cleanup."""
        logger.info(f"Session cleanup loop started (interval={self.cleanup_interval}s)")
        
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                if self._running:
                    await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
        
        logger.info("Session cleanup loop stopped")


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


async def initialize_session_manager() -> None:
    """Initialize and start the global session manager."""
    manager = get_session_manager()
    if not manager._running:
        await manager.start()


async def shutdown_session_manager() -> None:
    """Shutdown the global session manager."""
    global _session_manager
    if _session_manager and _session_manager._running:
        await _session_manager.stop()
        _session_manager = None