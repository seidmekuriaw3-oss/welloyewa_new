# ============================
# WOLLOYEWA STORE BOT - TEAM MANAGEMENT
# ============================
"""Team management for multi-tenant organizations."""

from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from core.logger import logger


class TeamRole(str, Enum):
    """Team member roles."""
    OWNER = "owner"          # Full access, can delete team
    ADMIN = "admin"          # Full access except deleting team
    MANAGER = "manager"      # Can manage members and settings
    MEMBER = "member"        # Can access team resources
    VIEWER = "viewer"        # Read-only access


@dataclass
class TeamMember:
    """Team member information."""
    
    user_id: int
    email: str
    name: str
    role: TeamRole
    joined_at: datetime = field(default_factory=datetime.utcnow)
    invited_by: Optional[int] = None
    is_active: bool = True


@dataclass
class Team:
    """Team information."""
    
    id: str
    name: str
    tenant_id: str
    description: Optional[str] = None
    created_by: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    settings: Dict[str, Any] = field(default_factory=dict)
    members: List[TeamMember] = field(default_factory=list)


@dataclass
class Invitation:
    """Team invitation."""
    
    id: str
    team_id: str
    email: str
    role: TeamRole
    invited_by: int
    invited_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = None
    accepted_at: Optional[datetime] = None
    is_active: bool = True


