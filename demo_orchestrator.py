#!/usr/bin/env python3
"""
ML Orchestrator Demo - Bridge Utilization Example

Shows:
1. Orchestrator analyzes task
2. Decides to use bridge (vs agents)
3. Creates collaboration room
4. Spawns multiple Claudes
5. Coordinates work via bridge

This is the ANSWER to: "how does this bridge work with skills, cowork, agents, mcp?"
The orchestrator decides WHEN to use bridge vs agents, HOW MANY Claudes, WHAT ROLES.
"""
import time
from datetime import datetime, timezone

from orchestrator_ml import MLOrchestrator, CollabStrategy
from collaboration_enhanced import EnhancedCollaborationRoom, MemberRole, VoteType


def print_banner(text):
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80 + "\n")


def simulate_task(
    orchestrator: MLOrchestrator, task_desc: str, code_context: dict = None
):
    """
    Simulate automatic orchestration for a task

    This shows the complete flow:
    1. Analyze task
    2. Decide strategy (bridge vs agents)
    3. If bridge: create room and coordinate
    """
    print_banner(f"TASK: {task_desc[:60]}...")

    # STEP 1: Analyze task
    print("📊 STEP 1: Analyzing Task...")
    print(f"   Task: {task_desc}")
    if code_context:
        print(
            f"   Context: {code_context.get('file_count', 0)} files, {code_context.get('loc', 0)} LOC"
        )
    print()

    time.sleep(0.5)

    # STEP 2: Create plan
    print("🤖 STEP 2: ML Orchestrator Creating Plan...")
    plan = orchestrator.create_plan(task_desc, code_context)
    print()

    time.sleep(0.5)

    # STEP 3: Show decision
    print("📋 STEP 3: Plan Generated")
    print(f"   Strategy: {plan.strategy.value.upper()}")
    print(f"   Team: {plan.num_claudes} Claudes, {plan.num_agents} agents")
    print(f"   Duration: ~{plan.estimated_duration_hours:.1f} hours")
    print(f"   Cost: ${plan.estimated_cost_usd:.2f}")
    print()

    # Show model selection and planning mode
    if plan.roles:
        print("   🤖 Model Selection & Planning Mode:")
        for role in plan.roles:
            planning_marker = " 📋" if role.use_planning_mode else ""
            print(
                f"     • {role.client_id}: {role.model.value.upper()}{planning_marker}"
            )
        print()

    print("   Reasoning:")
    for line in plan.reasoning.split("\n"):
        print(f"     {line}")
    print()

    time.sleep(1)

    # STEP 4: Execute (simulate if bridge)
    if plan.strategy in [
        CollabStrategy.BRIDGE_SMALL,
        CollabStrategy.BRIDGE_MEDIUM,
        CollabStrategy.BRIDGE_LARGE,
    ]:
        print("🌉 STEP 4: BRIDGE SELECTED - Creating Collaboration Room")
        print()

        # Create room
        room_id = f"room-{int(time.time())}"
        room = EnhancedCollaborationRoom(
            room_id, plan.room_topic, persistence_enabled=False
        )
        print(f"   ✅ Room created: {room_id}")
        print(f"   Topic: {plan.room_topic[:60]}")
        print()

        time.sleep(0.5)

        # Add members
        print("   👥 Adding team members:")
        for role_assignment in plan.roles:
            role_enum = MemberRole[role_assignment.role.upper()]
            room.join(
                role_assignment.client_id,
                role=role_enum,
                vote_weight=role_assignment.vote_weight,
            )
            print(
                f"      ✅ {role_assignment.client_id} ({role_assignment.role}, vote weight: {role_assignment.vote_weight}x)"
            )
            time.sleep(0.2)
        print()

        time.sleep(0.5)

        # Create channels
        channel_ids = {}
        if plan.channels:
            print("   📺 Creating channels:")
            for channel_config in plan.channels[1:]:  # Skip 'main' (auto-created)
                ch_id = room.create_channel(
                    channel_config["name"], channel_config["topic"], "coordinator"
                )
                channel_ids[channel_config["name"]] = ch_id
                print(f"      ✅ #{channel_config['name']}: {channel_config['topic']}")
                time.sleep(0.2)
            print()

        time.sleep(0.5)

        # Simulate coordination
        print("   💬 Simulating Collaboration:")
        print()

        # Coordinator proposes architecture decision
        print("      [coordinator] Proposing architecture decision...")
        dec_id = room.propose_decision(
            "claude-coordinator",
            "Use microservices architecture with Docker",
            vote_type=VoteType.SIMPLE_MAJORITY,
        )
        time.sleep(0.3)

        # Team votes
        for role in plan.roles[1:]:  # Skip coordinator
            approve = True  # Simple demo - everyone approves
            room.vote(dec_id, role.client_id, approve=approve)
            vote_text = "✅ Approve" if approve else "❌ Reject"
            print(f"      [{role.client_id}] {vote_text}")
            time.sleep(0.2)

        # Check decision
        decision = [d for d in room.decisions if d.id == dec_id][0]
        if decision.approved:
            print("      🎉 Decision APPROVED!")
        print()

        time.sleep(0.5)

        # Simulate messages
        print("      [coordinator] Assigning tasks...")
        room.send_message(
            "claude-coordinator", "Breaking down work into components", channel="main"
        )
        time.sleep(0.3)

        if plan.num_claudes >= 3:
            print("      [claude-coder-1] Working on auth service...")
            code_channel = channel_ids.get("code", "main")
            room.send_message(
                "claude-coder-1",
                "Implementing authentication service",
                channel=code_channel,
            )
            time.sleep(0.3)

        # Check if reviewer exists
        reviewer_exists = any(r.role == "reviewer" for r in plan.roles)
        if plan.num_claudes >= 4 and reviewer_exists:
            print("      [claude-reviewer] Reviewing architecture...")
            review_channel = channel_ids.get("review", "main")
            room.send_message(
                "claude-reviewer",
                "Architecture looks good, proceeding",
                channel=review_channel,
            )
            time.sleep(0.3)

        print()

        # Show summary
        summary = room.get_summary()
        print("   📊 Room Summary:")
        print(f"      Members: {summary['total_members']}")
        print(f"      Messages: {summary['total_messages']}")
        print(
            f"      Decisions: {summary['total_decisions']} ({summary['approved_decisions']} approved)"
        )
        print(f"      Channels: {summary['channels']}")
        print()

        time.sleep(0.5)

        print("   ✅ Bridge collaboration complete!")
        print()

    elif plan.strategy == CollabStrategy.AGENTS:
        print("🤖 STEP 4: AGENTS SELECTED - Would Spawn Subagents")
        print()
        print(
            f"   Would execute: Task(subagent_type='general-purpose', ...) x {plan.num_agents}"
        )
        print("   Agents share context window, cheaper than bridge")
        print()

    else:  # SINGLE_CLAUDE
        print("👤 STEP 4: SINGLE CLAUDE - No Coordination Needed")
        print()
        print("   Task simple enough for one Claude")
        print("   No collaboration required")
        print()

    print("-" * 80)
    print()
    time.sleep(1)


