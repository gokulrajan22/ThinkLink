"""Views for team invites, project teams, messaging, and notifications.

Objects are always fetched through querysets filtered by the signed-in user, so other people's
invites, projects, and conversations return 404 instead of leaking that they exist."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from . import collaboration as collab
from .models import Notification, StudentProfile, TeamAnalysis, TeamInvite
from .security import rate_limit


def _back(request, fallback):
    target = request.POST.get("next", "")
    return redirect(target if target.startswith("/") and not target.startswith("//") else fallback)


def _member_projects(user):
    return TeamAnalysis.objects.filter(memberships__user=user).distinct()


# ---- Invites --------------------------------------------------------------------------------

@login_required
def invites(request):
    base = TeamInvite.objects.select_related("project", "sender__student_profile", "recipient__student_profile")
    return render(request, "core/invites.html", {
        "active_nav": "invites",
        "incoming": base.filter(recipient=request.user, status=TeamInvite.PENDING),
        "outgoing": base.filter(sender=request.user, status=TeamInvite.PENDING),
        "history": base.filter(sender=request.user).exclude(status=TeamInvite.PENDING)[:10],
    })


@login_required
@require_POST
@rate_limit("invite-send", 30, 3600)
def invite_send(request):
    project = get_object_or_404(TeamAnalysis, pk=request.POST.get("project_id") or 0, owner=request.user)
    profile = get_object_or_404(StudentProfile, slug=request.POST.get("student", ""), owner__isnull=False)
    try:
        collab.send_invite(project, request.user, profile.owner, request.POST.get("message", ""), request=request)
        messages.success(request, f"Invite sent to {profile.name}.")
    except collab.CollaborationError as exc:
        messages.error(request, str(exc))
    return _back(request, "invites")


@login_required
@require_POST
@rate_limit("join-request", 20, 3600)
def project_request(request, pk):
    project = get_object_or_404(TeamAnalysis, pk=pk, is_open=True)
    try:
        collab.request_to_join(project, request.user, request.POST.get("message", ""), request=request)
        messages.success(request, f"Request sent to join “{project.title}”.")
    except collab.CollaborationError as exc:
        messages.error(request, str(exc))
    return _back(request, "invites")


@login_required
@require_POST
@rate_limit("invite-respond", 60, 3600)
def invite_respond(request, pk, action):
    try:
        if action == "cancel":
            collab.cancel(get_object_or_404(TeamInvite, pk=pk, sender=request.user), request.user)
            messages.success(request, "Invite cancelled.")
        else:
            invite = get_object_or_404(TeamInvite, pk=pk, recipient=request.user)
            collab.respond(invite, request.user, accept=(action == "accept"), request=request)
            messages.success(request, "Accepted — welcome to the team." if action == "accept" else "Declined.")
            if action == "accept":
                return redirect("project-detail", invite.project_id)
    except collab.CollaborationError as exc:
        messages.error(request, str(exc))
    return redirect("invites")


# ---- Project teams --------------------------------------------------------------------------

@login_required
def project_detail(request, pk):
    project = get_object_or_404(_member_projects(request.user).select_related("owner"), pk=pk)
    is_owner = project.owner_id == request.user.pk
    member_ids = list(project.memberships.values_list("user_id", flat=True))
    return render(request, "core/project_detail.html", {
        "project": project, "is_owner": is_owner,
        "members": project.memberships.select_related("user__student_profile"),
        "pending": project.invites.filter(status=TeamInvite.PENDING).select_related(
            "sender__student_profile", "recipient__student_profile") if is_owner else [],
        "candidates": collab.discoverable_profiles(request.user).exclude(owner_id__in=member_ids)[:50] if is_owner else [],
    })


@login_required
@require_POST
def project_toggle_open(request, pk):
    project = get_object_or_404(TeamAnalysis, pk=pk, owner=request.user)
    project.is_open = not project.is_open
    project.save(update_fields=["is_open"])
    collab.ensure_owner_membership(project)
    messages.success(request, "Project is now open to join requests." if project.is_open else "Project closed to join requests.")
    return _back(request, reverse("project-detail", args=[project.pk]))


@login_required
def project_chat(request, pk):
    project = get_object_or_404(_member_projects(request.user), pk=pk)
    return redirect("message-thread", collab.project_conversation(project).pk)


# ---- Messaging ------------------------------------------------------------------------------

@login_required
def messages_inbox(request):
    rows = []
    for conversation in collab.conversations_for(request.user)[:50]:
        last = conversation.messages.order_by("-id").first()
        rows.append({"conversation": conversation, "title": collab.conversation_title(conversation, request.user),
                     "last": last, "unread": collab.unread_count(conversation, request.user)})
    return render(request, "core/messages_inbox.html", {"active_nav": "messages", "rows": rows})


@login_required
@require_POST
@rate_limit("dm-start", 30, 3600)
def message_new(request, slug):
    profile = get_object_or_404(StudentProfile, slug=slug, owner__isnull=False)
    try:
        conversation = collab.get_or_create_dm(request.user, profile.owner)
    except collab.CollaborationError as exc:
        messages.error(request, str(exc))
        return _back(request, "messages-inbox")
    return redirect("message-thread", conversation.pk)


def _serialize(message, viewer):
    return {"id": message.pk, "sender": collab.display_name(message.sender), "body": message.body,
            "mine": message.sender_id == viewer.pk, "created": message.created_at.isoformat()}


@login_required
def message_thread(request, pk):
    conversation = get_object_or_404(collab.conversations_for(request.user), pk=pk)
    recent = list(conversation.messages.select_related("sender__student_profile").order_by("-id")[:100])[::-1]
    collab.mark_read(conversation, request.user)
    Notification.objects.filter(user=request.user, kind="message", link=request.path, is_read=False).update(is_read=True)
    return render(request, "core/message_thread.html", {
        "active_nav": "messages", "conversation": conversation, "thread": recent,
        "title": collab.conversation_title(conversation, request.user),
        "last_id": recent[-1].pk if recent else 0,
    })


@login_required
@require_POST
@rate_limit("message-send", 60, 600)
def message_send(request, pk):
    conversation = get_object_or_404(collab.conversations_for(request.user), pk=pk)
    wants_json = "application/json" in request.headers.get("Accept", "")
    try:
        message = collab.post_message(conversation, request.user, request.POST.get("body", ""), request=request)
    except collab.CollaborationError as exc:
        if wants_json:
            return JsonResponse({"error": str(exc)}, status=400)
        messages.error(request, str(exc))
        return redirect("message-thread", pk)
    if wants_json:
        return JsonResponse({"message": _serialize(message, request.user)})
    return redirect("message-thread", pk)


@login_required
@require_GET
def message_poll(request, pk):
    conversation = get_object_or_404(collab.conversations_for(request.user), pk=pk)
    try:
        after = max(int(request.GET.get("after", 0)), 0)
    except ValueError:
        after = 0
    new = list(conversation.messages.filter(id__gt=after).select_related("sender__student_profile")[:100])
    if new:
        collab.mark_read(conversation, request.user)
    return JsonResponse({"messages": [_serialize(m, request.user) for m in new]})


# ---- Notifications --------------------------------------------------------------------------

@login_required
def notifications(request):
    return render(request, "core/notifications.html", {
        "notes": Notification.objects.filter(user=request.user).select_related("actor")[:50]})


@login_required
def notification_open(request, pk):
    note = get_object_or_404(Notification, pk=pk, user=request.user)
    if not note.is_read:
        note.is_read = True
        note.save(update_fields=["is_read"])
    link = note.link if note.link.startswith("/") and not note.link.startswith("//") else ""
    return redirect(link or "notifications")


@login_required
@require_POST
def notifications_read_all(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return _back(request, "notifications")


@login_required
@require_GET
def api_notifications_summary(request):
    return JsonResponse(collab.summary(request.user))
