#!/usr/bin/env python3
"""
Unit tests for ML Orchestrator

Run with: pytest tests/test_orchestrator.py -v
"""
import pytest
from orchestrator_ml import MLOrchestrator, CollabStrategy, ClaudeModel


class TestMLOrchestrator:
    """Test ML orchestrator functionality"""

    def setup_method(self):
        """Setup test fixture"""
        self.orchestrator = MLOrchestrator()

    def test_trivial_task(self):
        """Test trivial task uses SINGLE_CLAUDE"""
        plan = self.orchestrator.create_plan(
            "Fix typo in README.md",
            {"file_count": 1, "loc": 50}
        )

        assert plan.strategy == CollabStrategy.SINGLE_CLAUDE
        assert plan.num_claudes == 1
        assert plan.num_agents == 0

    def test_medium_task_uses_agents(self):
        """Test medium task uses agents"""
        plan = self.orchestrator.create_plan(
            "Add user authentication with login and signup",
            {"file_count": 8, "loc": 1200}
        )

        assert plan.strategy == CollabStrategy.AGENTS
        assert plan.num_agents > 0
        assert plan.num_claudes <= 1

    def test_large_task_uses_bridge(self):
        """Test large task uses bridge"""
        plan = self.orchestrator.create_plan(
            "Build REST API with 25 endpoints",
            {"file_count": 25, "loc": 4000}
        )

        assert plan.strategy in [
            CollabStrategy.BRIDGE_SMALL,
            CollabStrategy.BRIDGE_MEDIUM,
            CollabStrategy.BRIDGE_LARGE
        ]
        assert plan.num_claudes >= 2

    def test_model_selection_opus_for_complex(self):
        """Test Opus selected for complex coordinator tasks"""
        plan = self.orchestrator.create_plan(
            "Build trading bot with 45 files",
            {"file_count": 45, "loc": 8000}
        )

        coordinator = next(r for r in plan.roles if r.role == "coordinator")
        assert coordinator.model == ClaudeModel.OPUS

    def test_model_selection_haiku_for_simple(self):
        """Test Haiku selected for simple tasks"""
        plan = self.orchestrator.create_plan(
            "Add unit tests for 3 functions",
            {"file_count": 3, "loc": 200}
        )

        # Should have a tester role with Haiku
        if plan.num_claudes > 1:
            tester = next((r for r in plan.roles if r.role == "tester"), None)
            if tester:
                assert tester.model == ClaudeModel.HAIKU

    def test_planning_mode_for_large_tasks(self):
        """Test planning mode enabled for large tasks"""
        plan = self.orchestrator.create_plan(
            "Build microservices architecture with 50 files",
            {"file_count": 50, "loc": 10000}
        )

        coordinator = next(r for r in plan.roles if r.role == "coordinator")
        assert coordinator.use_planning_mode is True

    def test_planning_mode_disabled_for_small_tasks(self):
        """Test planning mode disabled for small tasks"""
        plan = self.orchestrator.create_plan(
            "Fix bug in login function",
            {"file_count": 2, "loc": 100}
        )

        coordinator = next(r for r in plan.roles if r.role == "coordinator")
        assert coordinator.use_planning_mode is False

    def test_cost_estimation(self):
        """Test cost estimation is reasonable"""
        plan = self.orchestrator.create_plan(
            "Build web app",
            {"file_count": 20, "loc": 3000}
        )

        assert plan.estimated_cost_usd > 0
        assert plan.estimated_cost_usd < 100  # Should be reasonable

    def test_role_assignment_includes_reviewer(self):
        """Test reviewer assigned for code review needs"""
        plan = self.orchestrator.create_plan(
            "Implement critical payment processing system",
            {"file_count": 15, "loc": 2500}
        )

        # Should have reviewer for critical systems
        if plan.num_claudes >= 3:
            reviewer = next((r for r in plan.roles if r.role == "reviewer"), None)
            assert reviewer is not None

    def test_reasoning_includes_model_selection(self):
        """Test reasoning output includes model selection"""
        plan = self.orchestrator.create_plan(
            "Build complex system",
            {"file_count": 30, "loc": 5000}
        )

        assert "Model Selection:" in plan.reasoning
        assert plan.roles[0].model.value.upper() in plan.reasoning


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
