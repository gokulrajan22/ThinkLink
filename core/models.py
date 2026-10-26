from django.conf import settings
from django.db import models


SEMESTER_CHOICES = [(n, f"Semester {n}") for n in range(1, 9)]


class StudentProfile(models.Model):
    """Student profile. Skill levels are self-reported, not verified."""
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="student_profile", null=True, blank=True,
    )
    slug = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=120)
    initials = models.CharField(max_length=8)
    contact_email = models.EmailField(max_length=254, blank=True)
    college = models.CharField(max_length=160, default="ThinkLink Campus")
    semester = models.PositiveSmallIntegerField(null=True, blank=True, choices=SEMESTER_CHOICES)
    skills = models.JSONField(default=dict, blank=True)
    interests = models.JSONField(default=list, blank=True)
    availability = models.CharField(max_length=160, blank=True)
    contribution = models.CharField(max_length=120, blank=True)
    github_username = models.CharField(max_length=39, blank=True)
    github_skill_evidence = models.JSONField(default=dict, blank=True)
    # Public repository name/description/URL saved when the owner links GitHub.
    github_projects = models.JSONField(default=list, blank=True)
    # Opt-in: other signed-in students may see github_projects only when True.
    share_github_projects = models.BooleanField(default=False)
    # Opt-out: verified students appear in the directory and can be contacted unless they hide.
    is_discoverable = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=True)
    privacy_consent_at = models.DateTimeField(null=True, blank=True)
    privacy_policy_version = models.CharField(max_length=40, blank=True)
    color = models.CharField(max_length=20, default="violet")
    is_demo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def semester_label(self):
        return f"Semester {self.semester}" if self.semester else ""

    @property
    def display_email(self):
        """Use the account email for a member's own profile, demo address otherwise.

        Never render this for another real student: their account email is private (templates gate on
        is_demo or ownership; students contact each other through ThinkLink messages)."""
        return self.owner.email if self.owner_id else self.contact_email


class TeamAnalysis(models.Model):
    """A private team-analysis snapshot owned by the user who created it."""
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="team_analyses", null=True, blank=True,
    )
    title = models.CharField(max_length=200)
    problem_statement = models.TextField()
    selected_students = models.JSONField(default=list, blank=True)
    required_skills = models.JSONField(default=list, blank=True)
    covered_skills = models.JSONField(default=list, blank=True)
    missing_skills = models.JSONField(default=list, blank=True)
    coverage_score = models.PositiveSmallIntegerField(default=0)
    analysis_source = models.CharField(max_length=40, default="rules")
    # Owner opt-in: other students can see the project and request to join.
    is_open = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} — {self.created_at:%Y-%m-%d %H:%M}"


class RateLimitBucket(models.Model):
    """Shared request counters; database-backed for multi-instance deployments."""
    key = models.CharField(max_length=64, unique=True)
    scope = models.CharField(max_length=40, db_index=True)
    window_start = models.BigIntegerField(db_index=True)
    count = models.PositiveIntegerField(default=0)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["scope", "window_start"])]


class ProjectMembership(models.Model):
    ROLE_OWNER, ROLE_MEMBER = "owner", "member"
    project = models.ForeignKey(TeamAnalysis, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_memberships")
    role = models.CharField(max_length=10, choices=[(ROLE_OWNER, "Owner"), (ROLE_MEMBER, "Member")], default=ROLE_MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["project", "user"], name="unique_project_member")]
        ordering = ["joined_at"]


class TeamInvite(models.Model):
    """An owner inviting a student (kind=invite) or a student asking to join (kind=request)."""
    KIND_INVITE, KIND_REQUEST = "invite", "request"
    PENDING, ACCEPTED, DECLINED, CANCELLED = "pending", "accepted", "declined", "cancelled"
    project = models.ForeignKey(TeamAnalysis, on_delete=models.CASCADE, related_name="invites")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_invites")
    # For invites: the invited student. For requests: the project owner who must respond.
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_invites")
    kind = models.CharField(max_length=10, choices=[(KIND_INVITE, "Invite"), (KIND_REQUEST, "Join request")])
    status = models.CharField(max_length=10, default=PENDING, choices=[
        (PENDING, "Pending"), (ACCEPTED, "Accepted"), (DECLINED, "Declined"), (CANCELLED, "Cancelled")])
    message = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(
            fields=["project", "sender", "recipient", "kind"], condition=models.Q(status="pending"),
            name="unique_pending_invite")]


class Conversation(models.Model):
    """A 1:1 thread (project is null) or a project team chat."""
    project = models.OneToOneField(TeamAnalysis, on_delete=models.CASCADE, null=True, blank=True,
                                   related_name="conversation")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]


class ConversationMember(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversation_memberships")
    last_read_at = models.DateTimeField(null=True, blank=True)
    last_emailed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["conversation", "user"], name="unique_conversation_member")]


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages")
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        indexes = [models.Index(fields=["conversation", "id"])]


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True,
                              related_name="+")
    kind = models.CharField(max_length=20)
    text = models.CharField(max_length=200)
    # Always built server-side with reverse(); never taken from user input.
    link = models.CharField(max_length=200, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "is_read"])]
