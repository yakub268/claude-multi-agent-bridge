#!/usr/bin/env python3
"""
Test Visionary Agent - The Opposite of Devil's Advocate
Dreams big, thinks in possibilities, sees upside potential
"""
import asyncio
from test_live_thinktank import ThinkTankClient


async def test_visionary_vs_devils_advocate():
    """
    Test: Visionary (dreamer) vs Devil's Advocate (critic)
    Both are extremes - one finds opportunities, one finds risks
    """
    print("\n" + "=" * 80)
    print("🌟 VISIONARY vs 😈 DEVIL'S ADVOCATE")
    print("=" * 80 + "\n")
    print("Roles:")
    print("  🌟 VISIONARY: Dreams big, sees possibilities, 10x thinking")
    print("  😈 DEVIL'S ADVOCATE: Finds flaws, sees risks, cautious thinking")
    print("  🎯 PRAGMATISTS: Balanced, grounded, realistic thinking")
    print("=" * 80 + "\n")

    coordinator = ThinkTankClient("claude-coordinator", "coordinator")
    visionary = ThinkTankClient("claude-visionary", "researcher")
    devils_advocate = ThinkTankClient("claude-devils-advocate", "reviewer")
    pragmatist1 = ThinkTankClient("claude-pragmatist1", "coder")
    pragmatist2 = ThinkTankClient("claude-pragmatist2", "tester")

    try:
        # Connect
        await asyncio.gather(
            coordinator.connect(),
            visionary.connect(),
            devils_advocate.connect(),
            pragmatist1.connect(),
            pragmatist2.connect(),
        )
        print("✅ 5 Claude instances connected\n")

        room_id = await coordinator.create_room("Bold Vision Discussion")
        await asyncio.gather(
            visionary.join_room(room_id),
            devils_advocate.join_room(room_id),
            pragmatist1.join_room(room_id),
            pragmatist2.join_room(room_id),
        )
        await asyncio.sleep(0.5)

        # Moderate proposal
        print("📋 MODERATE PROPOSAL:\n")
        proposal = (
            "Let's add AI chatbot to our website for customer support. "
            "Cost: $50k, estimated 20% reduction in support tickets."
        )
        print(f"   Coordinator: {proposal}\n")

        decision = await coordinator.propose_decision(
            proposal, vote_type="simple_majority"
        )
        decision_id = decision["decision_id"]
        await asyncio.sleep(0.5)

        print("💬 REACTIONS FROM DIFFERENT PERSONAS:\n")

        # Visionary - expands the vision 100x
        print("🌟 VISIONARY (dreams big):")
        visionary_response = (
            "This is THINKING TOO SMALL! Why stop at customer support chatbot?\n\n"
            "BIGGER VISION:\n"
            "• AI chatbot → Full AI customer success platform\n"
            "• Don't just reduce tickets 20% → ELIMINATE 90% of tickets\n"
            "• Add: AI sales assistant, AI product recommendations, AI onboarding\n"
            "• Predictive support: AI contacts customers BEFORE they have problems\n"
            "• This isn't $50k project → It's a $5M competitive moat\n"
            "• We could LICENSE this to other companies → New revenue stream\n\n"
            "What if this becomes our core product in 3 years? Let's think 10x!"
        )
        print(f"   {visionary_response[:200]}...")
        await visionary.add_debate_argument(decision_id, "pro", visionary_response)
        await asyncio.sleep(0.3)

        # Devil's Advocate - finds all the risks
        print("\n😈 DEVIL'S ADVOCATE (finds risks):")
        devils_response = (
            "HOLD ON - Too many red flags:\n\n"
            "RISKS:\n"
            "• $50k is a LOT. Have we tried cheaper solutions first?\n"
            "• AI chatbots hallucinate. One wrong answer → lawsuit\n"
            "• 20% reduction is OPTIMISTIC. Industry average is 10%\n"
            "• Our support team will resist (job security fears)\n"
            "• Customer backlash: 'I want a HUMAN not a robot'\n"
            "• Integration complexity: Does it work with our CRM?\n"
            "• Maintenance cost: AI needs constant retraining\n\n"
            "RECOMMENDATION: Pilot with 100 customers first, not full launch."
        )
        print(f"   {devils_response[:200]}...")
        await devils_advocate.send_critique(
            decision_id, devils_response, severity="major"
        )
        await asyncio.sleep(0.3)

        # Pragmatist 1 - balanced view
        print("\n🎯 PRAGMATIST 1 (balanced):")
        pragmatist1_response = (
            "Both have good points. Visionary sees opportunity, Devil's Advocate sees risks.\n\n"
            "BALANCED APPROACH:\n"
            "• Start with $50k chatbot (as proposed)\n"
            "• Add human escalation path (addresses devil's advocate concern)\n"
            "• Measure results after 3 months\n"
            "• IF successful (>15% ticket reduction), THEN expand to visionary's bigger vision\n"
            "• This way we test assumptions before big bet"
        )
        print(f"   {pragmatist1_response[:200]}...")
        await pragmatist1.add_debate_argument(decision_id, "pro", pragmatist1_response)
        await asyncio.sleep(0.5)

        # Summary
        print("\n" + "=" * 80)
        print("📊 DEBATE SUMMARY")
        print("=" * 80)
        print("\n🌟 VISIONARY:")
        print("   ✨ Expands scope 100x ($50k → $5M platform)")
        print("   ✨ Sees new revenue streams (license to others)")
        print("   ✨ Thinks in possibilities ('What if this is our core product?')")
        print("   ✨ Pushes team to 10x thinking")

        print("\n😈 DEVIL'S ADVOCATE:")
        print("   ⚠️  Identifies 7 risks (hallucination, cost, resistance, etc.)")
        print("   ⚠️  Questions assumptions (20% → 10% more realistic)")
        print("   ⚠️  Suggests de-risking (pilot first)")
        print("   ⚠️  Prevents over-commitment")

        print("\n🎯 PRAGMATISTS:")
        print("   ⚖️  Balance vision with risk")
        print("   ⚖️  Phased approach (test then expand)")
        print("   ⚖️  Measurable milestones")
        print("   ⚖️  Best of both worlds")

        print("\n💡 OUTCOME:")
        print("   Visionary INSPIRED bigger thinking")
        print("   Devil's Advocate PREVENTED reckless execution")
        print("   Pragmatists SYNTHESIZED into actionable plan")
        print("   → Result: Smart, ambitious, de-risked approach")

    finally:
        await asyncio.gather(
            coordinator.close(),
            visionary.close(),
            devils_advocate.close(),
            pragmatist1.close(),
            pragmatist2.close(),
            return_exceptions=True,
        )


