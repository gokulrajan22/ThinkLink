import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from core.models import StudentProfile, TeamAnalysis
from core.ai_service import analyze_problem


class ThinkLinkAuthAndAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="test-user", email="test@example.com", password="Strong-test-password-2026")
        self.student = StudentProfile.objects.create(
            owner=self.user, slug="test-student", name="Test Student", initials="TS",
            college="Test College", year="2nd year", skills={"python": 3, "research": 2},
            interests=["AI"], availability="Weekends", contribution="Backend", is_demo=False,
        )
        self.client.force_login(self.user)

    def test_health_endpoint_is_public(self):
        self.client.logout()
        response = self.client.get("/api/v1/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_private_endpoints_redirect_anonymous_users(self):
        self.client.logout()
        self.assertEqual(self.client.get("/").status_code, 302)
        self.assertEqual(self.client.get("/api/v1/students/").status_code, 302)
        self.assertEqual(self.client.get("/api/v1/analyses/").status_code, 302)

    def test_signup_creates_user_and_owned_profile(self):
        self.client.logout()
        response = self.client.post("/accounts/signup/", {
            "username": "new-student", "full_name": "New Student", "email": "new@example.com",
            "college": "Test College", "year": "1st year",
            "password1": "Long-secure-passphrase-2026", "password2": "Long-secure-passphrase-2026",
            "privacy_consent": "on",
        })
        self.assertEqual(response.status_code, 302)
        new_user = User.objects.get(username="new-student")
        profile = StudentProfile.objects.get(owner=new_user)
        self.assertFalse(profile.is_demo)
        self.assertEqual(profile.name, "New Student")
        self.assertFalse(new_user.is_active)
        self.assertTrue(profile.privacy_consent_at)
        from django.core import mail
        self.assertTrue(mail.outbox)
        import re
        token = re.search(r"/accounts/verify/([^/]+)/", mail.outbox[-1].body).group(1)
        verify_response = self.client.get(f"/accounts/verify/{token}/")
        self.assertEqual(verify_response.status_code, 302)
        new_user.refresh_from_db()
        self.assertTrue(new_user.is_active)

    def test_profile_edit_updates_only_the_signed_in_users_profile(self):
        response = self.client.post("/profile/", {
            "name": "Updated Student", "college": "Test College", "year": "3rd year",
            "contribution": "Backend", "availability": "Weekends",
            "interests": "AI, accessibility", "skills_text": "python=4\nresearch=3",
        })
        self.assertEqual(response.status_code, 302)
        self.student.refresh_from_db()
        self.assertEqual(self.student.name, "Updated Student")
        self.assertEqual(self.student.skills, {"python": 4, "research": 3})
        self.assertEqual(self.student.interests, ["AI", "accessibility"])

    def test_profile_editor_requires_authentication(self):
        self.client.logout()
        self.assertEqual(self.client.get("/profile/").status_code, 302)

    def test_student_directory_only_includes_demo_and_own_profiles(self):
        other = User.objects.create_user(username="other-user", password="Other-strong-password-2026")
        StudentProfile.objects.create(owner=other, slug="other-private-profile", name="Other Student",
                                      initials="OS", college="Other College", is_demo=False)
        response = self.client.get("/api/v1/students/")
        self.assertEqual(response.status_code, 200)
        ids = {item["id"] for item in response.json()["results"]}
        self.assertIn("test-student", ids)
        self.assertNotIn("other-private-profile", ids)

    def test_saved_analyses_are_private_to_owner(self):
        own = TeamAnalysis.objects.create(owner=self.user, title="My private analysis",
                                          problem_statement="Private problem statement")
        other_user = User.objects.create_user(username="other-analysis-user", password="Other-strong-password-2026")
        TeamAnalysis.objects.create(owner=other_user, title="Other private analysis",
                                    problem_statement="Other private problem statement")
        response = self.client.get("/api/v1/analyses/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.json()["results"]], [own.id])

    def test_ai_uses_rule_fallback_without_key(self):
        with patch.dict("os.environ", {"GROQ_API_KEY": ""}):
            result, notice = analyze_problem("Build a Python backend API and SQL database.")
        self.assertEqual(result["analysis_source"], "rules")
        self.assertTrue(result["required_skills"])
        self.assertIn("not configured", notice)

    def test_team_analysis_is_saved_to_authenticated_owner(self):
        response = self.client.post("/", {
            "action": "analyze", "title": "Test project",
            "idea": "Build a Python backend API with a SQL database and a web dashboard.",
            "team": ["test-student"],
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Team fit report")
        record = TeamAnalysis.objects.get()
        self.assertEqual(record.owner, self.user)
        self.assertEqual(record.selected_students, ["test-student"])

    def test_github_invalid_username_is_handled_without_network(self):
        response = self.client.post("/github/analyze/", {"github_username": "not a valid username", "github_consent": "yes"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "valid GitHub username")

    @patch("core.views.analyze_github_user")
    def test_github_evidence_can_only_be_associated_with_own_profile(self, github_mock):
        github_mock.return_value = {
            "username": "test-gh", "profile_url": "https://github.com/test-gh", "public_repos": 1,
            "repositories": [{"name": "sample-repo", "url": "https://github.com/test-gh/sample-repo", "language": "Python", "updated_at": "2026-01-01"}],
            "inferred_skills": [{"skill_id": "github", "skill": "Git / GitHub workflows", "evidence": ["repository file: package.json"]}],
            "note": "Test evidence only.",
        }
        response = self.client.post("/github/analyze/", {"github_username": "test-gh", "student_slug": "test-student", "github_consent": "yes"})
        self.assertEqual(response.status_code, 200)
        self.student.refresh_from_db()
        self.assertEqual(self.student.github_username, "test-gh")
        self.assertIn("github", self.student.github_skill_evidence)

        other = User.objects.create_user(username="other-user2", password="Other-strong-password-2026")
        other_profile = StudentProfile.objects.create(owner=other, slug="other-profile", name="Other Student",
                                                       initials="OS", college="Other College", is_demo=False)
        self.client.post("/github/analyze/", {"github_username": "test-gh", "student_slug": "other-profile", "github_consent": "yes"})
        other_profile.refresh_from_db()
        self.assertEqual(other_profile.github_username, "")

    def test_privacy_notice_is_public_and_account_export_is_private(self):
        self.client.logout()
        self.assertEqual(self.client.get("/privacy/").status_code, 200)
        self.assertEqual(self.client.get("/account/export/").status_code, 302)
        self.client.force_login(self.user)
        TeamAnalysis.objects.create(owner=self.user, title="Export test", problem_statement="A private idea")
        response = self.client.get("/account/export/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment;", response["Content-Disposition"])
        payload = json.loads(response.content)
        self.assertEqual(payload["account"]["username"], self.user.username)
        self.assertEqual(payload["team_analyses"][0]["problem_statement"], "A private idea")

    def test_account_deletion_requires_password_and_deletes_owned_records(self):
        TeamAnalysis.objects.create(owner=self.user, title="Delete me", problem_statement="Private")
        bad = self.client.post("/account/delete/", {"password": "wrong", "confirm_delete": "DELETE"})
        self.assertEqual(bad.status_code, 400)
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())
        response = self.client.post("/account/delete/", {
            "password": "Strong-test-password-2026", "confirm_delete": "DELETE",
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())
        self.assertFalse(StudentProfile.objects.filter(slug="test-student").exists())
        self.assertFalse(TeamAnalysis.objects.filter(title="Delete me").exists())

    @patch("core.views.analyze_github_user")
    def test_github_projects_saved_and_shared_only_on_opt_in(self, github_mock):
        github_mock.return_value = {
            "username": "test-gh", "profile_url": "https://github.com/test-gh", "public_repos": 2,
            "repositories": [
                {"name": "sample-repo", "url": "https://github.com/test-gh/sample-repo", "language": "Python",
                 "description": "A short demo project", "updated_at": "2026-01-01"},
                {"name": "bad-link", "url": "javascript:alert(1)", "language": "", "description": "", "updated_at": ""},
            ],
            "inferred_skills": [], "note": "Test evidence only.",
        }
        self.client.post("/github/analyze/", {"github_username": "test-gh", "student_slug": "test-student", "github_consent": "yes"})
        self.student.refresh_from_db()
        self.assertEqual([p["name"] for p in self.student.github_projects], ["sample-repo"])
        self.assertFalse(self.student.share_github_projects)
        self.assertContains(self.client.get("/"), "A short demo project")

        viewer = User.objects.create_user(username="viewer", password="Viewer-strong-password-2026")
        self.client.force_login(viewer)
        self.assertNotContains(self.client.get("/"), "A short demo project")

        self.client.force_login(self.user)
        self.client.post("/github/analyze/", {"github_username": "test-gh", "student_slug": "test-student",
                                              "github_consent": "yes", "share_github_projects": "yes"})
        self.client.force_login(viewer)
        self.assertContains(self.client.get("/"), "A short demo project")

    @patch("core.views.analyze_github_user")
    def test_github_analysis_requires_explicit_consent(self, github_mock):
        response = self.client.post("/github/analyze/", {"github_username": "test-gh"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please confirm that you consent")
        github_mock.assert_not_called()

    def test_unverified_account_with_correct_password_gets_verification_hint(self):
        self.client.logout()
        User.objects.create_user(username="pending", email="p@example.com", password="Pending-strong-password-2026", is_active=False)
        right = self.client.post("/accounts/login/", {"username": "pending", "password": "Pending-strong-password-2026"})
        self.assertContains(right, "isn&#x27;t verified yet")
        wrong = self.client.post("/accounts/login/", {"username": "pending", "password": "wrong-password"})
        self.assertNotContains(wrong, "verified yet")

    def test_password_reset_and_verification_resend_pages_load(self):
        self.client.logout()
        self.assertEqual(self.client.get("/accounts/password-reset/").status_code, 200)
        self.assertEqual(self.client.get("/accounts/verify/resend/").status_code, 200)
        response = self.client.post("/accounts/verify/resend/", {"email": "nobody@example.com"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/accounts/login/")
        login_page = self.client.get("/accounts/login/")
        self.assertContains(login_page, "If that address has an unverified ThinkLink account")
