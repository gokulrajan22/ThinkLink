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
        })
        self.assertEqual(response.status_code, 302)
        new_user = User.objects.get(username="new-student")
        profile = StudentProfile.objects.get(owner=new_user)
        self.assertFalse(profile.is_demo)
        self.assertEqual(profile.name, "New Student")

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
        response = self.client.post("/github/analyze/", {"github_username": "not a valid username"})
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
        response = self.client.post("/github/analyze/", {"github_username": "test-gh", "student_slug": "test-student"})
        self.assertEqual(response.status_code, 200)
        self.student.refresh_from_db()
        self.assertEqual(self.student.github_username, "test-gh")
        self.assertIn("github", self.student.github_skill_evidence)

        other = User.objects.create_user(username="other-user2", password="Other-strong-password-2026")
        other_profile = StudentProfile.objects.create(owner=other, slug="other-profile", name="Other Student",
                                                       initials="OS", college="Other College", is_demo=False)
        self.client.post("/github/analyze/", {"github_username": "test-gh", "student_slug": "other-profile"})
        other_profile.refresh_from_db()
        self.assertEqual(other_profile.github_username, "")
