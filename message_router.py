#!/usr/bin/env python3
"""
Message Router with Filtering and Rules
Content-based routing, transformations, and middleware
"""
import re
from typing import Callable, List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum


class ActionType(Enum):
    """Router action types"""

    ALLOW = "allow"
    DENY = "deny"
    TRANSFORM = "transform"
    REDIRECT = "redirect"
    DUPLICATE = "duplicate"
    LOG = "log"


@dataclass
class RoutingRule:
    """
    Message routing rule

    Examples:
        # Block spam
        RoutingRule(
            name="block_spam",
            condition=lambda msg: "spam" in msg['payload'].get('text', ''),
            action=ActionType.DENY
        )

        # Redirect errors to admin
        RoutingRule(
            name="errors_to_admin",
            condition=lambda msg: msg['type'] == 'error',
            action=ActionType.REDIRECT,
            params={'to': 'admin'}
        )
    """

    name: str
    condition: Callable[[Dict], bool]
    action: ActionType
    params: Dict[str, Any] = None
    priority: int = 5
    enabled: bool = True


class MessageRouter:
    """
    Route and transform messages based on rules

    Features:
    - Content-based routing
    - Message filtering (allow/deny)
    - Message transformation
    - Redirection to different clients
    - Message duplication (broadcast)
    - Rule chaining
    - Priority-based execution
    """

    def __init__(self):
        self.rules: List[RoutingRule] = []
        self.middleware: List[Callable] = []
        self.stats = {
            "total_processed": 0,
            "allowed": 0,
            "denied": 0,
            "transformed": 0,
            "redirected": 0,
            "duplicated": 0,
        }

    def add_rule(self, rule: RoutingRule):
        """Add routing rule"""
        self.rules.append(rule)
        # Sort by priority (lower number = higher priority)
        self.rules.sort(key=lambda r: r.priority)

    def remove_rule(self, name: str) -> bool:
        """Remove rule by name"""
        for i, rule in enumerate(self.rules):
            if rule.name == name:
                del self.rules[i]
                return True
        return False

    def add_middleware(self, func: Callable):
        """
        Add middleware function

        Middleware is called for every message before routing.
        Can modify message in-place or return None to block.

        Example:
            def add_timestamp(msg):
                msg['processed_at'] = datetime.now().isoformat()
                return msg

            router.add_middleware(add_timestamp)
        """
        self.middleware.append(func)

    def process(self, message: Dict) -> Optional[Dict]:
        """
        Process message through routing rules

        Args:
            message: Original message

        Returns:
            Processed message or None if denied
            Can return list of messages if duplicated
        """
        self.stats["total_processed"] += 1

        # Run middleware first
        for func in self.middleware:
            result = func(message)
            if result is None:
                self.stats["denied"] += 1
                return None
            message = result

        # Apply rules
        messages = [message]

        for rule in self.rules:
            if not rule.enabled:
                continue

            new_messages = []

            for msg in messages:
                if rule.condition(msg):
                    result = self._apply_action(msg, rule)

                    if result is None:
                        # Message blocked
                        continue
                    elif isinstance(result, list):
                        # Message duplicated
                        new_messages.extend(result)
                    else:
                        # Message modified or passed through
                        new_messages.append(result)
                else:
                    # Rule doesn't match, pass through
                    new_messages.append(msg)

            messages = new_messages

            if not messages:
                # All messages blocked
                return None

        # Return single message or list
        if len(messages) == 1:
            return messages[0]
        elif len(messages) > 1:
            return messages
        else:
            return None

    def _apply_action(self, message: Dict, rule: RoutingRule) -> Optional[Any]:
        """Apply routing action to message"""

        if rule.action == ActionType.DENY:
            self.stats["denied"] += 1
            return None

        elif rule.action == ActionType.ALLOW:
            self.stats["allowed"] += 1
            return message

        elif rule.action == ActionType.TRANSFORM:
            self.stats["transformed"] += 1
            transform_func = rule.params.get("function")
            if transform_func:
                return transform_func(message)
            return message

        elif rule.action == ActionType.REDIRECT:
            self.stats["redirected"] += 1
            new_to = rule.params.get("to")
            if new_to:
                message["to"] = new_to
            return message

        elif rule.action == ActionType.DUPLICATE:
            self.stats["duplicated"] += 1
            targets = rule.params.get("targets", [])

            # Create copies for each target
            copies = [message.copy()]
            for target in targets:
                copy = message.copy()
                copy["to"] = target
                copies.append(copy)

            return copies

        elif rule.action == ActionType.LOG:
            # Just log and pass through
            print(
                f"[ROUTER] {rule.name}: {message.get('type')} from {message.get('from')}"
            )
            return message

        return message

    def get_stats(self) -> Dict:
        """Get routing statistics"""
        return {
            **self.stats,
            "active_rules": sum(1 for r in self.rules if r.enabled),
            "total_rules": len(self.rules),
            "middleware_count": len(self.middleware),
        }