async def test_visionary_transforms_rejection():
    """
    Test: Can visionary turn a rejection into an opportunity?
    """
    print("\n" + "=" * 80)
    print("🌟 TEST: VISIONARY TRANSFORMS REJECTION INTO OPPORTUNITY")
    print("=" * 80 + "\n")

    coordinator = ThinkTankClient("claude-coordinator", "coordinator")
    realist = ThinkTankClient("claude-realist", "reviewer")
    visionary = ThinkTankClient("claude-visionary", "researcher")

    try:
        await asyncio.gather(
            coordinator.connect(), realist.connect(), visionary.connect()
        )
        print("✅ 3 Claude instances connected\n")

        room_id = await coordinator.create_room("Failed Proposal Revival")
        await asyncio.gather(realist.join_room(room_id), visionary.join_room(room_id))
        await asyncio.sleep(0.3)

        # Initial proposal (will be rejected)
        print("📋 INITIAL PROPOSAL (rejected):\n")
        proposal = "Launch premium tier at $99/month (current is $19/month)"
        print(f"   {proposal}\n")

        decision = await coordinator.propose_decision(proposal)
        decision_id = decision["decision_id"]
        await asyncio.sleep(0.3)

        # Realist rejects
        print("❌ REALIST REJECTS:")
        print(
            "   'Too expensive. Customers will churn. We have no premium features to justify 5x price.'\n"
        )
        await realist.send_critique(
            decision_id,
            "Too expensive. Customers will churn. We have no premium features to justify 5x price.",
            severity="blocking",
        )
        await asyncio.sleep(0.5)

        # Visionary transforms rejection into bigger opportunity
        print("🌟 VISIONARY TRANSFORMS REJECTION:")
        vision = (
            "The realist is RIGHT - we can't charge $99 for current features.\n\n"
            "BUT... what if we BUILD the premium features FIRST?\n\n"
            "MOONSHOT VISION:\n"
            "• Premium tier isn't just 'more of the same'\n"
            "• It's a QUANTUM LEAP in value:\n"
            "  - AI-powered analytics (not basic reports)\n"
            "  - White-label capability (resell to their clients)\n"
            "  - Dedicated account manager\n"
            "  - API access for integrations\n"
            "  - Early access to new features\n\n"
            "NOW the question isn't 'Can we charge $99?'\n"
            "It's 'Can we justify NOT charging $199?'\n\n"
            "This isn't a price increase → It's creating a NEW PRODUCT.\n"
            "We're not moving customers up → We're attracting BIGGER customers.\n\n"
            "Rejection → Opportunity: Build the premium product that DESERVES $99+"
        )
        print(f"   {vision}\n")
        await visionary.propose_alternative(
            decision_id,
            "Don't just raise price - BUILD premium tier with 10x value: AI analytics, white-label, "
            "API, dedicated support. Target enterprise customers at $199/mo.",
        )
        await asyncio.sleep(0.5)

        print("=" * 80)
        print("📊 TRANSFORMATION ANALYSIS")
        print("=" * 80)
        print("\n❌ ORIGINAL (Rejected):")
        print("   'Charge 5x more for same product'")
        print("   → Doomed to fail")

        print("\n✅ VISIONARY ALTERNATIVE:")
        print("   'Build 10x value product, charge appropriately'")
        print("   → Creates new market segment")

        print("\n💡 KEY INSIGHT:")
        print("   Visionary didn't argue AGAINST rejection")
        print("   Visionary AGREED and made it BIGGER")
        print("   'You're right it won't work... so let's build what WILL work'")

        print("\n🎯 ROLE OF VISIONARY:")
        print("   ❌ NOT: Blindly optimistic (ignores reality)")
        print("   ✅ IS: Transforms constraints into opportunities")
        print("   ✅ IS: Asks 'What would make this 10x better?'")
        print("   ✅ IS: Sees possibilities others miss")

    finally:
        await coordinator.close()
        await realist.close()
        await visionary.close()


