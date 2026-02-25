#!/usr/bin/env python3
"""
Think-Tank Feature Tests
Tests critique, debate, amendment, and alternative proposal capabilities
"""
import pytest
from datetime import datetime, timezone
from collaboration_enhanced import (
    EnhancedCollaborationHub,
    MemberRole,
    VoteType
)


@pytest.fixture
def hub():
    """Create hub with test room"""
    return EnhancedCollaborationHub()


@pytest.fixture
def room(hub):
    """Create room with 5 members"""
    room_id = hub.create_room("Think-Tank Test Room")
    room = hub.get_room(room_id)

    # Add members with different roles
    room.join("coordinator", MemberRole.COORDINATOR, vote_weight=2.0)
    room.join("reviewer", MemberRole.REVIEWER, vote_weight=1.5)
    room.join("coder", MemberRole.CODER)
    room.join("tester", MemberRole.TESTER)
    room.join("researcher", MemberRole.RESEARCHER)

    return room


class TestCritiqueSystem:
    """Test structured critique functionality"""

    def test_send_critique(self, room):
        """Agent critiques another's message"""
        # Coordinator sends message
        msg = room.send_message("coordinator", "We should use MongoDB for storage")

        # Reviewer critiques
        critique = room.send_critique(
            "reviewer",
            msg.id,
            "MongoDB doesn't support ACID transactions, which we need for financial data",
            severity="blocking"
        )

        assert critique.type == "critique"
        assert "CRITIQUE" in critique.text
        assert "blocking" in critique.text.lower()
        assert len(room.critiques) == 1
        assert room.critiques[0].severity == "blocking"
        assert room.critiques[0].target_message_id == msg.id
        assert room.critiques[0].from_client == "reviewer"

    def test_critique_severity_levels(self, room):
        """Test all 4 severity levels"""
        msg = room.send_message("coder", "Let's deploy on Friday afternoon")

        severities = ["blocking", "major", "minor", "suggestion"]
        for i, severity in enumerate(severities):
            critique = room.send_critique(
                "reviewer",
                msg.id,
                f"Test critique {i}",
                severity=severity
            )
            assert room.critiques[i].severity == severity

        assert len(room.critiques) == 4

    def test_critique_invalid_target(self, room):
        """Critiquing non-existent message should fail"""
        with pytest.raises(ValueError, match="not found"):
            room.send_critique(
                "reviewer",
                "invalid-message-id",
                "This should fail"
            )

    def test_critique_invalid_severity(self, room):
        """Invalid severity should fail"""
        msg = room.send_message("coder", "Test message")

        with pytest.raises(ValueError, match="Invalid severity"):
            room.send_critique(
                "reviewer",
                msg.id,
                "Test",
                severity="critical"  # Invalid
            )

    def test_get_critiques_for_message(self, room):
        """Get all critiques for a message"""
        msg = room.send_message("coordinator", "Use Python for ML")

        # Add 3 critiques
        room.send_critique("reviewer", msg.id, "Critique 1", "minor")
        room.send_critique("tester", msg.id, "Critique 2", "major")
        room.send_critique("coder", msg.id, "Critique 3", "suggestion")

        critiques = room.get_critiques_for_message(msg.id)
        assert len(critiques) == 3
        assert all(c.target_message_id == msg.id for c in critiques)

    def test_resolve_critique(self, room):
        """Mark critique as resolved"""
        msg = room.send_message("coordinator", "Use MongoDB")
        critique_msg = room.send_critique("reviewer", msg.id, "No ACID", "blocking")

        # Initially not resolved
        assert room.critiques[0].resolved == False

        # Resolve it
        room.resolve_critique(room.critiques[0].id)
        assert room.critiques[0].resolved == True


