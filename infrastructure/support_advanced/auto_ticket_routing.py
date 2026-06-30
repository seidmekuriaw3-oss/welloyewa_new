# ============================
# WOLLOYEWA STORE BOT - AUTO TICKET ROUTING
# ============================
"""Automatic ticket routing to appropriate support agents."""

from enum import Enum
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from core.logger import logger


class RoutingStrategy(str, Enum):
    """Routing strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    SKILL_BASED = "skill_based"
    PRIORITY_BASED = "priority_based"


@dataclass
class RoutingRule:
    """Rule for routing tickets."""
    
    rule_id: str
    condition: str  # e.g., "category == 'payment'"
    target_team: str
    target_skills: List[str] = field(default_factory=list)
    priority: int = 0
    is_active: bool = True


@dataclass
class Agent:
    """Support agent information."""
    
    user_id: int
    name: str
    skills: List[str] = field(default_factory=list)
    current_load: int = 0
    max_load: int = 10
    is_online: bool = True
    last_assigned: Optional[datetime] = None


class AutoTicketRouter:
    """
    Automatic ticket router.
    
    Features:
    - Skill-based routing
    - Load balancing
    - Priority handling
    - Agent availability tracking
    """
    
    def __init__(self):
        self._agents: Dict[int, Agent] = {}
        self._rules: List[RoutingRule] = []
        self._routing_history: List[Dict[str, Any]] = []
        self._strategy = RoutingStrategy.SKILL_BASED
    
    def register_agent(self, agent: Agent) -> None:
        """Register a support agent."""
        self._agents[agent.user_id] = agent
        logger.info(f"Registered agent: {agent.name} (ID: {agent.user_id})")
    
    def update_agent_status(self, user_id: int, is_online: bool) -> None:
        """Update agent online status."""
        if user_id in self._agents:
            self._agents[user_id].is_online = is_online
            logger.info(f"Agent {user_id} is now {'online' if is_online else 'offline'}")
    
    def update_agent_load(self, user_id: int, load_change: int) -> None:
        """Update agent current load."""
        if user_id in self._agents:
            self._agents[user_id].current_load += load_change
            self._agents[user_id].current_load = max(0, self._agents[user_id].current_load)
    
    def add_routing_rule(self, rule: RoutingRule) -> None:
        """Add a routing rule."""
        self._rules.append(rule)
        # Sort by priority (higher priority first)
        self._rules.sort(key=lambda r: r.priority, reverse=True)
        logger.info(f"Added routing rule: {rule.rule_id}")
    
    def get_agent_for_ticket(
        self,
        ticket_category: str,
        ticket_priority: str,
        required_skills: List[str] = None,
    ) -> Optional[Agent]:
        """
        Get the best agent for a ticket.
        
        Args:
            ticket_category: Ticket category
            ticket_priority: Ticket priority
            required_skills: Required skills for the ticket
            
        Returns:
            Best agent or None
        """
        available_agents = [
            a for a in self._agents.values()
            if a.is_online and a.current_load < a.max_load
        ]
        
        if not available_agents:
            logger.warning("No available agents found")
            return None
        
        # Apply routing rules
        matched_team = None
        for rule in self._rules:
            if rule.is_active and self._evaluate_rule(rule, ticket_category):
                matched_team = rule.target_team
                if rule.target_skills:
                    required_skills = rule.target_skills
                break
        
        # Filter by required skills
        if required_skills:
            available_agents = [
                a for a in available_agents
                if any(skill in a.skills for skill in required_skills)
            ]
        
        # Apply routing strategy
        if self._strategy == RoutingStrategy.LEAST_LOADED:
            available_agents.sort(key=lambda a: a.current_load)
        elif self._strategy == RoutingStrategy.ROUND_ROBIN:
            available_agents.sort(key=lambda a: a.last_assigned or datetime.min)
        elif self._strategy == RoutingStrategy.PRIORITY_BASED:
            # High priority tickets go to most experienced agents
            if ticket_priority == "high" or ticket_priority == "urgent":
                available_agents.sort(key=lambda a: len(a.skills), reverse=True)
            else:
                available_agents.sort(key=lambda a: a.current_load)
        
        if available_agents:
            best_agent = available_agents[0]
            best_agent.last_assigned = datetime.utcnow()
            best_agent.current_load += 1
            
            # Record routing
            self._routing_history.append({
                "ticket_category": ticket_category,
                "ticket_priority": ticket_priority,
                "assigned_agent": best_agent.user_id,
                "strategy": self._strategy.value,
                "timestamp": datetime.utcnow(),
            })
            
            return best_agent
        
        return None
    
    def _evaluate_rule(self, rule: RoutingRule, ticket_category: str) -> bool:
        """Evaluate if rule matches ticket."""
        # Simple condition evaluation
        # In production, use a proper expression evaluator
        condition = rule.condition
        return condition.replace("category", f"'{ticket_category}'").replace("==", "in")
    
    def set_strategy(self, strategy: RoutingStrategy) -> None:
        """Set routing strategy."""
        self._strategy = strategy
        logger.info(f"Routing strategy set to: {strategy.value}")
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics."""
        stats = {
            "total_agents": len(self._agents),
            "online_agents": sum(1 for a in self._agents.values() if a.is_online),
            "available_agents": sum(1 for a in self._agents.values() if a.is_online and a.current_load < a.max_load),
            "total_routings": len(self._routing_history),
            "strategy": self._strategy.value,
            "agents": [
                {
                    "user_id": a.user_id,
                    "name": a.name,
                    "skills": a.skills,
                    "current_load": a.current_load,
                    "max_load": a.max_load,
                    "is_online": a.is_online,
                }
                for a in self._agents.values()
            ],
        }
        return stats


# Global ticket router
ticket_router = AutoTicketRouter()


async def route_ticket(
    ticket_category: str,
    ticket_priority: str,
    required_skills: List[str] = None,
) -> Optional[Agent]:
    """Route a ticket to the best agent."""
    return ticket_router.get_agent_for_ticket(ticket_category, ticket_priority, required_skills)


async def get_routing_stats() -> Dict[str, Any]:
    """Get routing statistics."""
    return ticket_router.get_routing_stats()


async def assign_best_agent(
    ticket_id: int,
    ticket_category: str,
    ticket_priority: str,
) -> Optional[int]:
    """Assign best agent to a ticket."""
    agent = ticket_router.get_agent_for_ticket(ticket_category, ticket_priority)
    
    if agent:
        # Update ticket with assigned agent
        # This would update the database
        logger.info(f"Ticket {ticket_id} assigned to agent {agent.user_id}")
        return agent.user_id
    
    logger.warning(f"No agent available for ticket {ticket_id}")
    return None


TicketRouter = AutoTicketRouter

__all__ = [
    "AutoTicketRouter",
    "TicketRouter",
    "RoutingRule",
    "RoutingStrategy",
    "Agent",
    "ticket_router",
    "route_ticket",
    "get_routing_stats",
    "assign_best_agent",
]