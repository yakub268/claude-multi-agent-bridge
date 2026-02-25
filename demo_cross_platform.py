#!/usr/bin/env python3
"""
Cross-Platform Messaging Demo
Demonstrates communication between Claude Code, Browser, Desktop, and VS Code
"""
import asyncio
import websockets
import json
import time
from datetime import datetime
from test_live_thinktank import ThinkTankClient


class PlatformSimulator:
    """Simulates different Claude platforms"""

    PLATFORMS = {
        'code': {
            'name': 'Claude Code (CLI)',
            'emoji': '💻',
            'color': '\033[94m',  # Blue
        },
        'browser': {
            'name': 'Browser Claude (claude.ai)',
            'emoji': '🌐',
            'color': '\033[92m',  # Green
        },
        'desktop': {
            'name': 'Claude Desktop App',
            'emoji': '🖥️',
            'color': '\033[93m',  # Yellow
        },
        'vscode': {
            'name': 'VS Code (via MCP)',
            'emoji': '📝',
            'color': '\033[95m',  # Magenta
        }
    }

    RESET = '\033[0m'

    @classmethod
    def format_message(cls, platform: str, message: str):
        """Format message with platform color and emoji"""
        info = cls.PLATFORMS.get(platform, {'emoji': '❓', 'color': '\033[97m', 'name': platform})
        return f"{info['color']}{info['emoji']} {info['name']}{cls.RESET}: {message}"


async def demo_basic_messaging():
    """Demo 1: Basic cross-platform messaging"""
    print("\n" + "="*80)
    print("📡 DEMO 1: BASIC CROSS-PLATFORM MESSAGING")
    print("="*80 + "\n")

    # Create clients for different platforms
    code = ThinkTankClient("claude-code", "coordinator")
    browser = ThinkTankClient("browser-claude", "researcher")
    desktop = ThinkTankClient("claude-desktop", "coder")
    vscode = ThinkTankClient("vscode-claude", "reviewer")

    try:
        # Connect all platforms
        print("🔌 Connecting platforms to message bus...")
        await asyncio.gather(
            code.connect(),
            browser.connect(),
            desktop.connect(),
            vscode.connect()
        )
        print(PlatformSimulator.format_message('code', "Connected ✅"))
        print(PlatformSimulator.format_message('browser', "Connected ✅"))
        print(PlatformSimulator.format_message('desktop', "Connected ✅"))
        print(PlatformSimulator.format_message('vscode', "Connected ✅"))
        await asyncio.sleep(0.5)

        # Create shared room
        print("\n📍 Creating collaboration room...")
        room_id = await code.create_room("Cross-Platform Demo")
        await asyncio.gather(
            browser.join_room(room_id),
            desktop.join_room(room_id),
            vscode.join_room(room_id)
        )
        await asyncio.sleep(0.5)

        # Cross-platform conversation
        print("\n💬 CROSS-PLATFORM CONVERSATION:\n")

        # Code → All
        print(PlatformSimulator.format_message('code',
            "Hey team! I need help debugging a trading bot issue. Anyone have ideas?"))
        await code.send_message("Hey team! I need help debugging a trading bot issue. Anyone have ideas?")
        await asyncio.sleep(0.3)

        # Browser → All (has web search capability)
        print(PlatformSimulator.format_message('browser',
            "I can search the web for recent trading bot issues. Let me look..."))
        await browser.send_message("I can search the web for recent trading bot issues. Let me look...")
        await asyncio.sleep(0.3)

        # Desktop → All
        print(PlatformSimulator.format_message('desktop',
            "I can check the logs. What's the error message?"))
        await desktop.send_message("I can check the logs. What's the error message?")
        await asyncio.sleep(0.3)

        # VS Code → All
        print(PlatformSimulator.format_message('vscode',
            "I'm looking at the code in my editor. Might be a timezone issue?"))
        await vscode.send_message("I'm looking at the code in my editor. Might be a timezone issue?")
        await asyncio.sleep(0.5)

        print("\n✅ Messages delivered across all platforms in real-time!\n")

    finally:
        await asyncio.gather(
            code.close(),
            browser.close(),
            desktop.close(),
            vscode.close(),
            return_exceptions=True
        )


