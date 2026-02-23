#!/usr/bin/env python3
"""
Five-Agent Debugging with Think-Tank Features
Simulates 5 Claude agents debugging a trading bot using critique, debate, and amendments
"""
import pytest
from collaboration_enhanced import (
    EnhancedCollaborationHub,
    MemberRole,
    VoteType
)


@pytest.fixture
def debugging_room():
    """Setup debugging room with 5 specialized agents"""
    hub = EnhancedCollaborationHub()
    room_id = hub.create_room("Trading Bot Bug Investigation")
    room = hub.get_room(room_id)

    # Join with specialized roles
    room.join("coordinator", MemberRole.COORDINATOR, vote_weight=2.0)
    room.join("timing-specialist", MemberRole.RESEARCHER, vote_weight=1.5)
    room.join("code-reviewer", MemberRole.REVIEWER, vote_weight=1.5)
    room.join("log-analyzer", MemberRole.RESEARCHER)
    room.join("database-expert", MemberRole.CODER)

    return room


class TestBasicDebugging:
    """Basic debugging workflow without think-tank features"""

    def test_five_agents_share_findings(self, debugging_room):
        """5 agents share their analysis"""
        room = debugging_room

        # Each agent shares findings
        room.send_message("coordinator", "🐛 Bug: Trades executing at wrong times")
        room.send_message("timing-specialist", "Analyzed logs: timestamps show UTC but trades execute in local time")
        room.send_message("code-reviewer", "Found issue in scheduler.py line 847 - uses datetime.now() instead of datetime.utcnow()")
        room.send_message("log-analyzer", "Log analysis confirms: 7-hour offset between logged time and actual execution")
        room.send_message("database-expert", "Database timestamps are correct (UTC), issue is in scheduler")

        # Coordinator proposes fix
        fix_id = room.propose_decision(
            "coordinator",
            "Change line 847 from datetime.now() to datetime.utcnow()"
        )

        # All vote
        room.vote(fix_id, "coordinator", approve=True)
        room.vote(fix_id, "timing-specialist", approve=True)
        room.vote(fix_id, "code-reviewer", approve=True)
        room.vote(fix_id, "log-analyzer", approve=True)
        room.vote(fix_id, "database-expert", approve=True)

        decision = room.decisions[0]
        assert decision.approved == True


class TestDebugWithCritiques:
    """Debugging with structured critiques"""

    def test_critique_reveals_deeper_issue(self, debugging_room):
        """
        Critique uncovers root cause:
        1. Initial diagnosis is wrong
        2. Critique points to real issue
        3. Amendment fixes correct problem
        """
        room = debugging_room

        # Initial (wrong) diagnosis
        decision_id = room.propose_decision(
            "coordinator",
            "Bug is in timezone parsing - fix by adding pytz library"
        )

        # Timing specialist critiques (blocking)
        room.send_critique(
            "timing-specialist",
            decision_id,
            "Not a parsing issue - it's UTC conversion. Line 847 uses local time instead of UTC. "
            "Adding pytz won't fix this.",
            severity="blocking"
        )

        # Code reviewer adds supporting critique
        room.send_critique(
            "code-reviewer",
            decision_id,
            "Confirmed: datetime.now() at line 847 should be datetime.utcnow(). "
            "Also found DST handling bug at line 1023.",
            severity="major"
        )

        # Coordinator proposes amendment based on critiques
        amendment_id = room.propose_amendment(
            "coordinator",
            decision_id,
            "Fix UTC conversion at line 847 AND DST handling at line 1023"
        )

        # Accept amendment
        room.accept_amendment(decision_id, amendment_id)

        decision = room.decisions[0]
        assert "line 847" in decision.text
        assert "line 1023" in decision.text
        assert decision.amendments[0]['accepted'] == True

        # Verify critiques were addressed
        critiques = room.get_critiques_for_message(decision_id)
        assert len(critiques) == 2
        assert critiques[0].severity == "blocking"