def main():
    print_banner("🤖 ML ORCHESTRATOR - BRIDGE UTILIZATION DEMO")
    print("This demonstrates HOW and WHEN the bridge is used")
    print("The orchestrator automatically decides: Bridge vs Agents vs Single Claude")
    print()

    time.sleep(1)

    orchestrator = MLOrchestrator()

    # ==================================================================
    # TEST 1: Simple task → Single Claude
    # ==================================================================
    simulate_task(
        orchestrator,
        "Fix typo in README.md - change 'colaboration' to 'collaboration'",
        {"file_count": 1, "loc": 50},
    )

    # ==================================================================
    # TEST 2: Medium task → Agents
    # ==================================================================
    simulate_task(
        orchestrator,
        "Add user authentication with login, signup, and password reset",
        {"file_count": 8, "loc": 1200},
    )

    # ==================================================================
    # TEST 3: Large task → Bridge (Small Team)
    # ==================================================================
    simulate_task(
        orchestrator,
        """Build a REST API for a task management system with:
- User authentication (JWT)
- CRUD operations for tasks
- Real-time notifications (WebSocket)
- PostgreSQL database
- Docker deployment
- Complete test suite""",
        {"file_count": 25, "loc": 4000},
    )

    # ==================================================================
    # TEST 4: Very Large task → Bridge (Medium Team)
    # ==================================================================
    simulate_task(
        orchestrator,
        """Build a trading bot platform with:
- 5 different trading strategies (momentum, mean reversion, arbitrage, ML-based, sentiment)
- Backtesting engine with historical data support
- Real-time dashboard with live charts and metrics
- Multi-broker support (Alpaca, OANDA, Kalshi)
- Risk management system with position sizing
- SQLite database for trade history
- Flask dashboard on port 5000
- Paper trading mode
- Comprehensive logging and error handling
- Unit tests for all strategies""",
        {"file_count": 45, "loc": 8000},
    )

    # ==================================================================
    # SUMMARY
    # ==================================================================
    print_banner("✅ DEMO COMPLETE - KEY INSIGHTS")

    print("🎯 WHEN TO USE BRIDGE (vs Agents):")
    print("   1. Task has 15+ files")
    print("   2. Estimated context > 100K tokens")
    print("   3. Duration > 2 hours")
    print("   4. Needs voting/consensus")
    print("   5. Multiple independent components")
    print()

    print("👥 HOW MANY CLAUDES:")
    print("   - Formula: files ÷ 10 (files per Claude)")
    print("   - Adjusted by parallelization score")
    print("   - Min: 2, Max: 8")
    print("   - Small: 2-3, Medium: 4-5, Large: 6-8")
    print()

    print("🎭 ROLE ASSIGNMENT:")
    print("   - Always: Coordinator (2.0x vote weight)")
    print("   - If needs review: Reviewer (1.5x vote weight, veto power)")
    print("   - If needs testing: Tester (1.0x)")
    print("   - Remaining: Coders (1.0x each)")
    print()

    print("💰 COST OPTIMIZATION:")
    print("   - Single Claude: $1-2/hour")
    print("   - Agents: $0.60/hour (shared context)")
    print("   - Bridge: $2-16/hour (multiple instances)")
    print("   - Orchestrator chooses cheapest viable option")
    print()

    print("🚀 RESULT: Intelligent auto-scaling collaboration!")
    print("   The bridge is used AUTOMATICALLY when optimal.")
    print("   No manual decision needed from user.")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted")
    except Exception as e:
        print(f"\n\n❌ Demo error: {e}")
        import traceback

        traceback.print_exc()