class TestCounterProposals:
    """Test alternative decision proposals"""

    def test_propose_alternative(self, room):
        """Agent proposes alternative to decision"""
        # Original decision
        original_id = room.propose_decision(
            "coordinator",
            "Use Python for ML pipeline",
            vote_type=VoteType.CONSENSUS
        )

        # Researcher proposes alternative
        alt_id = room.propose_alternative(
            "researcher",
            original_id,
            "Use Julia - fast as C++ with Python-like syntax"
        )

        # Verify alternative created
        assert alt_id != original_id
        alt_decision = next(d for d in room.decisions if d.id == alt_id)
        assert alt_decision.text == "Use Julia - fast as C++ with Python-like syntax"

        # Verify link to original
        original = next(d for d in room.decisions if d.id == original_id)
        assert alt_id in original.alternatives

    def test_multiple_alternatives(self, room):
        """Multiple agents propose alternatives"""
        original_id = room.propose_decision(
            "coordinator",
            "Use MongoDB for storage",
            vote_type=VoteType.SIMPLE_MAJORITY
        )

        # 3 alternatives
        alt1 = room.propose_alternative("reviewer", original_id, "Use PostgreSQL")
        alt2 = room.propose_alternative("coder", original_id, "Use MySQL")
        alt3 = room.propose_alternative("tester", original_id, "Use SQLite")

        original = next(d for d in room.decisions if d.id == original_id)
        assert len(original.alternatives) == 3
        assert all(alt_id in original.alternatives for alt_id in [alt1, alt2, alt3])

    def test_alternative_inherits_vote_type(self, room):
        """Alternative inherits vote type from original"""
        original_id = room.propose_decision(
            "coordinator",
            "Original decision",
            vote_type=VoteType.CONSENSUS
        )

        alt_id = room.propose_alternative(
            "reviewer",
            original_id,
            "Alternative"
        )

        alt_decision = next(d for d in room.decisions if d.id == alt_id)
        assert alt_decision.vote_type == VoteType.CONSENSUS

    def test_alternative_invalid_decision(self, room):
        """Proposing alternative to non-existent decision fails"""
        with pytest.raises(ValueError, match="not found"):
            room.propose_alternative(
                "reviewer",
                "invalid-decision-id",
                "Alternative"
            )


class TestStructuredDebate:
    """Test pro/con debate system"""

    def test_add_pro_argument(self, room):
        """Add pro argument to debate"""
        decision_id = room.propose_decision(
            "coordinator",
            "Use Python for ML",
            vote_type=VoteType.SIMPLE_MAJORITY
        )

        arg_id = room.add_debate_argument(
            "coder",
            decision_id,
            position="pro",
            argument_text="Python has best ML libraries (PyTorch, TensorFlow)"
        )

        assert len(room.debate_arguments) == 1
        arg = room.debate_arguments[0]
        assert arg.position == "pro"
        assert arg.decision_id == decision_id
        assert "PyTorch" in arg.argument_text

    def test_add_con_argument(self, room):
        """Add con argument to debate"""
        decision_id = room.propose_decision(
            "coordinator",
            "Use Python for ML"
        )

        arg_id = room.add_debate_argument(
            "tester",
            decision_id,
            position="con",
            argument_text="Python GIL limits parallelism"
        )

        assert room.debate_arguments[0].position == "con"
        assert "GIL" in room.debate_arguments[0].argument_text

    def test_debate_with_evidence(self, room):
        """Add argument with supporting evidence"""
        decision_id = room.propose_decision("coordinator", "Test decision")

        evidence = [
            "https://benchmark.com/python-vs-julia",
            "file-id-12345"
        ]

        arg_id = room.add_debate_argument(
            "researcher",
            decision_id,
            position="pro",
            argument_text="Julia is 10x faster",
            evidence=evidence
        )

        assert room.debate_arguments[0].supporting_evidence == evidence

    def test_debate_summary(self, room):
        """Get pro/con summary"""
        decision_id = room.propose_decision("coordinator", "Use Python")

        # Add 3 pro, 2 con arguments
        room.add_debate_argument("coder", decision_id, "pro", "Pro 1")
        room.add_debate_argument("reviewer", decision_id, "pro", "Pro 2")
        room.add_debate_argument("researcher", decision_id, "pro", "Pro 3")
        room.add_debate_argument("tester", decision_id, "con", "Con 1")
        room.add_debate_argument("coordinator", decision_id, "con", "Con 2")

        summary = room.get_debate_summary(decision_id)
        assert summary['total_pro'] == 3
        assert summary['total_con'] == 2
        assert len(summary['pro']) == 3
        assert len(summary['con']) == 2

    def test_debate_invalid_position(self, room):
        """Invalid position should fail"""
        decision_id = room.propose_decision("coordinator", "Test")

        with pytest.raises(ValueError, match="must be 'pro' or 'con'"):
            room.add_debate_argument(
                "coder",
                decision_id,
                position="neutral",  # Invalid
                argument_text="Test"
            )

    def test_debate_invalid_decision(self, room):
        """Debating non-existent decision fails"""
        with pytest.raises(ValueError, match="not found"):
            room.add_debate_argument(
                "coder",
                "invalid-decision-id",
                "pro",
                "Test"
            )


