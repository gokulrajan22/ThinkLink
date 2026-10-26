"""Team invites, messaging, and notifications. Every authorization rule lives here so views stay thin."""
import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.db.models import F, Q
from django.urls import reverse
from django.utils import timezone

from .models import (Conversation, ConversationMember, Message, Notification, ProjectMembership,
                     StudentProfile, TeamAnalysis, TeamInvite)

logger = logging.getLogger(__name__)
MESSAGE_EMAIL_INTERVAL = timedelta(hours=1)
MAX_MESSAGE_LENGTH = 2000


class CollaborationError(Exception):
    """A rule was broken; the message is safe to show to the user."""


def display_name(user):
    profile = getattr(user, "student_profile", None)
    return (profile.name if profile else "") or user.get_full_name() or user.username


def discoverable_profiles(user):
    """Verified real students who have not hidden themselves, excluding the viewer."""
    return (StudentProfile.objects.filter(owner__isnull=False, owner__is_active=True, is_demo=False,
                                          is_discoverable=True).exclude(owner=user).select_related("owner"))


def shares_project(a, b):
    return ProjectMembership.objects.filter(user=a, project__memberships__user=b).exists()


def can_contact(sender, recipient):
    if recipient is None or recipient.pk == sender.pk or not recipient.is_active:
        return False
    profile = getattr(recipient, "student_profile", None)
    if profile is None or profile.is_demo:
        return False
    return profile.is_discoverable or shares_project(sender, recipient)


def is_member(project, user):
    return ProjectMembership.objects.filter(project=project, user=user).exists()


def ensure_owner_membership(project):
    if project.owner_id:
        ProjectMembership.objects.get_or_create(project=project, user_id=project.owner_id,
                                                defaults={"role": ProjectMembership.ROLE_OWNER})


