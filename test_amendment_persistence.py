#!/usr/bin/env python3
"""
Test amendment persistence fix
Verifies that accepted amendments persist to database
"""
import os
import tempfile
from datetime import datetime, timezone
from collaboration_enhanced import EnhancedCollaborationRoom, VoteType, MemberRole
from collab_persistence import CollabPersistence


def test_amendment_persists_to_database():
    """Test that amendment acceptance updates decision text in DB"""

    # Create temp database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name

    try:
        # Create room with persistence
        persistence = CollabPersistence(db_path)
        room = EnhancedCollaborationRoom("test-room", "Amendment Persistence Test")
        room.persistence = persistence

        # Add member
        room.join("alice", MemberRole.COORDINATOR)

        # Propose decision
        decision_id = room.propose_decision(
            "alice",
            "Use MongoDB for storage",
            VoteType.SIMPLE_MAJORITY
        )

        # Verify original text in database
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT text FROM decisions WHERE id = ?", (decision_id,))
        original_text = cursor.fetchone()[0]
        conn.close()

        assert original_text == "Use MongoDB for storage"
        print(f"✅ Original text persisted: {original_text}")

        # Propose amendment
        amendment_id = room.propose_amendment(
            from_client="alice",
            decision_id=decision_id,
            amendment_text="Use PostgreSQL for ACID compliance"
        )

        # Accept amendment
        room.accept_amendment(decision_id, amendment_id)

        # Verify updated text in database
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT text FROM decisions WHERE id = ?", (decision_id,))
        updated_text = cursor.fetchone()[0]
        conn.close()

        assert updated_text == "Use PostgreSQL for ACID compliance"
        print(f"✅ Amendment persisted: {updated_text}")

        # Verify in-memory matches database
        decision = next(d for d in room.decisions if d.id == decision_id)
        assert decision.text == updated_text
        print("✅ In-memory matches database")

        print("\n✅ ALL TESTS PASSED - Amendment persistence works!")
        return True

    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)


if __name__ == '__main__':
    test_amendment_persists_to_database()
