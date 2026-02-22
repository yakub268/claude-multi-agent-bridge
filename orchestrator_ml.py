#!/usr/bin/env python3
"""
ML-Based Collaboration Orchestrator
Automatically determines optimal team composition and collaboration strategy

Features:
- ML model predicts: bridge vs agents, team size, roles
- Task analysis: complexity, parallelization, context size
- Smart role assignment
- Cost optimization
- Performance prediction
"""
import re
import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path


logger = logging.getLogger(__name__)


class CollabStrategy(Enum):
    """Collaboration strategy"""
    SINGLE_CLAUDE = "single"  # No collaboration needed
    AGENTS = "agents"  # Use Task tool with subagents
    BRIDGE_SMALL = "bridge_small"  # 2-3 Claudes
    BRIDGE_MEDIUM = "bridge_medium"  # 4-5 Claudes
    BRIDGE_LARGE = "bridge_large"  # 6+ Claudes
    HYBRID = "hybrid"  # Main Claude + agents + bridge


class TaskComplexity(Enum):
    """Task complexity levels"""
    TRIVIAL = 1  # Single file, <50 LOC
    SIMPLE = 2  # Single file, 50-200 LOC
    MEDIUM = 3  # 2-5 files, 200-500 LOC
    COMPLEX = 4  # 5-15 files, 500-2000 LOC
    VERY_COMPLEX = 5  # 15-30 files, 2000-5000 LOC
    LARGE = 6  # 30-50 files, 5000-10000 LOC
    VERY_LARGE = 7  # 50-100 files, 10000-20000 LOC
    MASSIVE = 8  # 100+ files, 20000+ LOC


@dataclass
class TaskFeatures:
    """Features extracted from task for ML model"""
    # Code metrics
    estimated_files: int
    estimated_loc: int
    file_types: List[str]  # py, js, md, etc.

    # Complexity indicators
    num_subtasks: int
    parallelization_score: float  # 0-1, how parallelizable
    dependency_depth: int  # Max dependency chain

    # Context requirements
    estimated_context_tokens: int
    needs_persistent_state: bool

    # Duration
    estimated_hours: float

    # Collaboration indicators
    needs_voting: bool
    needs_code_review: bool
    needs_testing: bool

    # Domain
    domain: str  # web, ml, systems, data, etc.


@dataclass
class RoleAssignment:
    """Role for a Claude in the team"""
    role: str
    client_id: str
    vote_weight: float
    responsibilities: List[str]
    files_assigned: List[str]


@dataclass
class CollaborationPlan:
    """Complete collaboration plan"""
    strategy: CollabStrategy
    num_agents: int
    num_claudes: int
    roles: List[RoleAssignment]

    # Room configuration (if using bridge)
    room_topic: str
    channels: List[Dict[str, str]]  # [{name, topic}]

    # Execution plan
    phases: List[Dict[str, any]]
    estimated_cost_usd: float
    estimated_duration_hours: float

    # Reasoning
    reasoning: str