class TestDebugWithDebate:
    """Debugging with pro/con debate"""

    def test_debate_on_fix_approach(self, debugging_room):
        """
        Debate best fix approach:
        - Pro: Quick fix (change one line)
        - Con: Comprehensive refactor (fix all timezone issues)
        """
        room = debugging_room

        decision_id = room.propose_decision(
            "coordinator",
            "Quick fix: Change line 847 to use UTC",
            vote_type=VoteType.SIMPLE_MAJORITY
        )

        # PRO arguments (quick fix)
        room.add_debate_argument(
            "coordinator",
            decision_id,
            "pro",
            "Immediate fix - stops bleeding. Can refactor later.",
            evidence=["Low risk: 1 line change", "Can deploy in 5 minutes"]
        )

        room.add_debate_argument(
            "timing-specialist",
            decision_id,
            "pro",
            "Quick fix targets the exact bug causing trading losses"
        )

        # CON arguments (comprehensive refactor)
        room.add_debate_argument(
            "code-reviewer",
            decision_id,
            "con",
            "Found 47 other datetime.now() calls that should be UTC. "
            "Quick fix leaves 46 time bombs.",
            evidence=["grep shows 47 occurrences in codebase"]
        )

        room.add_debate_argument(
            "database-expert",
            decision_id,
            "con",
            "DST transitions will break again in 2 weeks. Need comprehensive fix."
        )

        # Get debate summary
        debate = room.get_debate_summary(decision_id)
        assert debate['total_pro'] == 2
        assert debate['total_con'] == 2

        # Coordinator proposes compromise
        amendment_id = room.propose_amendment(
            "coordinator",
            decision_id,
            "IMMEDIATE: Fix line 847. TOMORROW: Refactor all 47 datetime calls. Add tests for DST."
        )

        room.accept_amendment(decision_id, amendment_id)

        # Vote on compromise
        room.vote(decision_id, "coordinator", approve=True)
        room.vote(decision_id, "timing-specialist", approve=True)
        room.vote(decision_id, "code-reviewer", approve=True)

        decision = room.decisions[0]
        assert decision.approved == True
        assert "IMMEDIATE" in decision.text
        assert "TOMORROW" in decision.text


class TestDebugWithAlternatives:
    """Debugging with competing fix proposals"""

    def test_three_competing_fixes(self, debugging_room):
        """
        3 agents propose different fixes:
        1. Quick patch
        2. Comprehensive refactor
        3. Library replacement
        """
        room = debugging_room

        # Original proposal (quick patch)
        original_id = room.propose_decision(
            "coordinator",
            "Fix: Change line 847 to datetime.utcnow()",
            vote_type=VoteType.WEIGHTED
        )

        # Alternative 1: Comprehensive refactor
        alt1 = room.propose_alternative(
            "code-reviewer",
            original_id,
            "Fix: Refactor entire datetime handling to use timezone-aware objects (pytz)"
        )

        # Alternative 2: Library replacement
        alt2 = room.propose_alternative(
            "database-expert",
            original_id,
            "Fix: Replace all datetime with pendulum library (handles DST automatically)"
        )

        # Debate each approach
        # Original: PRO
        room.add_debate_argument(
            "coordinator",
            original_id,
            "pro",
            "Fastest fix - 5 minutes"
        )

        # Original: CON
        room.add_debate_argument(
            "code-reviewer",
            original_id,
            "con",
            "Leaves 46 other bugs"
        )

        # Alt1 (pytz): PRO
        room.add_debate_argument(
            "timing-specialist",
            alt1,
            "pro",
            "Comprehensive - fixes all timezone issues forever"
        )

        # Alt1: CON
        room.add_debate_argument(
            "log-analyzer",
            alt1,
            "con",
            "3-day refactor effort, high risk of introducing new bugs"
        )

        # Alt2 (pendulum): PRO
        room.add_debate_argument(
            "database-expert",
            alt2,
            "pro",
            "Pendulum handles DST automatically - future-proof"
        )

        # Alt2: CON
        room.add_debate_argument(
            "coordinator",
            alt2,
            "con",
            "New dependency - needs security audit and team training"
        )

        # Vote for Alt1 (comprehensive refactor)
        # coordinator=2.0, code-reviewer=1.5, timing-specialist=1.5
        room.vote(alt1, "coordinator", approve=True)
        room.vote(alt1, "code-reviewer", approve=True)
        room.vote(alt1, "timing-specialist", approve=True)

        alt1_decision = next(d for d in room.decisions if d.id == alt1)
        assert alt1_decision.approved == True
        assert "pytz" in alt1_decision.text

        # Verify all 3 options were debated
        original = next(d for d in room.decisions if d.id == original_id)
        assert len(original.alternatives) == 2


