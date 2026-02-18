"""
MasterClaw Context Manager

Provides programmatic access to rex-deus context files (goals, knowledge, 
people, preferences, projects) via a unified API.

This module bridges the static rex-deus context files with the MasterClaw
Core API, enabling dynamic context queries and updates.
"""

import os
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger("masterclaw.context")


@dataclass
class Project:
    """Represents a project in rex-deus/projects.md"""
    name: str
    status: str  # active, paused, completed, archived
    priority: str  # critical, high, medium, low
    description: str
    tags: List[str] = field(default_factory=list)
    urls: List[str] = field(default_factory=list)
    updated_at: Optional[str] = None


@dataclass
class Goal:
    """Represents a goal in rex-deus/goals.md"""
    title: str
    status: str  # active, completed, deferred
    priority: str
    description: str
    target_date: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class Person:
    """Represents a person in rex-deus/people.md"""
    name: str
    role: str
    relationship: str
    notes: str
    contact: Optional[str] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class KnowledgeEntry:
    """Represents a knowledge entry in rex-deus/knowledge.md"""
    category: str
    topic: str
    content: str
    confidence: str  # high, medium, low
    source: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class Preference:
    """Represents a preference in rex-deus/preferences.md"""
    category: str
    item: str
    value: str
    priority: str  # required, preferred, optional