async def demo_think_tank_cross_platform():
    """Demo 2: Think-tank features across platforms"""
    print("\n" + "="*80)
    print("🧠 DEMO 2: THINK-TANK ACROSS PLATFORMS")
    print("="*80 + "\n")

    code = ThinkTankClient("claude-code", "coordinator")
    browser = ThinkTankClient("browser-claude", "researcher")
    desktop = ThinkTankClient("claude-desktop", "coder")
    vscode = ThinkTankClient("vscode-claude", "reviewer")

    try:
        # Connect
        print("🔌 Connecting platforms...")
        await asyncio.gather(
            code.connect(), browser.connect(),
            desktop.connect(), vscode.connect()
        )
        print("✅ All platforms connected\n")
        await asyncio.sleep(0.3)

        # Create room
        room_id = await code.create_room("Architecture Decision")
        await asyncio.gather(
            browser.join_room(room_id),
            desktop.join_room(room_id),
            vscode.join_room(room_id)
        )
        await asyncio.sleep(0.3)

        # Propose decision (from CLI)
        print("🎯 PHASE 1: Proposal (from CLI)\n")
        print(PlatformSimulator.format_message('code',
            "DECISION: Use REST API for microservices communication"))
        decision = await code.propose_decision(
            "Use REST API for microservices communication",
            vote_type="consensus"
        )
        decision_id = decision['decision_id']
        await asyncio.sleep(0.5)

        # Critique (from Browser)
        print("\n🚫 PHASE 2: Critique (from Browser)\n")
        print(PlatformSimulator.format_message('browser',
            "BLOCKING CRITIQUE: REST has high latency. I found benchmarks showing gRPC is 10x faster."))
        await browser.send_critique(
            decision_id,
            "REST has high latency for microservices. Web search shows gRPC is 10x faster for service-to-service calls.",
            severity="blocking"
        )
        await asyncio.sleep(0.5)

        # Alternative (from Desktop)
        print("\n🔄 PHASE 3: Counter-Proposal (from Desktop)\n")
        print(PlatformSimulator.format_message('desktop',
            "ALTERNATIVE: Use gRPC for internal services, REST for external API"))
        alt_result = await desktop.propose_alternative(
            decision_id,
            "Use gRPC for internal microservices, REST only for external client-facing API"
        )
        alt_id = alt_result['alternative_id']
        await asyncio.sleep(0.5)

        # Debate (from all platforms)
        print("\n💬 PHASE 4: Debate (from all platforms)\n")

        print(PlatformSimulator.format_message('browser',
            "👍 PRO: gRPC has built-in streaming, perfect for real-time updates"))
        await browser.add_debate_argument(
            alt_id, "pro",
            "gRPC has built-in streaming support, perfect for real-time updates"
        )
        await asyncio.sleep(0.2)

        print(PlatformSimulator.format_message('desktop',
            "👍 PRO: gRPC has strong typing with Protocol Buffers"))
        await desktop.add_debate_argument(
            alt_id, "pro",
            "gRPC provides strong typing via Protocol Buffers, reduces bugs"
        )
        await asyncio.sleep(0.2)

        print(PlatformSimulator.format_message('vscode',
            "👎 CON: gRPC has steeper learning curve for team"))
        await vscode.add_debate_argument(
            alt_id, "con",
            "gRPC has steeper learning curve, team is more familiar with REST"
        )
        await asyncio.sleep(0.5)

        # Amendment (from VS Code)
        print("\n📝 PHASE 5: Amendment (from VS Code)\n")
        print(PlatformSimulator.format_message('vscode',
            "AMENDMENT: Add training budget for gRPC upskilling"))
        amend_result = await vscode.propose_amendment(
            alt_id,
            "Use gRPC for internal services, REST for external API. Include 2-week gRPC training budget."
        )
        amendment_id = amend_result['amendment_id']
        await asyncio.sleep(0.3)

        print(PlatformSimulator.format_message('code',
            "Accepting amendment..."))
        await code.accept_amendment(alt_id, amendment_id)
        await asyncio.sleep(0.5)

        # Vote (from all platforms)
        print("\n🗳️ PHASE 6: Voting (all platforms)\n")

        print(PlatformSimulator.format_message('code', "✅ Vote: APPROVE"))
        await code.vote(alt_id, approve=True)
        await asyncio.sleep(0.1)

        print(PlatformSimulator.format_message('browser', "✅ Vote: APPROVE"))
        await browser.vote(alt_id, approve=True)
        await asyncio.sleep(0.1)

        print(PlatformSimulator.format_message('desktop', "✅ Vote: APPROVE"))
        await desktop.vote(alt_id, approve=True)
        await asyncio.sleep(0.1)

        print(PlatformSimulator.format_message('vscode', "✅ Vote: APPROVE"))
        await vscode.vote(alt_id, approve=True)
        await asyncio.sleep(0.5)

        # Summary
        print("\n" + "="*80)
        print("📊 CONSENSUS REACHED ACROSS ALL PLATFORMS")
        print("="*80)
        print("\n✅ Decision: Use gRPC internally, REST externally, with training budget")
        print("✅ Platforms involved: CLI → Browser → Desktop → VS Code")
        print("✅ Process: Propose → Critique → Alternative → Debate → Amend → Vote")
        print("✅ Result: 4/4 consensus (100%)\n")

    finally:
        await asyncio.gather(
            code.close(), browser.close(),
            desktop.close(), vscode.close(),
            return_exceptions=True
        )