class TestRealWorldScenario:
    """Complex real-world debugging scenario"""

    def test_complete_bug_investigation(self, debugging_room):
        """
        Complete investigation workflow:
        1. Bug reported with symptoms
        2. Agents investigate and share findings
        3. Multiple hypotheses proposed
        4. Critiques narrow down to root cause
        5. Debate on fix approach
        6. Amendments refine solution
        7. Consensus on final fix
        """
        room = debugging_room

        # 1. Bug report
        room.send_message(
            "coordinator",
            "🚨 CRITICAL BUG: Trading bot bought AAPL at 4am EST instead of 10am EST. Lost $2,400."
        )

        # 2. Agents investigate
        room.send_message(
            "log-analyzer",
            "Log shows: order_time=2024-02-23T09:00:00 (UTC) but NYSE opens at 14:30 UTC. 6hr difference."
        )

        room.send_message(
            "timing-specialist",
            "Hypothesis: Scheduler uses local time (MST -7hr) but NYSE is EST (-5hr). Off by 2hr."
        )

        room.send_message(
            "code-reviewer",
            "Found in scheduler.py line 847: datetime.now() + market_hours[symbol]. "
            "No timezone info!"
        )

        room.send_message(
            "database-expert",
            "Database shows all timestamps in UTC. Issue is in scheduler, not DB."
        )

        # 3. Initial hypothesis (WRONG)
        hypothesis_id = room.propose_decision(
            "coordinator",
            "Bug is timezone parsing in scheduler - fix by converting to market timezone"
        )

        # 4. Critiques reveal root cause
        room.send_critique(
            "timing-specialist",
            hypothesis_id,
            "Not a parsing issue. Root cause: datetime.now() is timezone-naive. "
            "When comparing to market hours (UTC), Python assumes same timezone. "
            "Fix: Use timezone-aware datetime objects throughout.",
            severity="blocking"
        )

        room.send_critique(
            "code-reviewer",
            hypothesis_id,
            "Also found: DST transitions on March 10 will break again. "
            "Need timezone-aware objects, not just UTC conversion.",
            severity="major"
        )

        # 5. Debate on fix scope
        # Amendment based on critiques
        amendment1 = room.propose_amendment(
            "coordinator",
            hypothesis_id,
            "Fix: Make all datetime objects timezone-aware using pytz"
        )

        room.accept_amendment(hypothesis_id, amendment1)

        # Debate ensues
        room.add_debate_argument(
            "timing-specialist",
            hypothesis_id,
            "pro",
            "Timezone-aware objects prevent this entire class of bugs"
        )

        room.add_debate_argument(
            "log-analyzer",
            hypothesis_id,
            "con",
            "Changing 47 datetime calls is risky - could introduce new bugs"
        )

        # Alternative proposed
        alt_id = room.propose_alternative(
            "database-expert",
            hypothesis_id,
            "PHASE 1: Fix line 847 only (blocks immediate bleeding). "
            "PHASE 2: Comprehensive refactor next week with full test coverage."
        )

        # Debate alternative
        room.add_debate_argument(
            "coordinator",
            alt_id,
            "pro",
            "2-phase approach: immediate fix + planned refactor. Best of both."
        )

        room.add_debate_argument(
            "code-reviewer",
            alt_id,
            "pro",
            "Gives time to write comprehensive tests before refactor"
        )

        # Vote on alternative (weighted: need >50% of 7.0 total = >3.5)
        # coordinator=2.0, timing=1.5, code-reviewer=1.5, db=1.0 = 6.0
        room.vote(alt_id, "coordinator", approve=True)
        room.vote(alt_id, "timing-specialist", approve=True)
        room.vote(alt_id, "code-reviewer", approve=True)
        room.vote(alt_id, "database-expert", approve=True)

        alt_decision = next(d for d in room.decisions if d.id == alt_id)
        assert alt_decision.approved == True
        assert "PHASE 1" in alt_decision.text
        assert "PHASE 2" in alt_decision.text

        # Verify investigation used all think-tank features
        assert len(room.critiques) >= 2  # Blocking + major
        assert len(room.debate_arguments) >= 4  # Pro/con for both decisions
        assert len(room.decisions[0].amendments) >= 1  # At least one amendment
        assert len(room.decisions[0].alternatives) >= 1  # Alternative proposed


