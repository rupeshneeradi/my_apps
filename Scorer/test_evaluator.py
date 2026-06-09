import unittest

from evaluator import evaluate_resume_fit, find_keyword_evidence
from semantic_scorer import score_with_domain_bank


class EvaluatorTest(unittest.TestCase):
    def test_experience_evidence_beats_skill_listing(self):
        resume = """
        Technical Skills
        Python, SQL, Selenium

        Professional Experience
        Built Selenium regression tests covering 45 workflows and reduced release defects by 30%.
        """
        evidence = find_keyword_evidence(resume, ["selenium", "python"])

        self.assertEqual(evidence["selenium"]["level"], "proven_with_metric")
        self.assertEqual(evidence["python"]["level"], "listed")

    def test_qa_domain_fallback_scores_non_oracle_job(self):
        resume = "QA Engineer with Selenium, API testing, Postman, regression testing, and Python."
        jd = """
        Required Qualifications
        Selenium test automation, API testing, regression testing, Python.
        Preferred: performance testing.
        """
        score, matched, missing = score_with_domain_bank(resume, jd, "QA Engineer", "qa_testing")

        self.assertGreater(score, 50)
        self.assertIn("selenium", matched)
        self.assertIn("performance testing", missing)

    def test_missing_unsupported_skill_is_learning_gap(self):
        resume = """
        Summary
        Data analyst with SQL and Tableau experience.
        Skills
        SQL, Tableau
        Experience
        Built Tableau dashboards for 12 finance users.
        """
        jd = """
        Requirements
        SQL, Tableau, Kubernetes.
        """
        result = evaluate_resume_fit(
            resume,
            jd,
            "Data Analyst",
            66.0,
            70,
            ["sql", "tableau"],
            ["kubernetes"],
            {"summary": True, "skills": True, "experience": True, "education": False},
        )

        learning_gap_keywords = {item["keyword"] for item in result["learning_gaps"]}
        safe_keywords = {item["keyword"] for item in result["safe_to_add"]}
        self.assertIn("kubernetes", learning_gap_keywords)
        self.assertNotIn("kubernetes", safe_keywords)


if __name__ == "__main__":
    unittest.main()
