import unittest
import os
import shutil
from app import app, db, User, Resume, Analysis
from analyzer import analyze_resume_ats

class ATSAnalyzerTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        self.app_context = app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_analyzer_logic(self):
        sample_resume = """
        John Doe
        Email: john.doe@example.com | Phone: (555) 123-4567
        
        Professional Experience:
        Senior Full Stack Python Developer with 5 years experience.
        Proficient in Python, Flask, Django, SQL, PostgreSQL, HTML, CSS, JavaScript, React, Git, and Docker.
        
        Education:
        B.S. in Computer Science
        
        Projects:
        ATS Resume Analyzer App
        """
        
        sample_jd = """
        We are seeking a Senior Python Developer with expertise in Python, Flask, SQL, React, AWS, Docker, and Kubernetes.
        Must have strong problem solving skills and experience with REST APIs.
        """
        
        result = analyze_resume_ats(sample_resume, sample_jd, "Senior Python Developer")
        
        self.assertIn("Python", result['matched_skills'])
        self.assertIn("Flask", result['matched_skills'])
        self.assertIn("React", result['matched_skills'])
        self.assertIn("AWS", result['missing_skills'])
        self.assertGreaterEqual(result['overall_score'], 50)
        print("\n[TEST] ATS Analyzer Logic Test Passed!")
        print(f"Overall Score: {result['overall_score']}%, Matched: {result['matched_skills']}, Missing: {result['missing_skills']}")

    def test_user_registration_and_login(self):
        # Register user
        res = self.client.post('/register', data={
            'username': 'testuser',
            'email': 'testuser@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        
        user = User.query.filter_by(username='testuser').first()
        self.assertIsNotNone(user)
        self.assertTrue(user.check_password('password123'))
        
        # Login user
        res = self.client.post('/login', data={
            'email_or_user': 'testuser',
            'password': 'password123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Candidate Dashboard', res.data)
        print("[TEST] User Registration & Login Test Passed!")

if __name__ == '__main__':
    unittest.main()