class TestAmendmentSystem:
    """Test decision amendment functionality"""

    def test_propose_amendment(self, room):
        """Propose amendment to decision"""
        decision_id = room.propose_decision(
            "coordinator",
            "Use Python for ML pipeline"
        )

        amend_id = room.propose_amendment(
            "reviewer",
            decision_id,
            "Use Python for training, C++ for inference"
        )

        decision = next(d for d in room.decisions if d.id == decision_id)
        assert len(decision.amendments) == 1
        assert decision.amendments[0]['text'] == "Use Python for training, C++ for inference"
        assert decision.amendments[0]['from'] == "reviewer"
        assert decision.amendments[0]['accepted'] == False

    def test_accept_amendment(self, room):
        """Accept amendment updates decision text"""
        decision_id = room.propose_decision(
            "coordinator",
            "Original text"
        )

        amend_id = room.propose_amendment(
            "reviewer",
            decision_id,
            "Amended text"
        )

        # Accept amendment
        room.accept_amendment(decision_id, amend_id)

        decision = next(d for d in room.decisions if d.id == decision_id)
        assert decision.text == "Amended text"
        assert decision.amendments[0]['accepted'] == True

    def test_multiple_amendments(self, room):
        """Multiple amendments can be proposed"""
        decision_id = room.propose_decision("coordinator", "Original")

        amend1 = room.propose_amendment("reviewer", decision_id, "Amendment 1")
        amend2 = room.propose_amendment("coder", decision_id, "Amendment 2")
        amend3 = room.propose_amendment("tester", decision_id, "Amendment 3")

        decision = next(d for d in room.decisions if d.id == decision_id)
        assert len(decision.amendments) == 3

    def test_amendment_invalid_decision(self, room):
        """Amending non-existent decision fails"""
        with pytest.raises(ValueError, match="not found"):
            room.propose_amendment(
                "reviewer",
                "invalid-decision-id",
                "Amendment"
            )

    def test_accept_nonexistent_amendment(self, room):
        """Accepting non-existent amendment fails"""
        decision_id = room.propose_decision("coordinator", "Test")

        with pytest.raises(ValueError, match="not found"):
            room.accept_amendment(decision_id, "invalid-amendment-id")