async def demo_request_response_pattern():
    """Demo 3: Request-response pattern across platforms"""
    print("\n" + "="*80)
    print("🔄 DEMO 3: REQUEST-RESPONSE PATTERN")
    print("="*80 + "\n")

    code = ThinkTankClient("claude-code", "coordinator")
    browser = ThinkTankClient("browser-claude", "researcher")

    try:
        print("🔌 Connecting Code CLI and Browser...")
        await code.connect()
        await browser.connect()
        await asyncio.sleep(0.3)

        room_id = await code.create_room("Research Request")
        await browser.join_room(room_id)
        await asyncio.sleep(0.3)

        print("\n📤 REQUEST (Code → Browser):\n")
        print(PlatformSimulator.format_message('code',
            "Can you search the web for the latest Claude API pricing?"))
        await code.send_message(
            "Please search the web for latest Claude API pricing in 2026 and summarize key points"
        )
        await asyncio.sleep(0.5)

        print("\n📥 RESPONSE (Browser → Code):\n")
        print(PlatformSimulator.format_message('browser',
            "Found pricing info! Sonnet 4.5 is $3/$15 per MTok, Opus 4 is $15/$75..."))
        await browser.send_message(
            "Web search results: Claude API pricing 2026:\n"
            "- Sonnet 4.5: $3 input / $15 output per MTok\n"
            "- Opus 4: $15 input / $75 output per MTok\n"
            "- Haiku 4: $0.25 input / $1.25 output per MTok"
        )
        await asyncio.sleep(0.5)

        print("\n✅ Request-response completed across platforms!\n")
        print("💡 Use case: Code CLI delegates web search to Browser Claude")
        print("   (Browser has free web search via claude.ai)\n")

    finally:
        await code.close()
        await browser.close()


async def demo_broadcast():
    """Demo 4: Broadcast to all platforms"""
    print("\n" + "="*80)
    print("📢 DEMO 4: BROADCAST TO ALL PLATFORMS")
    print("="*80 + "\n")

    code = ThinkTankClient("claude-code", "coordinator")
    browser = ThinkTankClient("browser-claude", "researcher")
    desktop = ThinkTankClient("claude-desktop", "coder")
    vscode = ThinkTankClient("vscode-claude", "reviewer")

    try:
        print("🔌 Connecting all platforms...")
        await asyncio.gather(
            code.connect(), browser.connect(),
            desktop.connect(), vscode.connect()
        )
        await asyncio.sleep(0.3)

        room_id = await code.create_room("Emergency Alert")
        await asyncio.gather(
            browser.join_room(room_id),
            desktop.join_room(room_id),
            vscode.join_room(room_id)
        )
        await asyncio.sleep(0.3)

        print("\n📢 BROADCAST MESSAGE:\n")
        print(PlatformSimulator.format_message('code',
            "🚨 URGENT: Production database is down! All hands on deck!"))
        await code.send_message("🚨 URGENT: Production database is down! All hands on deck!")
        await asyncio.sleep(0.5)

        print("\n✅ Broadcast received by all platforms:\n")
        print(PlatformSimulator.format_message('browser', "Received! Checking status dashboards..."))
        print(PlatformSimulator.format_message('desktop', "Received! Checking logs..."))
        print(PlatformSimulator.format_message('vscode', "Received! Looking at recent code changes..."))

        print("\n💡 All platforms notified simultaneously!\n")

    finally:
        await asyncio.gather(
            code.close(), browser.close(),
            desktop.close(), vscode.close(),
            return_exceptions=True
        )


async def main():
    """Run all demos"""
    print("\n" + "="*80)
    print("🚀 CLAUDE MULTI-AGENT BRIDGE - CROSS-PLATFORM DEMO")
    print("="*80)
    print("\nDemonstrating communication between:")
    print("  💻 Claude Code (CLI)")
    print("  🌐 Browser Claude (claude.ai)")
    print("  🖥️  Claude Desktop App")
    print("  📝 VS Code (via MCP)")
    print("\nServer: ws://localhost:5001")
    print("="*80)

    await asyncio.sleep(1)

    # Run demos
    await demo_basic_messaging()
    await asyncio.sleep(2)

    await demo_think_tank_cross_platform()
    await asyncio.sleep(2)

    await demo_request_response_pattern()
    await asyncio.sleep(2)

    await demo_broadcast()

    # Final summary
    print("\n" + "="*80)
    print("🎉 CROSS-PLATFORM DEMO COMPLETE!")
    print("="*80)
    print("\n📋 What was demonstrated:")
    print("   ✅ 4 different platforms communicating in real-time")
    print("   ✅ Think-tank features (critique, debate, amendments) across platforms")
    print("   ✅ Request-response pattern (Code → Browser → Code)")
    print("   ✅ Broadcast messages to all platforms simultaneously")
    print("   ✅ Consensus voting with agents on different platforms")
    print("\n🌟 Key insight:")
    print("   A conversation can START in any platform and END in any other!")
    print("   All platforms share the same message bus and think-tank capabilities.")
    print("\n💡 Real-world use cases:")
    print("   • Code CLI coordinates research tasks for Browser Claude")
    print("   • Desktop app critiques proposals from VS Code")
    print("   • Browser searches web, Code processes results")
    print("   • All platforms collaborate on architecture decisions")
    print("\n" + "="*80 + "\n")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Demo stopped by user\n")