class TestConflictResolution:
    """Test resolving disagreements between agents"""

    def test_veto_then_amendment_resolves(self, debugging_room):
        """
        Agent vetoes decision, coordinator amends to address concern
        """
        room = debugging_room

        decision_id = room.propose_decision(
            "coordinator",
            "Deploy hotfix immediately to production"
        )

        # Code reviewer vetoes (no tests)
        room.vote(decision_id, "code-reviewer", veto=True)

        decision = room.decisions[0]
        assert decision.vetoed == True

        # Critique explains veto
        room.send_critique(
            "code-reviewer",
            decision_id,
            "Deploying without tests risks making bug worse. Need smoke tests at minimum.",
            severity="blocking"
        )

        # Coordinator proposes amendment
        amendment_id = room.propose_amendment(
            "coordinator",
            decision_id,
            "Deploy hotfix to staging, run smoke tests, THEN production"
        )

        room.accept_amendment(decision_id, amendment_id)

        # Re-propose (original is vetoed, create new decision)
        new_decision_id = room.propose_decision(
            "coordinator",
            decision.text,  # Uses amended text
            vote_type=VoteType.CONSENSUS
        )

        # Now all vote (including original vetoer)
        room.vote(new_decision_id, "coordinator", approve=True)
        room.vote(new_decision_id, "timing-specialist", approve=True)
        room.vote(new_decision_id, "code-reviewer", approve=True)
        room.vote(new_decision_id, "log-analyzer", approve=True)
        room.vote(new_decision_id, "database-expert", approve=True)

        new_decision = room.decisions[-1]
        assert new_decision.approved == True
        assert "staging" in new_decision.text.lower()


class TestPerformanceMetrics:
    """Verify think-tank improves debugging efficiency"""

    def test_critique_prevents_wrong_fix(self, debugging_room):
        """
        Without critique: wrong fix deployed
        With critique: correct fix deployed
        """
        room = debugging_room

        # Wrong diagnosis
        wrong_fix = room.propose_decision(
            "coordinator",
            "Bug is in database - add index on timestamp column"
        )

        # Critique catches mistake
        room.send_critique(
            "database-expert",
            wrong_fix,
            "Database performance is fine. Real bug is in scheduler.py line 847 - uses local time.",
            severity="blocking"
        )

        # Amendment corrects
        amendment = room.propose_amendment(
            "coordinator",
            wrong_fix,
            "Bug is in scheduler.py line 847 - change datetime.now() to datetime.utcnow()"
        )

        room.accept_amendment(wrong_fix, amendment)

        decision = room.decisions[0]
        assert "scheduler.py" in decision.text
        assert "database" not in decision.text  # Original wrong diagnosis removed


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