class TeamManager:
    """
    Team management for multi-tenant organizations.
    
    Features:
    - Create and manage teams
    - Add/remove members
    - Role-based access control
    - Invitation system
    """
    
    def __init__(self, db_session):
        self.db = db_session
        self._teams: Dict[str, Team] = {}
        self._invitations: Dict[str, Invitation] = {}
    
    async def create_team(
        self,
        name: str,
        tenant_id: str,
        created_by: int,
        description: Optional[str] = None,
    ) -> Team:
        """
        Create a new team.
        
        Args:
            name: Team name
            tenant_id: Tenant ID
            created_by: User ID of creator
            description: Team description
            
        Returns:
            Created Team
        """
        import uuid
        team_id = str(uuid.uuid4())
        
        team = Team(
            id=team_id,
            name=name,
            tenant_id=tenant_id,
            description=description,
            created_by=created_by,
        )
        
        # Add creator as owner
        owner = TeamMember(
            user_id=created_by,
            email="",  # Would be populated from user service
            name="",   # Would be populated from user service
            role=TeamRole.OWNER,
        )
        team.members.append(owner)
        
        self._teams[team_id] = team
        logger.info(f"Team created: {name} (ID: {team_id})")
        
        return team
    
    async def get_team(self, team_id: str) -> Optional[Team]:
        """Get team by ID."""
        return self._teams.get(team_id)
    
    async def get_teams_for_user(self, user_id: int, tenant_id: str) -> List[Team]:
        """Get all teams a user belongs to."""
        user_teams = []
        
        for team in self._teams.values():
            if team.tenant_id != tenant_id:
                continue
            
            for member in team.members:
                if member.user_id == user_id and member.is_active:
                    user_teams.append(team)
                    break
        
        return user_teams
    
    async def add_member(
        self,
        team_id: str,
        user_id: int,
        email: str,
        name: str,
        role: TeamRole,
        added_by: int,
    ) -> Optional[TeamMember]:
        """
        Add a member to a team.
        
        Args:
            team_id: Team ID
            user_id: User ID to add
            email: User email
            name: User name
            role: Role to assign
            added_by: User ID adding the member
            
        Returns:
            Added TeamMember or None
        """
        team = await self.get_team(team_id)
        if not team:
            logger.warning(f"Team not found: {team_id}")
            return None
        
        # Check if user is already a member
        for member in team.members:
            if member.user_id == user_id:
                logger.warning(f"User {user_id} already in team {team_id}")
                return None
        
        # Check if adder has permission
        adder_member = await self.get_member(team_id, added_by)
        if not adder_member or adder_member.role not in [TeamRole.OWNER, TeamRole.ADMIN, TeamRole.MANAGER]:
            logger.warning(f"User {added_by} lacks permission to add members to team {team_id}")
            return None
        
        # Create new member
        member = TeamMember(
            user_id=user_id,
            email=email,
            name=name,
            role=role,
            invited_by=added_by,
        )
        
        team.members.append(member)
        logger.info(f"Added user {user_id} to team {team_id} as {role.value}")
        
        return member
    
    async def remove_member(
        self,
        team_id: str,
        user_id: int,
        removed_by: int,
    ) -> bool:
        """
        Remove a member from a team.
        
        Args:
            team_id: Team ID
            user_id: User ID to remove
            removed_by: User ID performing removal
            
        Returns:
            True if removed
        """
        team = await self.get_team(team_id)
        if not team:
            return False
        
        # Check if remover has permission
        remover_member = await self.get_member(team_id, removed_by)
        target_member = await self.get_member(team_id, user_id)
        
        if not remover_member or not target_member:
            return False
        
        # Owner cannot be removed by anyone
        if target_member.role == TeamRole.OWNER:
            logger.warning(f"Cannot remove owner {user_id} from team {team_id}")
            return False
        
        # Only owners and admins can remove members
        if remover_member.role not in [TeamRole.OWNER, TeamRole.ADMIN]:
            logger.warning(f"User {removed_by} lacks permission to remove members")
            return False
        
        # Remove member
        team.members = [m for m in team.members if m.user_id != user_id]
        logger.info(f"Removed user {user_id} from team {team_id}")
        
        return True
    
    async def update_member_role(
        self,
        team_id: str,
        user_id: int,
        new_role: TeamRole,
        updated_by: int,
    ) -> bool:
        """
        Update a member's role.
        
        Args:
            team_id: Team ID
            user_id: User ID to update
            new_role: New role
            updated_by: User ID performing update
            
        Returns:
            True if updated
        """
        team = await self.get_team(team_id)
        if not team:
            return False
        
        updater = await self.get_member(team_id, updated_by)
        target = await self.get_member(team_id, user_id)
        
        if not updater or not target:
            return False
        
        # Permission checks
        if updater.role == TeamRole.OWNER:
            # Owner can change any role
            pass
        elif updater.role == TeamRole.ADMIN:
            # Admin cannot change owner or other admins
            if target.role in [TeamRole.OWNER, TeamRole.ADMIN]:
                return False
        else:
            # Only owners and admins can change roles
            return False
        
        # Cannot change owner role
        if target.role == TeamRole.OWNER:
            return False
        
        target.role = new_role
        logger.info(f"Updated role of user {user_id} in team {team_id} to {new_role.value}")
        
        return True
    
    async def get_member(self, team_id: str, user_id: int) -> Optional[TeamMember]:
        """Get a team member."""
        team = await self.get_team(team_id)
        if not team:
            return None
        
        for member in team.members:
            if member.user_id == user_id and member.is_active:
                return member
        
        return None
    
    async def create_invitation(
        self,
        team_id: str,
        email: str,
        role: TeamRole,
        invited_by: int,
        expires_in_days: int = 7,
    ) -> Optional[Invitation]:
        """Create a team invitation."""
        import uuid
        
        team = await self.get_team(team_id)
        if not team:
            return None
        
        inviter = await self.get_member(team_id, invited_by)
        if not inviter or inviter.role not in [TeamRole.OWNER, TeamRole.ADMIN, TeamRole.MANAGER]:
            return None
        
        invitation = Invitation(
            id=str(uuid.uuid4()),
            team_id=team_id,
            email=email,
            role=role,
            invited_by=invited_by,
            expires_at=datetime.utcnow() + timedelta(days=expires_in_days),
        )
        
        self._invitations[invitation.id] = invitation
        logger.info(f"Created invitation for {email} to join team {team_id}")
        
        return invitation


# Global team manager (would be initialized with DB session)
team_manager = None


async def create_team(db, name: str, tenant_id: str, created_by: int) -> Team:
    """Create a new team."""
    manager = TeamManager(db)
    return await manager.create_team(name, tenant_id, created_by)


async def add_team_member(db, team_id: str, user_id: int, email: str, name: str, role: TeamRole, added_by: int) -> Optional[TeamMember]:
    """Add a member to a team."""
    manager = TeamManager(db)
    return await manager.add_member(team_id, user_id, email, name, role, added_by)


async def remove_team_member(db, team_id: str, user_id: int, removed_by: int) -> bool:
    """Remove a member from a team."""
    manager = TeamManager(db)
    return await manager.remove_member(team_id, user_id, removed_by)


async def update_member_role(db, team_id: str, user_id: int, new_role: TeamRole, updated_by: int) -> bool:
    """Update a member's role."""
    manager = TeamManager(db)
    return await manager.update_member_role(team_id, user_id, new_role, updated_by)


__all__ = [
    "TeamManager",
    "Team",
    "TeamMember",
    "TeamRole",
    "Invitation",
    "create_team",
    "add_team_member",
    "remove_team_member",
    "update_member_role",
]