class ContextManager:
    """
    Manages access to rex-deus context files.
    
    Provides methods to read, parse, and query context data from:
    - goals.md
    - knowledge.md  
    - people.md
    - preferences.md
    - projects.md
    """
    
    def __init__(self, context_dir: Optional[str] = None):
        """
        Initialize the context manager.
        
        Args:
            context_dir: Path to rex-deus context directory. 
                        Defaults to ~/workspace/rex-deus/context
        """
        if context_dir:
            self.context_dir = Path(context_dir)
        else:
            # Default to workspace/rex-deus/context
            workspace = Path.home() / ".openclaw" / "workspace"
            self.context_dir = workspace / "rex-deus" / "context"
        
        self._cache: Dict[str, Any] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_seconds = 60  # Cache for 1 minute
        
        logger.info(f"ContextManager initialized with context_dir: {self.context_dir}")
    
    def _is_cache_valid(self) -> bool:
        """Check if the cache is still valid based on TTL"""
        if self._cache_timestamp is None:
            return False
        elapsed = (datetime.now() - self._cache_timestamp).total_seconds()
        return elapsed < self._cache_ttl_seconds
    
    def _parse_markdown_sections(self, content: str) -> List[Dict[str, str]]:
        """
        Parse markdown content into sections based on headers.
        
        Returns list of dicts with 'title', 'level', and 'content' keys.
        """
        sections = []
        lines = content.split('\n')
        current_section = None
        current_content = []
        
        for line in lines:
            # Check for header
            if line.startswith('#'):
                # Save previous section
                if current_section:
                    current_section['content'] = '\n'.join(current_content).strip()
                    sections.append(current_section)
                
                # Parse header level and title
                level = len(line) - len(line.lstrip('#'))
                title = line.lstrip('#').strip()
                current_section = {'title': title, 'level': level, 'content': ''}
                current_content = []
            else:
                if current_section is not None:
                    current_content.append(line)
        
        # Don't forget the last section
        if current_section:
            current_section['content'] = '\n'.join(current_content).strip()
            sections.append(current_section)
        
        return sections
    
    def _extract_bullet_items(self, content: str) -> List[str]:
        """Extract bullet list items from markdown content"""
        items = []
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('- ') or line.startswith('* '):
                items.append(line[2:].strip())
        return items
    
    def _parse_key_value_pairs(self, content: str) -> Dict[str, str]:
        """Parse key: value pairs from markdown content"""
        pairs = {}
        for line in content.split('\n'):
            line = line.strip()
            if ':' in line and not line.startswith('-'):
                key, value = line.split(':', 1)
                pairs[key.strip().lower()] = value.strip()
        return pairs
    
    def _read_file(self, filename: str) -> Optional[str]:
        """Read a context file, returning None if not found"""
        filepath = self.context_dir / filename
        try:
            return filepath.read_text(encoding='utf-8')
        except FileNotFoundError:
            logger.warning(f"Context file not found: {filepath}")
            return None
        except Exception as e:
            logger.error(f"Error reading context file {filepath}: {e}")
            return None
    
    def get_projects(self) -> List[Project]:
        """
        Parse and return projects from projects.md
        
        Returns:
            List of Project objects
        """
        content = self._read_file('projects.md')
        if not content:
            return []
        
        projects = []
        sections = self._parse_markdown_sections(content)
        
        current_project = None
        for section in sections:
            title = section['title']
            section_content = section['content']
            
            # Skip the main title
            if title.lower() in ['projects', 'active projects']:
                continue
            
            # Parse project section
            if section['level'] == 2:  # ## Project Name
                if current_project:
                    projects.append(current_project)
                
                pairs = self._parse_key_value_pairs(section_content)
                current_project = Project(
                    name=title,
                    status=pairs.get('status', 'unknown'),
                    priority=pairs.get('priority', 'medium'),
                    description=pairs.get('description', section_content[:200]),
                    tags=self._extract_bullet_items(pairs.get('tags', '')),
                    urls=self._extract_bullet_items(pairs.get('urls', '')),
                    updated_at=pairs.get('updated')
                )
        
        if current_project:
            projects.append(current_project)
        
        return projects
    
    def get_goals(self) -> List[Goal]:
        """
        Parse and return goals from goals.md
        
        Returns:
            List of Goal objects
        """
        content = self._read_file('goals.md')
        if not content:
            return []
        
        goals = []
        sections = self._parse_markdown_sections(content)
        
        current_goal = None
        for section in sections:
            title = section['title']
            section_content = section['content']
            
            if title.lower() in ['goals', 'current goals']:
                continue
            
            if section['level'] == 2:
                if current_goal:
                    goals.append(current_goal)
                
                pairs = self._parse_key_value_pairs(section_content)
                current_goal = Goal(
                    title=title,
                    status=pairs.get('status', 'active'),
                    priority=pairs.get('priority', 'medium'),
                    description=pairs.get('description', section_content[:200]),
                    target_date=pairs.get('target_date') or pairs.get('target date'),
                    completed_at=pairs.get('completed')
                )
        
        if current_goal:
            goals.append(current_goal)
        
        return goals
    
    def get_people(self) -> List[Person]:
        """
        Parse and return people from people.md
        
        Returns:
            List of Person objects
        """
        content = self._read_file('people.md')
        if not content:
            return []
        
        people = []
        sections = self._parse_markdown_sections(content)
        
        current_person = None
        for section in sections:
            title = section['title']
            section_content = section['content']
            
            if title.lower() in ['people', 'key people']:
                continue
            
            if section['level'] == 2:
                if current_person:
                    people.append(current_person)
                
                pairs = self._parse_key_value_pairs(section_content)
                current_person = Person(
                    name=title,
                    role=pairs.get('role', 'unknown'),
                    relationship=pairs.get('relationship', pairs.get('rel', 'contact')),
                    notes=pairs.get('notes', section_content),
                    contact=pairs.get('contact'),
                    tags=self._extract_bullet_items(pairs.get('tags', ''))
                )
        
        if current_person:
            people.append(current_person)
        
        return people
    
    def get_knowledge(self) -> List[KnowledgeEntry]:
        """
        Parse and return knowledge entries from knowledge.md
        
        Returns:
            List of KnowledgeEntry objects
        """
        content = self._read_file('knowledge.md')
        if not content:
            return []
        
        knowledge = []
        sections = self._parse_markdown_sections(content)
        
        current_category = None
        for section in sections:
            title = section['title']
            section_content = section['content']
            
            # Top-level is category
            if section['level'] == 1:
                current_category = title
                continue
            
            if section['level'] == 2 and current_category:
                pairs = self._parse_key_value_pairs(section_content)
                knowledge.append(KnowledgeEntry(
                    category=current_category,
                    topic=title,
                    content=pairs.get('content', section_content),
                    confidence=pairs.get('confidence', 'medium'),
                    source=pairs.get('source'),
                    updated_at=pairs.get('updated')
                ))
        
        return knowledge
    
    def get_preferences(self) -> List[Preference]:
        """
        Parse and return preferences from preferences.md
        
        Returns:
            List of Preference objects
        """
        content = self._read_file('preferences.md')
        if not content:
            return []
        
        preferences = []
        sections = self._parse_markdown_sections(content)
        
        current_category = None
        for section in sections:
            title = section['title']
            section_content = section['content']
            
            # Top-level is category
            if section['level'] == 1:
                current_category = title
                continue
            
            if section['level'] == 2 and current_category:
                pairs = self._parse_key_value_pairs(section_content)
                preferences.append(Preference(
                    category=current_category,
                    item=title,
                    value=pairs.get('value', section_content.strip()),
                    priority=pairs.get('priority', 'preferred')
                ))
        
        return preferences
    
    def query_context(self, query: str) -> Dict[str, List[Any]]:
        """
        Search across all context files for relevant information.
        
        Args:
            query: Search query string
            
        Returns:
            Dict with keys: projects, goals, people, knowledge, preferences
            containing matching items
        """
        query_lower = query.lower()
        results = {
            'projects': [],
            'goals': [],
            'people': [],
            'knowledge': [],
            'preferences': []
        }
        
        # Search projects
        for project in self.get_projects():
            if (query_lower in project.name.lower() or 
                query_lower in project.description.lower() or
                any(query_lower in tag.lower() for tag in project.tags)):
                results['projects'].append(project)
        
        # Search goals
        for goal in self.get_goals():
            if (query_lower in goal.title.lower() or 
                query_lower in goal.description.lower()):
                results['goals'].append(goal)
        
        # Search people
        for person in self.get_people():
            if (query_lower in person.name.lower() or 
                query_lower in person.role.lower() or
                query_lower in person.notes.lower()):
                results['people'].append(person)
        
        # Search knowledge
        for entry in self.get_knowledge():
            if (query_lower in entry.topic.lower() or 
                query_lower in entry.content.lower() or
                query_lower in entry.category.lower()):
                results['knowledge'].append(entry)
        
        # Search preferences
        for pref in self.get_preferences():
            if (query_lower in pref.item.lower() or 
                query_lower in pref.value.lower()):
                results['preferences'].append(pref)
        
        return results
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all context data.
        
        Returns:
            Dict with counts and high-level summary information
        """
        projects = self.get_projects()
        goals = self.get_goals()
        people = self.get_people()
        knowledge = self.get_knowledge()
        preferences = self.get_preferences()
        
        # Calculate status breakdowns
        project_status = {}
        for p in projects:
            project_status[p.status] = project_status.get(p.status, 0) + 1
        
        goal_status = {}
        for g in goals:
            goal_status[g.status] = goal_status.get(g.status, 0) + 1
        
        return {
            'counts': {
                'projects': len(projects),
                'goals': len(goals),
                'people': len(people),
                'knowledge_entries': len(knowledge),
                'preferences': len(preferences)
            },
            'projects': {
                'by_status': project_status,
                'active': [p.name for p in projects if p.status == 'active'],
                'high_priority': [p.name for p in projects if p.priority == 'high']
            },
            'goals': {
                'by_status': goal_status,
                'active': [g.title for g in goals if g.status == 'active']
            },
            'context_dir': str(self.context_dir)
        }


# Singleton instance
_context_manager: Optional[ContextManager] = None


def get_context_manager() -> ContextManager:
    """Get or create the singleton ContextManager instance"""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager


def reset_context_manager():
    """Reset the singleton (useful for testing)"""
    global _context_manager
    _context_manager = None