def notify(user, kind, text, link="", actor=None, request=None, email_subject=None):
    note = Notification.objects.create(user=user, actor=actor, kind=kind, text=text[:200], link=link)
    profile = getattr(user, "student_profile", None)
    if email_subject and user.email and (profile is None or profile.email_notifications):
        url = request.build_absolute_uri(link) if request and link else ""
        body = f"{text}\n\n{url}\n\nYou can turn off these emails on your ThinkLink profile page."
        try:
            send_mail(email_subject, body, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
        except Exception:  # never let email failure break the action
            logger.exception("Notification email failed for kind=%s", kind)
    return note


# ---- Invites and join requests -------------------------------------------------------------

def send_invite(project, sender, recipient, message="", request=None):
    if project.owner_id != sender.pk:
        raise CollaborationError("Only the project owner can invite teammates.")
    if not can_contact(sender, recipient):
        raise CollaborationError("That student can't be invited.")
    if is_member(project, recipient):
        raise CollaborationError(f"{display_name(recipient)} is already on this team.")
    try:
        with transaction.atomic():
            invite = TeamInvite.objects.create(project=project, sender=sender, recipient=recipient,
                                               kind=TeamInvite.KIND_INVITE, message=message.strip()[:300])
    except IntegrityError:
        raise CollaborationError("An invite to this student is already pending.")
    notify(recipient, "invite", f"{display_name(sender)} invited you to join “{project.title}”.",
           reverse("invites"), actor=sender, request=request, email_subject="You've been invited to a ThinkLink team")
    return invite


def request_to_join(project, sender, message="", request=None):
    if not project.is_open or project.owner_id is None:
        raise CollaborationError("This project isn't accepting join requests.")
    if project.owner_id == sender.pk or is_member(project, sender):
        raise CollaborationError("You're already on this team.")
    try:
        with transaction.atomic():
            invite = TeamInvite.objects.create(project=project, sender=sender, recipient=project.owner,
                                               kind=TeamInvite.KIND_REQUEST, message=message.strip()[:300])
    except IntegrityError:
        raise CollaborationError("You already have a pending request for this project.")
    notify(project.owner, "request", f"{display_name(sender)} asked to join “{project.title}”.",
           reverse("invites"), actor=sender, request=request, email_subject="New ThinkLink join request")
    return invite


def respond(invite, user, accept, request=None):
    if invite.recipient_id != user.pk or invite.status != TeamInvite.PENDING:
        raise CollaborationError("This invite can't be answered.")
    invite.status = TeamInvite.ACCEPTED if accept else TeamInvite.DECLINED
    invite.responded_at = timezone.now()
    joiner = invite.recipient if invite.kind == TeamInvite.KIND_INVITE else invite.sender
    with transaction.atomic():
        invite.save(update_fields=["status", "responded_at"])
        if accept:
            ensure_owner_membership(invite.project)
            ProjectMembership.objects.get_or_create(project=invite.project, user=joiner)
            project_conversation(invite.project)
    verb = "accepted" if accept else "declined"
    what = "your invite to" if invite.kind == TeamInvite.KIND_INVITE else "your request to join"
    link = reverse("project-detail", args=[invite.project_id]) if accept else reverse("invites")
    notify(invite.sender, f"invite_{verb}", f"{display_name(user)} {verb} {what} “{invite.project.title}”.",
           link, actor=user, request=request)
    return invite


def cancel(invite, user):
    if invite.sender_id != user.pk or invite.status != TeamInvite.PENDING:
        raise CollaborationError("This invite can't be cancelled.")
    invite.status = TeamInvite.CANCELLED
    invite.responded_at = timezone.now()
    invite.save(update_fields=["status", "responded_at"])


def open_projects_for(user):
    """Other students' projects that accept join requests and that the user is not part of."""
    return (TeamAnalysis.objects.filter(is_open=True, owner__is_active=True).exclude(owner=user)
            .exclude(memberships__user=user).select_related("owner")[:12])


# ---- Messaging ------------------------------------------------------------------------------

def project_conversation(project):
    conversation, _ = Conversation.objects.get_or_create(project=project)
    member_ids = set(project.memberships.values_list("user_id", flat=True))
    existing = set(conversation.members.values_list("user_id", flat=True))
    ConversationMember.objects.bulk_create(
        [ConversationMember(conversation=conversation, user_id=uid) for uid in member_ids - existing],
        ignore_conflicts=True)
    return conversation


def get_or_create_dm(a, b):
    if not can_contact(a, b):
        raise CollaborationError("You can't message that student.")
    conversation = (Conversation.objects.filter(project=None, members__user=a)
                    .filter(members__user=b).first())
    if conversation is None:
        with transaction.atomic():
            conversation = Conversation.objects.create()
            ConversationMember.objects.bulk_create([ConversationMember(conversation=conversation, user=a),
                                                    ConversationMember(conversation=conversation, user=b)])
    return conversation


def conversations_for(user):
    return (Conversation.objects.filter(members__user=user)
            .select_related("project").prefetch_related("members__user__student_profile"))


def conversation_title(conversation, viewer):
    if conversation.project_id:
        return conversation.project.title
    others = [display_name(m.user) for m in conversation.members.all() if m.user_id != viewer.pk]
    return ", ".join(others) or "Conversation"


def mark_read(conversation, user):
    ConversationMember.objects.filter(conversation=conversation, user=user).update(last_read_at=timezone.now())


def unread_count(conversation, user):
    member = conversation.members.filter(user=user).first()
    qs = conversation.messages.exclude(sender=user)
    if member and member.last_read_at:
        qs = qs.filter(created_at__gt=member.last_read_at)
    return qs.count()


def unread_message_total(user):
    return (Message.objects.filter(Q(conversation__members__last_read_at__isnull=True)
                                   | Q(created_at__gt=F("conversation__members__last_read_at")),
                                   conversation__members__user=user)
            .exclude(sender=user).count())


def post_message(conversation, user, body, request=None):
    body = (body or "").strip()
    if not body:
        raise CollaborationError("Write a message first.")
    if len(body) > MAX_MESSAGE_LENGTH:
        raise CollaborationError(f"Messages can be at most {MAX_MESSAGE_LENGTH} characters.")
    if not conversation.members.filter(user=user).exists():
        raise CollaborationError("You're not part of this conversation.")
    message = Message.objects.create(conversation=conversation, sender=user, body=body)
    Conversation.objects.filter(pk=conversation.pk).update(updated_at=timezone.now())
    mark_read(conversation, user)
    link = reverse("message-thread", args=[conversation.pk])
    sender_name = display_name(user)
    now = timezone.now()
    where = f" in “{conversation.project.title}”" if conversation.project_id else ""
    for member in conversation.members.exclude(user=user).select_related("user__student_profile"):
        # One unread bell entry per conversation instead of one per message.
        if not Notification.objects.filter(user=member.user, kind="message", link=link, is_read=False).exists():
            send_email = member.last_emailed_at is None or now - member.last_emailed_at >= MESSAGE_EMAIL_INTERVAL
            notify(member.user, "message", f"New message from {sender_name}{where}.", link, actor=user,
                   request=request, email_subject="New ThinkLink message" if send_email else None)
            if send_email:
                ConversationMember.objects.filter(pk=member.pk).update(last_emailed_at=now)
    return message


def summary(user):
    return {
        "unread_notifications": Notification.objects.filter(user=user, is_read=False).count(),
        "unread_messages": unread_message_total(user),
        "pending_invites": TeamInvite.objects.filter(recipient=user, status=TeamInvite.PENDING).count(),
    }