# ============================================================================
# Pre-built Rules
# ============================================================================


class CommonRules:
    """Common routing rules"""

    @staticmethod
    def block_spam(keywords: List[str]) -> RoutingRule:
        """Block messages containing spam keywords"""
        pattern = "|".join(re.escape(k) for k in keywords)

        return RoutingRule(
            name="block_spam",
            condition=lambda msg: re.search(
                pattern, str(msg.get("payload", {})), re.IGNORECASE
            )
            is not None,
            action=ActionType.DENY,
            priority=1,
        )

    @staticmethod
    def redirect_errors() -> RoutingRule:
        """Redirect all errors to admin"""
        return RoutingRule(
            name="errors_to_admin",
            condition=lambda msg: msg.get("type") == "error",
            action=ActionType.REDIRECT,
            params={"to": "admin"},
            priority=2,
        )

    @staticmethod
    def rate_limit_client(client_id: str, max_per_minute: int) -> RoutingRule:
        """Rate limit specific client (simplified)"""
        # In production, this would track timestamps
        count = {"current": 0}

        def check_rate(msg):
            if msg.get("from") == client_id:
                count["current"] += 1
                return count["current"] <= max_per_minute
            return True

        return RoutingRule(
            name=f"rate_limit_{client_id}",
            condition=lambda msg: not check_rate(msg),
            action=ActionType.DENY,
            priority=1,
        )

    @staticmethod
    def broadcast_to_all(clients: List[str]) -> RoutingRule:
        """Broadcast specific message types to all clients"""
        return RoutingRule(
            name="broadcast_alerts",
            condition=lambda msg: msg.get("type") == "alert",
            action=ActionType.DUPLICATE,
            params={"targets": clients},
            priority=3,
        )

    @staticmethod
    def transform_uppercase() -> RoutingRule:
        """Transform text to uppercase (example)"""

        def uppercase_text(msg):
            if "payload" in msg and "text" in msg["payload"]:
                msg["payload"]["text"] = msg["payload"]["text"].upper()
            return msg

        return RoutingRule(
            name="uppercase_transform",
            condition=lambda msg: msg.get("type") == "command",
            action=ActionType.TRANSFORM,
            params={"function": uppercase_text},
            priority=5,
        )


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🔀 Message Router Test")
    print("=" * 70)

    # Create router
    router = MessageRouter()

    # Add middleware
    def add_metadata(msg):
        msg["routed"] = True
        return msg

    router.add_middleware(add_metadata)

    # Add rules
    router.add_rule(CommonRules.block_spam(["spam", "advertisement"]))
    router.add_rule(CommonRules.redirect_errors())
    router.add_rule(CommonRules.broadcast_to_all(["monitor", "logger"]))

    # Test messages
    messages = [
        {
            "from": "user1",
            "to": "server",
            "type": "message",
            "payload": {"text": "Hello world"},
        },
        {
            "from": "user2",
            "to": "server",
            "type": "message",
            "payload": {"text": "Buy this spam product!"},
        },
        {
            "from": "app",
            "to": "server",
            "type": "error",
            "payload": {"message": "Database connection failed"},
        },
        {
            "from": "admin",
            "to": "all",
            "type": "alert",
            "payload": {"text": "System maintenance in 10 min"},
        },
    ]

    print("\n📨 Processing messages...")
    for i, msg in enumerate(messages, 1):
        print(f"\n{i}. {msg['type']} from {msg['from']}")
        result = router.process(msg)

        if result is None:
            print("   ❌ BLOCKED")
        elif isinstance(result, list):
            print(f"   📋 DUPLICATED to {len(result)} recipients")
            for r in result:
                print(f"      → {r['to']}")
        else:
            print(f"   ✅ ROUTED to {result['to']}")

    # Stats
    print("\n📊 Router stats:")
    for key, value in router.get_stats().items():
        print(f"   {key}: {value}")