async def test_balanced_team():
    """
    Test: Ideal team composition with both extremes
    """
    print("\n" + "=" * 80)
    print("⚖️  IDEAL TEAM: VISIONARY + DEVIL'S ADVOCATE + PRAGMATISTS")
    print("=" * 80 + "\n")

    coordinator = ThinkTankClient("claude-coordinator", "coordinator")
    visionary = ThinkTankClient("claude-visionary", "researcher")
    devils_advocate = ThinkTankClient("claude-devils-advocate", "reviewer")
    builder = ThinkTankClient("claude-builder", "coder")
    executor = ThinkTankClient("claude-executor", "tester")

    try:
        await asyncio.gather(
            coordinator.connect(),
            visionary.connect(),
            devils_advocate.connect(),
            builder.connect(),
            executor.connect(),
        )
        print("✅ 5 Claude instances connected\n")
        print("Team Composition:")
        print("  🎯 Coordinator: Facilitates discussion")
        print("  🌟 Visionary: Dreams big, sees possibilities")
        print("  😈 Devil's Advocate: Finds risks, prevents disasters")
        print("  🔨 Builder: Focuses on implementation feasibility")
        print("  🚀 Executor: Focuses on execution and delivery\n")

        room_id = await coordinator.create_room("Balanced Team Decision")
        await asyncio.gather(
            visionary.join_room(room_id),
            devils_advocate.join_room(room_id),
            builder.join_room(room_id),
            executor.join_room(room_id),
        )
        await asyncio.sleep(0.3)

        print("📋 DECISION: Should we build a mobile app?\n")
        decision = await coordinator.propose_decision(
            "Build mobile app (iOS + Android). Estimated 6 months, $300k cost."
        )
        decision_id = decision["decision_id"]
        await asyncio.sleep(0.5)

        print("💬 TEAM DISCUSSION:\n")

        # Visionary
        print("🌟 VISIONARY:")
        print("   'Mobile isn't just an app - it's our FUTURE!'")
        print("   'Push notifications → 10x engagement'")
        print("   'Native experience → app store featuring → millions of downloads'")
        print("   'What if mobile becomes our PRIMARY platform?'\n")
        await visionary.add_debate_argument(
            decision_id,
            "pro",
            "Mobile is our FUTURE. Push notifications = 10x engagement. "
            "App store featuring could bring millions of users. "
            "This isn't just a feature - it's a strategic platform shift.",
        )
        await asyncio.sleep(0.2)

        # Devil's Advocate
        print("😈 DEVIL'S ADVOCATE:")
        print("   'WAIT - what's our mobile usage? 5% of traffic?'")
        print("   '$300k for 5% of users? ROI doesn't math'")
        print("   'Maintenance hell: 2 platforms (iOS + Android) to update forever'")
        print("   'Mobile web is 90% as good for 10% of cost'\n")
        await devils_advocate.send_critique(
            decision_id,
            "Mobile usage is only 5% of our traffic. $300k for 5% of users = poor ROI. "
            "Maintaining iOS + Android = 2x ongoing cost forever. "
            "Progressive Web App (PWA) gives 90% of benefits for 10% of cost.",
            severity="major",
        )
        await asyncio.sleep(0.2)

        # Builder
        print("🔨 BUILDER:")
        print("   'I can build PWA in 1 month vs 6 months for native'")
        print("   'PWA gives us push notifications + offline support'")
        print("   'Test mobile engagement FIRST, then go native if needed'\n")
        await builder.add_debate_argument(
            decision_id,
            "con",
            "PWA is faster path (1 month vs 6). Gives push notifications and offline support. "
            "We can test mobile engagement assumptions before committing to native. "
            "If PWA proves mobile demand, THEN invest in native.",
        )
        await asyncio.sleep(0.2)

        # Executor
        print("🚀 EXECUTOR:")
        print("   'Phased approach: PWA → iOS → Android'")
        print("   'Month 1: PWA launch, measure engagement'")
        print("   'Month 3: If >20% mobile usage, start iOS'")
        print("   'Month 6: If iOS successful, start Android'\n")
        await executor.add_debate_argument(
            decision_id,
            "pro",
            "Phased rollout de-risks: PWA first (1 month), measure mobile engagement. "
            "If >20% mobile traffic, build iOS (3 months). If iOS proves value, add Android. "
            "Each phase validates assumptions before next investment.",
        )
        await asyncio.sleep(0.5)

        print("=" * 80)
        print("📊 SYNTHESIS")
        print("=" * 80)
        print("\n🌟 VISIONARY contributed:")
        print("   ✨ Big vision (mobile as primary platform)")
        print("   ✨ Long-term strategic thinking")
        print("   ✨ Inspired team to think beyond current state")

        print("\n😈 DEVIL'S ADVOCATE contributed:")
        print("   ⚠️  Reality check (5% usage, $300k cost)")
        print("   ⚠️  Alternative consideration (PWA)")
        print("   ⚠️  Prevented premature $300k commitment")

        print("\n🔨 BUILDER contributed:")
        print("   🛠️  Practical path (PWA in 1 month)")
        print("   🛠️  Technical feasibility assessment")
        print("   🛠️  Cost-effective alternative")

        print("\n🚀 EXECUTOR contributed:")
        print("   📋 Phased approach (de-risked)")
        print("   📋 Clear milestones and decision gates")
        print("   📋 Actionable plan")

        print("\n🎯 FINAL DECISION:")
        print("   ✅ Phase 1: Build PWA (1 month, $30k)")
        print("   ✅ Phase 2: IF >20% mobile → iOS (3 months, $150k)")
        print("   ✅ Phase 3: IF iOS successful → Android (3 months, $150k)")
        print("\n   Total: Still $300k potential, but VALIDATED at each step")
        print(
            "   Combines: Visionary ambition + Devil's advocate caution + Builder practicality + Executor planning"
        )

        print("\n💡 KEY LESSON:")
        print("   Best decisions need BOTH extremes:")
        print("   🌟 Visionary → Inspires ambition")
        print("   😈 Devil's Advocate → Prevents disasters")
        print("   🎯 Pragmatists → Execute smartly")
        print("\n   Remove ANY role → Decision quality degrades")

    finally:
        await asyncio.gather(
            coordinator.close(),
            visionary.close(),
            devils_advocate.close(),
            builder.close(),
            executor.close(),
            return_exceptions=True,
        )