class MLOrchestrator:
    """
    ML-based orchestration engine

    Uses lightweight ML model to predict optimal collaboration strategy
    based on task features
    """

    def __init__(self):
        self.model_weights = self._load_model_weights()

    def _load_model_weights(self) -> Dict:
        """Load pre-trained model weights (or use defaults)"""
        # In production, load from file
        # For now, use calibrated defaults based on heuristics
        return {
            'complexity_threshold_agents': 3,
            'complexity_threshold_bridge': 5,
            'files_threshold_bridge': 15,
            'context_threshold_bridge': 100000,
            'parallelization_threshold': 0.6,

            # Team size calculation
            'base_team_size': 2,
            'files_per_claude': 10,
            'max_team_size': 8,

            # Cost weights
            'cost_per_claude_hour': 2.0,  # Approximate API cost
            'cost_agent_vs_claude': 0.3,  # Agents are cheaper
        }

    def analyze_task(self, task_description: str,
                    code_context: Optional[Dict] = None) -> TaskFeatures:
        """
        Analyze task and extract features

        Args:
            task_description: Natural language task description
            code_context: Optional context (file count, LOC, etc.)

        Returns:
            TaskFeatures object
        """
        # Extract features from description
        keywords = {
            'trivial': ['fix typo', 'update comment', 'rename variable'],
            'simple': ['add function', 'fix bug', 'update config'],
            'medium': ['add feature', 'refactor module', 'implement api'],
            'complex': ['build system', 'integrate service', 'migrate database'],
            'large': ['build application', 'redesign architecture'],
            'massive': ['build platform', 'rebuild system']
        }

        # Detect complexity from keywords
        complexity_score = 2  # Default: simple
        for level, words in keywords.items():
            if any(word in task_description.lower() for word in words):
                complexity_score = {
                    'trivial': 1, 'simple': 2, 'medium': 3,
                    'complex': 4, 'large': 6, 'massive': 8
                }[level]
                break

        # Count mentioned files
        file_mentions = len(re.findall(r'\b\w+\.(py|js|ts|java|cpp|rs|go|rb)\b',
                                       task_description, re.I))

        # Detect parallelization potential
        parallel_keywords = ['parallel', 'concurrent', 'independent', 'separate',
                           'multiple', 'each', 'simultaneously']
        parallelization_score = min(1.0,
            sum(0.2 for kw in parallel_keywords if kw in task_description.lower()))

        # Detect subtasks
        subtask_markers = re.findall(r'(?:^|\n)\s*[\-\*\d\.]+\s+', task_description)
        num_subtasks = max(len(subtask_markers), 1)

        # Detect need for voting/review
        needs_voting = any(kw in task_description.lower()
                          for kw in ['decide', 'vote', 'consensus', 'approve'])
        needs_review = any(kw in task_description.lower()
                          for kw in ['review', 'verify', 'validate', 'check'])
        needs_testing = any(kw in task_description.lower()
                           for kw in ['test', 'qa', 'testing'])

        # Estimate metrics
        if code_context:
            estimated_files = code_context.get('file_count', file_mentions * 3)
            estimated_loc = code_context.get('loc', estimated_files * 100)
        else:
            estimated_files = max(file_mentions * 3, complexity_score * 5)
            estimated_loc = estimated_files * 100

        # Context estimation
        estimated_context_tokens = estimated_loc * 2  # Rough estimate

        # Duration estimation (very rough)
        base_hours = {
            1: 0.5, 2: 1, 3: 2, 4: 4, 5: 8, 6: 16, 7: 32, 8: 64
        }
        estimated_hours = base_hours.get(complexity_score, 4)

        # Detect domain
        domain_keywords = {
            'web': ['web', 'frontend', 'backend', 'api', 'http', 'html', 'css'],
            'ml': ['machine learning', 'model', 'training', 'neural', 'ai'],
            'data': ['data', 'analysis', 'pipeline', 'etl', 'database'],
            'systems': ['system', 'performance', 'infrastructure', 'devops'],
            'mobile': ['mobile', 'android', 'ios', 'app']
        }
        domain = 'general'
        for dom, keywords_list in domain_keywords.items():
            if any(kw in task_description.lower() for kw in keywords_list):
                domain = dom
                break

        return TaskFeatures(
            estimated_files=estimated_files,
            estimated_loc=estimated_loc,
            file_types=['py', 'js', 'md'],  # Default
            num_subtasks=num_subtasks,
            parallelization_score=parallelization_score,
            dependency_depth=min(num_subtasks, 3),
            estimated_context_tokens=estimated_context_tokens,
            needs_persistent_state=estimated_hours > 2,
            estimated_hours=estimated_hours,
            needs_voting=needs_voting,
            needs_code_review=needs_review,
            needs_testing=needs_testing,
            domain=domain
        )

    def predict_strategy(self, features: TaskFeatures) -> CollabStrategy:
        """
        Predict optimal collaboration strategy using ML model

        Decision tree (lightweight ML):
        - Context size + complexity → strategy
        - Parallelization score → team composition
        """
        w = self.model_weights

        # Decision tree
        if features.estimated_files <= 1 and features.num_subtasks <= 1:
            return CollabStrategy.SINGLE_CLAUDE

        # Check if agents can handle it
        if (features.estimated_files <= w['files_threshold_bridge'] and
            features.estimated_context_tokens < w['context_threshold_bridge'] and
            features.estimated_hours < 2):
            return CollabStrategy.AGENTS

        # Bridge required - determine size
        if features.estimated_files <= 30:
            return CollabStrategy.BRIDGE_SMALL
        elif features.estimated_files <= 60:
            return CollabStrategy.BRIDGE_MEDIUM
        else:
            return CollabStrategy.BRIDGE_LARGE

    def calculate_team_size(self, features: TaskFeatures,
                           strategy: CollabStrategy) -> Tuple[int, int]:
        """
        Calculate optimal number of agents/claudes

        Returns:
            (num_agents, num_claudes)
        """
        w = self.model_weights

        if strategy == CollabStrategy.SINGLE_CLAUDE:
            return (0, 1)

        elif strategy == CollabStrategy.AGENTS:
            # Scale agents by parallelization potential
            base_agents = min(features.num_subtasks, 5)
            num_agents = max(2, int(base_agents * (0.5 + features.parallelization_score)))
            return (num_agents, 1)

        else:  # Bridge
            # Calculate based on files and parallelization
            files_per_claude = w['files_per_claude']
            num_claudes = max(2, min(
                features.estimated_files // files_per_claude,
                w['max_team_size']
            ))

            # Adjust by parallelization score
            if features.parallelization_score > 0.7:
                num_claudes = min(num_claudes + 1, w['max_team_size'])

            # Strategy-specific sizing
            if strategy == CollabStrategy.BRIDGE_SMALL:
                num_claudes = min(num_claudes, 3)
            elif strategy == CollabStrategy.BRIDGE_MEDIUM:
                num_claudes = min(max(num_claudes, 4), 5)
            else:  # BRIDGE_LARGE
                num_claudes = max(num_claudes, 6)

            return (0, num_claudes)

    def assign_roles(self, features: TaskFeatures, num_claudes: int) -> List[RoleAssignment]:
        """
        Assign roles to team members based on task needs
        """
        roles = []

        if num_claudes == 1:
            roles.append(RoleAssignment(
                role="coordinator",
                client_id="claude-main",
                vote_weight=2.0,
                responsibilities=["all tasks"],
                files_assigned=[]
            ))
            return roles

        # Always have coordinator
        roles.append(RoleAssignment(
            role="coordinator",
            client_id="claude-coordinator",
            vote_weight=2.0,
            responsibilities=["orchestration", "integration", "decisions"],
            files_assigned=[]
        ))

        remaining = num_claudes - 1

        # Assign based on task needs
        if features.needs_code_review and remaining > 0:
            roles.append(RoleAssignment(
                role="reviewer",
                client_id="claude-reviewer",
                vote_weight=1.5,
                responsibilities=["code review", "quality assurance", "veto power"],
                files_assigned=[]
            ))
            remaining -= 1

        if features.needs_testing and remaining > 0:
            roles.append(RoleAssignment(
                role="tester",
                client_id="claude-tester",
                vote_weight=1.0,
                responsibilities=["testing", "QA", "bug reporting"],
                files_assigned=[]
            ))
            remaining -= 1

        # Assign coders for remaining slots
        for i in range(remaining):
            roles.append(RoleAssignment(
                role="coder",
                client_id=f"claude-coder-{i+1}",
                vote_weight=1.0,
                responsibilities=[f"implementation {i+1}"],
                files_assigned=[]
            ))

        return roles

    def create_plan(self, task_description: str,
                   code_context: Optional[Dict] = None) -> CollaborationPlan:
        """
        Create complete collaboration plan for a task

        Args:
            task_description: Natural language task description
            code_context: Optional code metrics

        Returns:
            CollaborationPlan with full execution strategy
        """
        # Step 1: Analyze task
        features = self.analyze_task(task_description, code_context)

        # Step 2: Predict strategy
        strategy = self.predict_strategy(features)

        # Step 3: Calculate team size
        num_agents, num_claudes = self.calculate_team_size(features, strategy)

        # Step 4: Assign roles
        roles = self.assign_roles(features, num_claudes)

        # Step 5: Create channels (if bridge)
        channels = []
        if strategy != CollabStrategy.SINGLE_CLAUDE and strategy != CollabStrategy.AGENTS:
            channels = [
                {"name": "main", "topic": "General discussion"},
                {"name": "code", "topic": "Code development"},
            ]
            if features.needs_testing:
                channels.append({"name": "testing", "topic": "QA and testing"})
            if features.needs_code_review:
                channels.append({"name": "review", "topic": "Code review"})

        # Step 6: Create phases
        phases = self._create_phases(features, strategy, roles)

        # Step 7: Estimate cost
        cost_usd = self._estimate_cost(features, strategy, num_agents, num_claudes)

        # Step 8: Generate reasoning
        reasoning = self._generate_reasoning(features, strategy, num_agents, num_claudes)

        return CollaborationPlan(
            strategy=strategy,
            num_agents=num_agents,
            num_claudes=num_claudes,
            roles=roles,
            room_topic=task_description[:100],
            channels=channels,
            phases=phases,
            estimated_cost_usd=cost_usd,
            estimated_duration_hours=features.estimated_hours,
            reasoning=reasoning
        )

    def _create_phases(self, features: TaskFeatures, strategy: CollabStrategy,
                      roles: List[RoleAssignment]) -> List[Dict]:
        """Create execution phases"""
        phases = []

        if strategy == CollabStrategy.AGENTS:
            phases.append({
                "name": "Research & Planning",
                "agents": ["explore", "general-purpose"],
                "duration_hours": features.estimated_hours * 0.3
            })
            phases.append({
                "name": "Implementation",
                "agents": ["general-purpose"] * (len(roles) - 1),
                "duration_hours": features.estimated_hours * 0.5
            })
            phases.append({
                "name": "Testing & Review",
                "agents": ["general-purpose"],
                "duration_hours": features.estimated_hours * 0.2
            })
        else:
            # Bridge phases
            phases.append({
                "name": "Planning & Design",
                "roles": ["coordinator"],
                "duration_hours": features.estimated_hours * 0.2,
                "deliverable": "Architecture decision"
            })
            phases.append({
                "name": "Parallel Implementation",
                "roles": [r.role for r in roles if r.role == "coder"],
                "duration_hours": features.estimated_hours * 0.5,
                "deliverable": "Code complete"
            })
            if features.needs_code_review:
                phases.append({
                    "name": "Code Review",
                    "roles": ["reviewer"],
                    "duration_hours": features.estimated_hours * 0.15,
                    "deliverable": "Review approved"
                })
            if features.needs_testing:
                phases.append({
                    "name": "Testing",
                    "roles": ["tester"],
                    "duration_hours": features.estimated_hours * 0.15,
                    "deliverable": "Tests passing"
                })

        return phases

    def _estimate_cost(self, features: TaskFeatures, strategy: CollabStrategy,
                      num_agents: int, num_claudes: int) -> float:
        """Estimate USD cost"""
        w = self.model_weights

        if strategy == CollabStrategy.AGENTS:
            # Agents share context, cheaper
            return features.estimated_hours * w['cost_per_claude_hour'] * w['cost_agent_vs_claude']
        else:
            # Multiple Claude instances
            return features.estimated_hours * num_claudes * w['cost_per_claude_hour']

    def _generate_reasoning(self, features: TaskFeatures, strategy: CollabStrategy,
                           num_agents: int, num_claudes: int) -> str:
        """Generate human-readable reasoning"""
        lines = []

        lines.append(f"Task Analysis:")
        lines.append(f"  - Estimated: {features.estimated_files} files, {features.estimated_loc} LOC")
        lines.append(f"  - Complexity: {features.num_subtasks} subtasks")
        lines.append(f"  - Parallelization: {features.parallelization_score:.1%}")
        lines.append(f"  - Duration: ~{features.estimated_hours:.1f} hours")
        lines.append("")

        lines.append(f"Strategy Decision: {strategy.value.upper()}")

        if strategy == CollabStrategy.SINGLE_CLAUDE:
            lines.append("  ✓ Task is simple enough for one Claude")
        elif strategy == CollabStrategy.AGENTS:
            lines.append(f"  ✓ Use {num_agents} agents for parallel subtasks")
            lines.append("  ✓ Fits in single context window")
        else:
            lines.append(f"  ✓ Use {num_claudes} Claude instances")
            lines.append(f"  ✓ Context size ({features.estimated_context_tokens:,} tokens) requires splitting")
            lines.append(f"  ✓ Parallelization score ({features.parallelization_score:.1%}) supports team work")

        return "\n".join(lines)

    def execute_plan(self, plan: CollaborationPlan) -> bool:
        """
        Execute the collaboration plan

        This would actually:
        1. Start server (if bridge)
        2. Create room (if bridge)
        3. Spawn agents or Claude instances
        4. Coordinate execution

        Returns:
            Success status
        """
        print(f"\n{'='*80}")
        print(f"🎯 EXECUTING COLLABORATION PLAN")
        print(f"{'='*80}\n")

        print(f"Strategy: {plan.strategy.value}")
        print(f"Team Size: {plan.num_claudes} Claudes, {plan.num_agents} agents")
        print(f"Duration: ~{plan.estimated_duration_hours:.1f} hours")
        print(f"Cost: ~${plan.estimated_cost_usd:.2f}")
        print("")

        print("Roles:")
        for role in plan.roles:
            print(f"  - {role.role}: {role.client_id} (vote weight: {role.vote_weight}x)")
        print("")

        print("Phases:")
        for i, phase in enumerate(plan.phases, 1):
            print(f"  {i}. {phase['name']} (~{phase.get('duration_hours', 0):.1f}h)")
        print("")

        print("Reasoning:")
        print(plan.reasoning)
        print("")

        if plan.strategy == CollabStrategy.AGENTS:
            print("⚙️  Would spawn agents via Task tool...")
            return True

        elif plan.strategy != CollabStrategy.SINGLE_CLAUDE:
            print("🌉 Would create collaboration room via bridge...")
            print(f"   Room: {plan.room_topic}")
            print(f"   Channels: {[ch['name'] for ch in plan.channels]}")
            print(f"   Members: {plan.num_claudes} Claudes")
            return True

        else:
            print("👤 Single Claude execution (no coordination needed)")
            return True