class TestFullThinkTankWorkflow:
    """Integration tests for complete think-tank workflow"""

    def test_full_debate_workflow(self, room):
        """
        Complete think-tank debate:
        1. Propose decision
        2. Reviewer critiques (blocking)
        3. Coordinator proposes amendment
        4. Coder adds pro argument
        5. Tester adds con argument
        6. Researcher proposes alternative
        7. Get debate summary
        8. Accept amendment
        9. Re-vote and approve
        """
        # 1. Propose decision
        decision_id = room.propose_decision(
            "coordinator",
            "Use Python for ML pipeline",
            vote_type=VoteType.CONSENSUS
        )

        # 2. Reviewer critiques (blocking)
        critique = room.send_critique(
            "reviewer",
            decision_id,
            "Python is too slow for real-time inference. Consider C++ or Rust.",
            severity="blocking"
        )
        assert room.critiques[0].severity == "blocking"

        # 3. Coordinator proposes amendment
        amendment_id = room.propose_amendment(
            "coordinator",
            decision_id,
            "Use Python for training, C++ for inference"
        )
        assert len(room.decisions[0].amendments) == 1

        # 4. Coder adds pro argument
        pro_arg = room.add_debate_argument(
            "coder",
            decision_id,
            position="pro",
            argument_text="Python has best ML libraries (PyTorch, TensorFlow)"
        )

        # 5. Tester adds con argument
        con_arg = room.add_debate_argument(
            "tester",
            decision_id,
            position="con",
            argument_text="Python GIL limits parallelism"
        )

        # 6. Researcher proposes alternative
        alt_id = room.propose_alternative(
            "researcher",
            decision_id,
            "Use Julia - fast as C++ with Python-like syntax"
        )

        # 7. Get debate summary
        debate_summary = room.get_debate_summary(decision_id)
        assert debate_summary['total_pro'] == 1
        assert debate_summary['total_con'] == 1

        # 8. Accept amendment
        room.accept_amendment(decision_id, amendment_id)
        decision = room.decisions[0]
        assert decision.text == "Use Python for training, C++ for inference"

        # 9. Re-vote and approve (consensus requires all 5 votes)
        room.vote(decision_id, "coordinator", approve=True)
        room.vote(decision_id, "reviewer", approve=True)
        room.vote(decision_id, "coder", approve=True)
        room.vote(decision_id, "tester", approve=True)
        room.vote(decision_id, "researcher", approve=True)

        assert decision.approved == True

    def test_iterative_consensus_with_amendments(self, room):
        """
        Test iterative consensus building:
        - Proposal → critique → amend → vote → repeat until consensus
        """
        decision_id = room.propose_decision(
            "coordinator",
            "Deploy on Friday at 5pm",
            vote_type=VoteType.SIMPLE_MAJORITY
        )

        # Critique 1: Bad timing
        room.send_critique(
            "reviewer",
            decision_id,
            "Friday evening is risky - no support team on weekend",
            severity="major"
        )

        # Amendment 1: Change to Thursday
        amend1 = room.propose_amendment(
            "coordinator",
            decision_id,
            "Deploy on Thursday at 2pm"
        )
        room.accept_amendment(decision_id, amend1)

        # Critique 2: Still during work hours
        room.send_critique(
            "tester",
            decision_id,
            "2pm is during peak usage - consider off-hours",
            severity="minor"
        )

        # Amendment 2: Early morning
        amend2 = room.propose_amendment(
            "coordinator",
            decision_id,
            "Deploy on Thursday at 6am"
        )
        room.accept_amendment(decision_id, amend2)

        # Now vote
        room.vote(decision_id, "coordinator", approve=True)
        room.vote(decision_id, "reviewer", approve=True)
        room.vote(decision_id, "tester", approve=True)

        decision = room.decisions[0]
        assert decision.text == "Deploy on Thursday at 6am"
        assert decision.approved == True
        assert len(decision.amendments) == 2

    def test_competing_alternatives_vote(self, room):
        """
        Multiple alternatives compete:
        1. Original proposal
        2. Three alternatives proposed
        3. Each gets debated
        4. Agents vote on best option
        """
        # Original
        original_id = room.propose_decision(
            "coordinator",
            "Use MongoDB",
            vote_type=VoteType.WEIGHTED
        )

        # Alternatives
        alt1 = room.propose_alternative("reviewer", original_id, "Use PostgreSQL")
        alt2 = room.propose_alternative("coder", original_id, "Use MySQL")
        alt3 = room.propose_alternative("researcher", original_id, "Use SQLite")

        # Debate original
        room.add_debate_argument("coder", original_id, "pro", "Scales horizontally")
        room.add_debate_argument("tester", original_id, "con", "No ACID")

        # Debate alt1 (PostgreSQL)
        room.add_debate_argument("reviewer", alt1, "pro", "Full ACID compliance")
        room.add_debate_argument("coder", alt1, "pro", "Better tooling")

        # Vote for PostgreSQL (coordinator=2.0, reviewer=1.5, coder=1.0 = 4.5 weight)
        room.vote(alt1, "coordinator", approve=True)
        room.vote(alt1, "reviewer", approve=True)
        room.vote(alt1, "coder", approve=True)

        alt1_decision = next(d for d in room.decisions if d.id == alt1)
        assert alt1_decision.approved == True
        assert alt1_decision.total_weight == 4.5


class TestThinkTankEdgeCases:
    """Edge cases and error handling"""

    def test_critique_own_message(self, room):
        """Agent can critique their own message (self-correction)"""
        msg = room.send_message("coordinator", "Let's use MongoDB")

        # Self-critique should work
        critique = room.send_critique(
            "coordinator",
            msg.id,
            "On second thought, we need ACID transactions",
            severity="major"
        )

        assert critique.from_client == "coordinator"
        assert room.critiques[0].from_client == "coordinator"

    def test_empty_debate(self, room):
        """Debate summary with no arguments"""
        decision_id = room.propose_decision("coordinator", "Test")

        summary = room.get_debate_summary(decision_id)
        assert summary['total_pro'] == 0
        assert summary['total_con'] == 0
        assert len(summary['pro']) == 0
        assert len(summary['con']) == 0

    def test_amendment_without_acceptance(self, room):
        """Unaccepted amendments don't change decision text"""
        decision_id = room.propose_decision("coordinator", "Original")

        amend1 = room.propose_amendment("reviewer", decision_id, "Amendment 1")
        amend2 = room.propose_amendment("coder", decision_id, "Amendment 2")

        decision = room.decisions[0]
        assert decision.text == "Original"  # Unchanged
        assert len(decision.amendments) == 2
        assert all(not a['accepted'] for a in decision.amendments)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