async def main():
    """Run all visionary tests"""
    print("\n" + "=" * 80)
    print("🌟 VISIONARY AGENT ANALYSIS")
    print("=" * 80)
    print("\nThe Opposite of Devil's Advocate:")
    print("  😈 Devil's Advocate: Finds risks, prevents disasters")
    print("  🌟 Visionary: Finds opportunities, inspires ambition")
    print("\nBoth extremes are valuable!")
    print("=" * 80)

    await test_visionary_vs_devils_advocate()
    await asyncio.sleep(2)

    await test_visionary_transforms_rejection()
    await asyncio.sleep(2)

    await test_balanced_team()

    # Final insights
    print("\n" + "=" * 80)
    print("🎓 KEY INSIGHTS")
    print("=" * 80)
    print("\n1. VISIONARY IS NOT 'BLIND OPTIMISM'")
    print("   ❌ Bad visionary: Ignores reality, unrealistic")
    print("   ✅ Good visionary: Sees possibilities, transforms constraints\n")

    print("2. VISIONARY + DEVIL'S ADVOCATE = POWERFUL COMBO")
    print("   🌟 Visionary: 'What if we 10x this?'")
    print("   😈 Devil's Advocate: 'Here are the risks...'")
    print("   🎯 Pragmatist: 'Here's how we do it safely...'\n")

    print("3. ROLE OF VISIONARY:")
    print("   ✨ Expands scope (thinks bigger)")
    print("   ✨ Sees secondary opportunities (new revenue streams)")
    print(
        "   ✨ Transforms rejections ('You're right... so let's build what WILL work')"
    )
    print("   ✨ Pushes team beyond incremental thinking\n")

    print("4. WHEN YOU NEED A VISIONARY:")
    print("   • Team is stuck in incremental thinking")
    print("   • Playing it too safe (missing big opportunities)")
    print("   • After a rejection (find the opportunity)")
    print("   • Strategic planning (where will we be in 5 years?)\n")

    print("5. WHEN YOU NEED DEVIL'S ADVOCATE:")
    print("   • Team is too excited (need reality check)")
    print("   • High-risk decision (need to surface risks)")
    print("   • Groupthink detected (need dissenting voice)")
    print("   • Before major commitment ($$$, resources, time)\n")

    print("6. IDEAL TEAM COMPOSITION:")
    print("   🎯 1 Coordinator (facilitates)")
    print("   🌟 1 Visionary (dreams big)")
    print("   😈 1 Devil's Advocate (finds risks)")
    print("   🔨 1-2 Builders (implementation focus)")
    print("   🚀 1 Executor (delivery focus)")
    print("\n   = 5 agents with complementary perspectives\n")

    print("💡 BOTTOM LINE:")
    print("   You need BOTH extremes for best decisions:")
    print("   • Too many visionaries → Unrealistic, no execution")
    print("   • Too many devil's advocates → Paralysis, no innovation")
    print("   • Balance = Ambitious goals + smart risk management")

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Tests stopped\n")