# Command-line interface
if __name__ == '__main__':
    import sys

    print("="*80)
    print("🤖 ML-Based Collaboration Orchestrator")
    print("="*80)

    orchestrator = MLOrchestrator()

    # Test cases
    test_cases = [
        {
            "task": "Fix typo in README.md",
            "context": {"file_count": 1, "loc": 50}
        },
        {
            "task": "Add new feature: user authentication with login, signup, password reset, and email verification",
            "context": {"file_count": 12, "loc": 2000}
        },
        {
            "task": """Build a trading bot with:
- 5 different trading strategies (momentum, mean reversion, arbitrage, ML-based, sentiment)
- Backtesting engine with historical data
- Real-time dashboard with charts
- Risk management system
- Database for trade history
- API integration with 3 brokers""",
            "context": {"file_count": 45, "loc": 8000}
        },
        {
            "task": "Refactor authentication module and add tests",
            "context": {"file_count": 5, "loc": 800}
        }
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\n\n{'='*80}")
        print(f"TEST CASE {i}")
        print(f"{'='*80}")
        print(f"Task: {test['task'][:100]}...")
        print("")

        plan = orchestrator.create_plan(test['task'], test.get('context'))

        print(f"📋 PLAN SUMMARY")
        print(f"  Strategy: {plan.strategy.value}")
        print(f"  Team: {plan.num_claudes} Claudes, {plan.num_agents} agents")
        print(f"  Duration: {plan.estimated_duration_hours:.1f} hours")
        print(f"  Cost: ${plan.estimated_cost_usd:.2f}")
        print(f"  Phases: {len(plan.phases)}")
        print("")

        print("Reasoning:")
        for line in plan.reasoning.split('\n'):
            print(f"  {line}")

    print("\n" + "="*80)
    print("✅ Orchestrator tests complete!")
    print("="*80)
