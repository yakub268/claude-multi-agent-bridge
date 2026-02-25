#!/usr/bin/env python3
"""
GitHub Integration for Collaboration Room
Create issues, PRs, and review code directly from multi-Claude rooms

Identified in collaborative brainstorming as improvement idea
"""
import os
import json
import subprocess
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class GitHubIssue:
    """GitHub issue"""

    number: int
    title: str
    body: str
    state: str
    created_by: str
    labels: List[str]
    assignees: List[str]
    url: str


@dataclass
class GitHubPR:
    """GitHub pull request"""

    number: int
    title: str
    body: str
    state: str
    created_by: str
    source_branch: str
    target_branch: str
    url: str
    reviewers: List[str]


class GitHubIntegration:
    """
    GitHub integration for collaboration room

    Features:
    - Create issues from room discussions
    - Create PRs from code changes
    - Add code reviews
    - Link room decisions to GitHub
    - Auto-label issues
    - Assign to room members

    Requires: gh CLI installed and authenticated
    """

    def __init__(self, repo: str):
        """
        Initialize GitHub integration

        Args:
            repo: Repository in format "owner/repo"
        """
        self.repo = repo
        self._check_gh_cli()

    def _check_gh_cli(self):
        """Check if gh CLI is installed and authenticated"""
        try:
            result = subprocess.run(
                ["gh", "auth", "status"], capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                raise Exception("gh CLI not authenticated. Run: gh auth login")
        except FileNotFoundError:
            raise Exception("gh CLI not found. Install from: https://cli.github.com/")

    def create_issue(
        self,
        title: str,
        body: str,
        created_by: str,
        labels: List[str] = None,
        assignees: List[str] = None,
        room_link: str = None,
    ) -> GitHubIssue:
        """
        Create GitHub issue

        Args:
            title: Issue title
            body: Issue description
            created_by: Creator (room member)
            labels: Issue labels
            assignees: Issue assignees
            room_link: Link back to collaboration room

        Returns:
            Created issue
        """
        # Add room context to body
        full_body = body
        if room_link:
            full_body += f"\n\n---\n🤝 Created from collaboration room: {room_link}"
        full_body += f"\n👤 Created by: {created_by}"

        # Build command
        cmd = [
            "gh",
            "issue",
            "create",
            "--repo",
            self.repo,
            "--title",
            title,
            "--body",
            full_body,
        ]

        if labels:
            cmd.extend(["--label", ",".join(labels)])

        if assignees:
            cmd.extend(["--assignee", ",".join(assignees)])

        # Execute
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            raise Exception(f"Failed to create issue: {result.stderr}")

        # Parse issue URL from output
        issue_url = result.stdout.strip()

        # Get issue number from URL
        issue_number = int(issue_url.split("/")[-1])

        return GitHubIssue(
            number=issue_number,
            title=title,
            body=full_body,
            state="open",
            created_by=created_by,
            labels=labels or [],
            assignees=assignees or [],
            url=issue_url,
        )

    def create_pr(
        self,
        title: str,
        body: str,
        source_branch: str,
        target_branch: str = "main",
        created_by: str = "",
        reviewers: List[str] = None,
        room_link: str = None,
    ) -> GitHubPR:
        """
        Create GitHub pull request

        Args:
            title: PR title
            body: PR description
            source_branch: Source branch
            target_branch: Target branch
            created_by: Creator
            reviewers: Requested reviewers
            room_link: Link to room

        Returns:
            Created PR
        """
        # Add room context
        full_body = body
        if room_link:
            full_body += f"\n\n---\n🤝 Created from collaboration room: {room_link}"
        if created_by:
            full_body += f"\n👤 Created by: {created_by}"

        # Build command
        cmd = [
            "gh",
            "pr",
            "create",
            "--repo",
            self.repo,
            "--title",
            title,
            "--body",
            full_body,
            "--base",
            target_branch,
            "--head",
            source_branch,
        ]

        if reviewers:
            cmd.extend(["--reviewer", ",".join(reviewers)])

        # Execute
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            raise Exception(f"Failed to create PR: {result.stderr}")

        pr_url = result.stdout.strip()
        pr_number = int(pr_url.split("/")[-1])

        return GitHubPR(
            number=pr_number,
            title=title,
            body=full_body,
            state="open",
            created_by=created_by,
            source_branch=source_branch,
            target_branch=target_branch,
            url=pr_url,
            reviewers=reviewers or [],
        )

    def add_pr_review(
        self, pr_number: int, reviewer: str, approve: bool = True, comment: str = ""
    ) -> bool:
        """
        Add review to pull request

        Args:
            pr_number: PR number
            reviewer: Reviewer name
            approve: True to approve, False to request changes
            comment: Review comment

        Returns:
            True if review added
        """
        review_state = "APPROVE" if approve else "REQUEST_CHANGES"

        cmd = [
            "gh",
            "pr",
            "review",
            str(pr_number),
            "--repo",
            self.repo,
            "--" + review_state.lower().replace("_", "-"),
        ]

        if comment:
            cmd.extend(["--body", f"{comment}\n\n🤝 Review from: {reviewer}"])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        return result.returncode == 0

    def add_issue_comment(self, issue_number: int, author: str, comment: str) -> bool:
        """
        Add comment to issue

        Args:
            issue_number: Issue number
            author: Comment author
            comment: Comment text

        Returns:
            True if comment added
        """
        full_comment = f"{comment}\n\n👤 {author}"

        cmd = [
            "gh",
            "issue",
            "comment",
            str(issue_number),
            "--repo",
            self.repo,
            "--body",
            full_comment,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        return result.returncode == 0

    def close_issue(self, issue_number: int, reason: str = "") -> bool:
        """Close issue"""
        cmd = ["gh", "issue", "close", str(issue_number), "--repo", self.repo]

        if reason:
            cmd.extend(["--comment", f"Closing: {reason}"])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        return result.returncode == 0

    def merge_pr(self, pr_number: int, merge_method: str = "squash") -> bool:
        """
        Merge pull request

        Args:
            pr_number: PR number
            merge_method: 'merge', 'squash', or 'rebase'

        Returns:
            True if merged
        """
        cmd = [
            "gh",
            "pr",
            "merge",
            str(pr_number),
            "--repo",
            self.repo,
            "--" + merge_method,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        return result.returncode == 0

    def get_issue(self, issue_number: int) -> Optional[GitHubIssue]:
        """Get issue details"""
        cmd = [
            "gh",
            "issue",
            "view",
            str(issue_number),
            "--repo",
            self.repo,
            "--json",
            "number,title,body,state,labels,assignees,url",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)

        return GitHubIssue(
            number=data["number"],
            title=data["title"],
            body=data["body"],
            state=data["state"],
            created_by="",
            labels=[label["name"] for label in data.get("labels", [])],
            assignees=[assignee["login"] for assignee in data.get("assignees", [])],
            url=data["url"],
        )

    def get_pr(self, pr_number: int) -> Optional[GitHubPR]:
        """Get PR details"""
        cmd = [
            "gh",
            "pr",
            "view",
            str(pr_number),
            "--repo",
            self.repo,
            "--json",
            "number,title,body,state,headRefName,baseRefName,url",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)

        return GitHubPR(
            number=data["number"],
            title=data["title"],
            body=data["body"],
            state=data["state"],
            created_by="",
            source_branch=data["headRefName"],
            target_branch=data["baseRefName"],
            url=data["url"],
            reviewers=[],
        )

    def list_open_issues(
        self, labels: List[str] = None, limit: int = 10
    ) -> List[GitHubIssue]:
        """List open issues"""
        cmd = [
            "gh",
            "issue",
            "list",
            "--repo",
            self.repo,
            "--limit",
            str(limit),
            "--json",
            "number,title,body,state,labels,assignees,url",
        ]

        if labels:
            cmd.extend(["--label", ",".join(labels)])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            return []

        data = json.loads(result.stdout)

        return [
            GitHubIssue(
                number=item["number"],
                title=item["title"],
                body=item["body"],
                state=item["state"],
                created_by="",
                labels=[label["name"] for label in item.get("labels", [])],
                assignees=[assignee["login"] for assignee in item.get("assignees", [])],
                url=item["url"],
            )
            for item in data
        ]

    def list_open_prs(self, limit: int = 10) -> List[GitHubPR]:
        """List open pull requests"""
        cmd = [
            "gh",
            "pr",
            "list",
            "--repo",
            self.repo,
            "--limit",
            str(limit),
            "--json",
            "number,title,body,state,headRefName,baseRefName,url",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode != 0:
            return []

        data = json.loads(result.stdout)

        return [
            GitHubPR(
                number=item["number"],
                title=item["title"],
                body=item["body"],
                state=item["state"],
                created_by="",
                source_branch=item["headRefName"],
                target_branch=item["baseRefName"],
                url=item["url"],
                reviewers=[],
            )
            for item in data
        ]


# Integration with collaboration room
class CollabRoomGitHub:
    """
    Helper to integrate GitHub with collaboration room
    """

    def __init__(self, room, github: GitHubIntegration):
        self.room = room
        self.github = github
        self.issue_map = {}  # room_decision_id -> github_issue_number
        self.pr_map = {}  # room_task_id -> github_pr_number

    def decision_to_issue(self, decision_id: str) -> Optional[GitHubIssue]:
        """
        Convert room decision to GitHub issue

        Args:
            decision_id: Decision ID from room

        Returns:
            Created issue
        """
        decision = None
        for d in self.room.decisions:
            if d.id == decision_id:
                decision = d
                break

        if not decision:
            return None

        # Create issue
        issue = self.github.create_issue(
            title=f"[Decision] {decision.text}",
            body=f"Decision from collaboration room\n\nProposed by: {decision.proposed_by}",
            created_by=decision.proposed_by,
            labels=["decision", "collaboration-room"],
            room_link=f"Room: {self.room.room_id}",
        )

        self.issue_map[decision_id] = issue.number

        # Announce in room
        self.room.send_message(
            "SYSTEM", f"✅ Created GitHub issue #{issue.number}: {issue.url}"
        )

        return issue

    def task_to_pr(self, task_id: str, branch: str) -> Optional[GitHubPR]:
        """
        Convert room task to GitHub PR

        Args:
            task_id: Task ID from room
            branch: Source branch

        Returns:
            Created PR
        """
        task = None
        for t in self.room.tasks:
            if t["id"] == task_id:
                task = t
                break

        if not task:
            return None

        # Create PR
        pr = self.github.create_pr(
            title=task["text"],
            body=f"Task from collaboration room\n\nAssignee: {task['assignee']}",
            source_branch=branch,
            created_by=task["assigned_by"],
            reviewers=[task["assignee"]],
            room_link=f"Room: {self.room.room_id}",
        )

        self.pr_map[task_id] = pr.number

        # Announce in room
        self.room.send_message("SYSTEM", f"✅ Created GitHub PR #{pr.number}: {pr.url}")

        return pr


if __name__ == "__main__":
    print("=" * 80)
    print("🐙 GitHub Integration for Collaboration Room")
    print("=" * 80)

    # Check gh CLI
    print("\n🔍 Checking gh CLI...")
    try:
        result = subprocess.run(["gh", "--version"], capture_output=True, text=True)
        print(f"   ✅ {result.stdout.strip()}")
    except FileNotFoundError:
        print("   ❌ gh CLI not found")
        print("   Install: https://cli.github.com/")
        exit(1)

    print("\n📋 Features:")
    print("   ✅ Create issues from room decisions")
    print("   ✅ Create PRs from room tasks")
    print("   ✅ Add code reviews")
    print("   ✅ Link room context to GitHub")
    print("   ✅ Auto-label and assign")

    print("\n📝 Usage:")
    print("   # In collaboration room")
    print("   decision_id = room.propose_decision('Use FastAPI for backend')")
    print("   room.approve_decision(decision_id, 'claude-1')")
    print("   ")
    print("   # Convert to GitHub issue")
    print("   gh = GitHubIntegration('owner/repo')")
    print("   collab_gh = CollabRoomGitHub(room, gh)")
    print("   issue = collab_gh.decision_to_issue(decision_id)")

    print("\n✅ GitHub integration ready!")
    print("   Requires: gh auth login")
