# HR Feedback Analysis & Course Assignment System
# Complete Python Implementation

import sqlite3
import re
import json
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict
import math

# Mock NLP libraries (in production, use spacy, transformers, etc.)
class MockNLPProcessor:
    """Mock NLP processor - replace with actual spacy/transformers in production"""
    
    def __init__(self):
        # Sample skill keywords mapping
        self.skill_keywords = {
            'communication': ['communication', 'speaking', 'presentation', 'writing', 'articulation', 'clarity'],
            'leadership': ['leadership', 'managing', 'delegation', 'motivation', 'guidance', 'mentoring'],
            'time_management': ['deadline', 'punctuality', 'scheduling', 'prioritization', 'organization'],
            'teamwork': ['collaboration', 'cooperation', 'team', 'working together', 'partnership'],
            'technical': ['programming', 'coding', 'development', 'technical', 'software', 'system'],
            'problem_solving': ['problem solving', 'analytical', 'critical thinking', 'troubleshooting'],
            'adaptability': ['adaptability', 'flexibility', 'change', 'learning', 'adjustment'],
            'quality': ['quality', 'attention to detail', 'accuracy', 'precision', 'standards']
        }
        
        # Negative sentiment indicators
        self.negative_indicators = [
            'poor', 'bad', 'terrible', 'awful', 'struggling', 'difficulty', 'problem',
            'issue', 'concern', 'disappointing', 'unsatisfactory', 'below expectations',
            'needs improvement', 'lacking', 'weak', 'insufficient', 'missed', 'late',
            'failed', 'unable', 'cannot', 'difficult', 'challenge', 'conflict'
        ]
        
        # Positive sentiment indicators
        self.positive_indicators = [
            'excellent', 'outstanding', 'great', 'good', 'strong', 'impressive',
            'effective', 'successful', 'exceeded', 'improved', 'skilled', 'talented',
            'proficient', 'capable', 'reliable', 'consistent', 'innovative', 'creative'
        ]
    
    def analyze_sentiment(self, text: str) -> Dict:
        """Analyze sentiment of text"""
        text_lower = text.lower()
        
        positive_count = sum(1 for word in self.positive_indicators if word in text_lower)
        negative_count = sum(1 for word in self.negative_indicators if word in text_lower)
        
        total_words = len(text.split())
        
        # Calculate sentiment score (-1 to 1)
        if total_words > 0:
            sentiment_score = (positive_count - negative_count) / max(total_words / 10, 1)
            sentiment_score = max(-1, min(1, sentiment_score))
        else:
            sentiment_score = 0
        
        # Determine sentiment label
        if sentiment_score > 0.1:
            sentiment_label = "POSITIVE"
        elif sentiment_score < -0.1:
            sentiment_label = "NEGATIVE"
        else:
            sentiment_label = "NEUTRAL"
        
        confidence = min(0.95, abs(sentiment_score) + 0.5)
        
        return {
            'score': sentiment_score,
            'label': sentiment_label,
            'confidence': confidence
        }
    
    def extract_keywords(self, text: str) -> List[Dict]:
        """Extract skill-related keywords from text"""
        text_lower = text.lower()
        extracted_keywords = []
        
        for skill_category, keywords in self.skill_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    # Calculate confidence based on exact match and context
                    confidence = 0.8 if keyword in text_lower else 0.6
                    extracted_keywords.append({
                        'keyword': keyword,
                        'category': skill_category,
                        'confidence': confidence
                    })
        
        return extracted_keywords

# Data Models
@dataclass
class Employee:
    id: int
    name: str
    role: str
    department: str
    manager_id: Optional[int] = None

@dataclass
class Course:
    id: int
    title: str
    description: str
    category: str
    duration: int  # in hours
    difficulty: str  # Easy, Medium, Hard
    skills_addressed: List[str]

@dataclass
class Feedback:
    id: int
    employee_id: int
    manager_id: int
    content: str
    category: str
    timestamp: str
    priority: str = "Medium"

@dataclass
class FeedbackAnalysis:
    feedback_id: int
    sentiment_score: float
    sentiment_label: str
    confidence: float
    keywords: List[Dict]
    skill_gaps: List[str]

@dataclass
class CourseRecommendation:
    id: int
    feedback_id: int
    course_id: int
    relevance_score: float
    urgency_score: float
    explanation: str
    status: str = "pending"

# Database Manager
class DatabaseManager:
    def __init__(self, db_path: str = "hr_system.db"):
        self.db_path = db_path
        self.init_database()
        self.populate_sample_data()
    
    def init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                department TEXT NOT NULL,
                manager_id INTEGER,
                FOREIGN KEY (manager_id) REFERENCES employees (id)
            );
            
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                category TEXT NOT NULL,
                duration INTEGER,
                difficulty TEXT,
                skills_addressed TEXT
            );
            
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY,
                employee_id INTEGER NOT NULL,
                manager_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                category TEXT,
                timestamp TEXT,
                priority TEXT,
                FOREIGN KEY (employee_id) REFERENCES employees (id),
                FOREIGN KEY (manager_id) REFERENCES employees (id)
            );
            
            CREATE TABLE IF NOT EXISTS feedback_analysis (
                id INTEGER PRIMARY KEY,
                feedback_id INTEGER NOT NULL,
                sentiment_score REAL,
                sentiment_label TEXT,
                confidence REAL,
                keywords TEXT,
                skill_gaps TEXT,
                FOREIGN KEY (feedback_id) REFERENCES feedback (id)
            );
            
            CREATE TABLE IF NOT EXISTS recommendations (
                id INTEGER PRIMARY KEY,
                feedback_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                relevance_score REAL,
                urgency_score REAL,
                explanation TEXT,
                status TEXT,
                created_at TEXT,
                FOREIGN KEY (feedback_id) REFERENCES feedback (id),
                FOREIGN KEY (course_id) REFERENCES courses (id)
            );
            
            CREATE TABLE IF NOT EXISTS enrollments (
                id INTEGER PRIMARY KEY,
                employee_id INTEGER NOT NULL,
                course_id INTEGER NOT NULL,
                status TEXT,
                enrolled_at TEXT,
                completion_date TEXT,
                FOREIGN KEY (employee_id) REFERENCES employees (id),
                FOREIGN KEY (course_id) REFERENCES courses (id)
            );
        """)
        
        conn.commit()
        conn.close()
    
    def populate_sample_data(self):
        """Populate database with sample data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if data already exists
        cursor.execute("SELECT COUNT(*) FROM employees")
        if cursor.fetchone()[0] > 0:
            conn.close()
            return
        
        # Sample employees
        employees = [
            (1, "John Manager", "Engineering Manager", "Engineering", None),
            (2, "Alice Developer", "Software Developer", "Engineering", 1),
            (3, "Bob Analyst", "Data Analyst", "Analytics", 1),
            (4, "Carol Designer", "UX Designer", "Design", 1),
            (5, "David Tester", "QA Engineer", "Engineering", 1)
        ]
        
        # Sample courses
        courses = [
            (1, "Effective Communication Skills", "Master verbal and written communication", "Soft Skills", 8, "Easy", "communication,presentation"),
            (2, "Leadership Fundamentals", "Basic leadership and management skills", "Leadership", 12, "Medium", "leadership,management"),
            (3, "Time Management Mastery", "Improve productivity and deadline management", "Productivity", 6, "Easy", "time_management,organization"),
            (4, "Advanced Python Programming", "Deep dive into Python development", "Technical", 24, "Hard", "technical,programming"),
            (5, "Team Collaboration Workshop", "Enhance teamwork and collaboration", "Soft Skills", 4, "Easy", "teamwork,collaboration"),
            (6, "Problem Solving Techniques", "Analytical thinking and problem resolution", "Skills", 10, "Medium", "problem_solving,analytical"),
            (7, "Agile Project Management", "Learn agile methodologies and practices", "Management", 16, "Medium", "project_management,agile"),
            (8, "Quality Assurance Best Practices", "Improve testing and quality processes", "Technical", 14, "Medium", "quality,testing"),
            (9, "Conflict Resolution", "Handle workplace conflicts effectively", "Soft Skills", 8, "Medium", "communication,leadership"),
            (10, "Data Analysis with Python", "Statistical analysis and data science", "Technical", 20, "Hard", "technical,analytical")
        ]
        
        cursor.executemany("INSERT INTO employees VALUES (?, ?, ?, ?, ?)", employees)
        cursor.executemany("INSERT INTO courses VALUES (?, ?, ?, ?, ?, ?, ?)", courses)
        
        conn.commit()
        conn.close()

# Feedback Analyzer
class FeedbackAnalyzer:
    def __init__(self):
        self.nlp_processor = MockNLPProcessor()
        self.db = DatabaseManager()
    
    def analyze_feedback(self, feedback_text: str) -> Dict:
        """Complete feedback analysis pipeline"""
        # Preprocessing
        cleaned_text = self._preprocess_text(feedback_text)
        
        # Sentiment Analysis
        sentiment_result = self.nlp_processor.analyze_sentiment(cleaned_text)
        
        # Keyword Extraction
        keywords = self.nlp_processor.extract_keywords(cleaned_text)
        
        # Skill Gap Identification
        skill_gaps = self._identify_skill_gaps(keywords, sentiment_result)
        
        return {
            'sentiment': sentiment_result,
            'keywords': keywords,
            'skill_gaps': skill_gaps,
            'processed_text': cleaned_text
        }
    
    def _preprocess_text(self, text: str) -> str:
        """Clean and preprocess text"""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s\.,!?-]', '', text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def _identify_skill_gaps(self, keywords: List[Dict], sentiment: Dict) -> List[str]:
        """Identify skill gaps based on keywords and sentiment"""
        skill_gaps = []
        
        # If sentiment is negative, skills mentioned are likely gaps
        if sentiment['label'] == 'NEGATIVE':
            skill_categories = set()
            for keyword in keywords:
                skill_categories.add(keyword['category'])
            skill_gaps.extend(list(skill_categories))
        
        return skill_gaps

# Course Recommendation Engine
class CourseRecommendationEngine:
    def __init__(self):
        self.db = DatabaseManager()
        self.analyzer = FeedbackAnalyzer()
        
        # Rule-based scoring weights
        self.weights = {
            'relevance': 0.4,
            'urgency': 0.3,
            'difficulty_match': 0.2,
            'popularity': 0.1
        }
    
    def recommend_courses(self, feedback_id: int, employee_id: int, analysis: Dict) -> List[CourseRecommendation]:
        """Generate course recommendations based on feedback analysis"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        # Get all available courses
        cursor.execute("SELECT * FROM courses")
        courses = cursor.fetchall()
        
        recommendations = []
        
        for course in courses:
            course_id, title, description, category, duration, difficulty, skills_str = course
            course_skills = skills_str.split(',') if skills_str else []
            
            # Calculate recommendation scores
            relevance_score = self._calculate_relevance_score(analysis, course_skills, category)
            urgency_score = self._calculate_urgency_score(analysis)
            
            # Combined score
            total_score = (relevance_score * self.weights['relevance'] + 
                          urgency_score * self.weights['urgency'])
            
            # Only recommend if score is above threshold
            if total_score > 0.3:
                explanation = self._generate_explanation(analysis, title, relevance_score)
                
                recommendation = CourseRecommendation(
                    id=len(recommendations) + 1,
                    feedback_id=feedback_id,
                    course_id=course_id,
                    relevance_score=relevance_score,
                    urgency_score=urgency_score,
                    explanation=explanation
                )
                recommendations.append(recommendation)
        
        # Sort by total score (relevance + urgency)
        recommendations.sort(key=lambda x: x.relevance_score + x.urgency_score, reverse=True)
        
        conn.close()
        return recommendations[:5]  # Return top 5 recommendations
    
    def _calculate_relevance_score(self, analysis: Dict, course_skills: List[str], category: str) -> float:
        """Calculate how relevant a course is to the feedback"""
        skill_gaps = analysis.get('skill_gaps', [])
        keywords = analysis.get('keywords', [])
        
        score = 0.0
        
        # Direct skill gap matching
        for gap in skill_gaps:
            if gap in course_skills:
                score += 0.4
        
        # Keyword matching
        for keyword_data in keywords:
            if keyword_data['category'] in course_skills:
                score += keyword_data['confidence'] * 0.3
        
        # Category matching with sentiment
        sentiment = analysis.get('sentiment', {})
        if sentiment.get('label') == 'NEGATIVE':
            # Boost score for relevant categories when sentiment is negative
            relevant_categories = ['Soft Skills', 'Skills', 'Leadership', 'Management']
            if category in relevant_categories:
                score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_urgency_score(self, analysis: Dict) -> float:
        """Calculate urgency based on sentiment severity"""
        sentiment = analysis.get('sentiment', {})
        sentiment_score = sentiment.get('score', 0)
        
        # More negative sentiment = higher urgency
        if sentiment_score < -0.5:
            return 0.9
        elif sentiment_score < -0.2:
            return 0.6
        elif sentiment_score < 0:
            return 0.4
        else:
            return 0.2
    
    def _generate_explanation(self, analysis: Dict, course_title: str, relevance_score: float) -> str:
        """Generate explanation for why course is recommended"""
        sentiment = analysis.get('sentiment', {})
        skill_gaps = analysis.get('skill_gaps', [])
        
        if sentiment.get('label') == 'NEGATIVE' and skill_gaps:
            return f"Recommended due to identified gaps in {', '.join(skill_gaps)} based on feedback analysis."
        elif relevance_score > 0.7:
            return f"Highly relevant to address concerns mentioned in the feedback."
        else:
            return f"May help improve overall performance based on feedback themes."

# Main HR System
class HRFeedbackSystem:
    def __init__(self):
        self.db = DatabaseManager()
        self.analyzer = FeedbackAnalyzer()
        self.recommender = CourseRecommendationEngine()
    
    def submit_feedback(self, employee_id: int, manager_id: int, content: str, 
                       category: str = "General", priority: str = "Medium") -> int:
        """Submit new feedback"""
        if len(content) < 50:
            raise ValueError("Feedback must be at least 50 characters long")
        
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO feedback (employee_id, manager_id, content, category, timestamp, priority)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (employee_id, manager_id, content, category, timestamp, priority))
        
        feedback_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Automatically analyze feedback
        self.analyze_and_recommend(feedback_id)
        
        return feedback_id
    
    def analyze_and_recommend(self, feedback_id: int) -> Dict:
        """Analyze feedback and generate recommendations"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        # Get feedback
        cursor.execute("SELECT * FROM feedback WHERE id = ?", (feedback_id,))
        feedback_data = cursor.fetchone()
        
        if not feedback_data:
            raise ValueError("Feedback not found")
        
        _, employee_id, manager_id, content, category, timestamp, priority = feedback_data
        
        # Analyze feedback
        analysis = self.analyzer.analyze_feedback(content)
        
        # Save analysis
        cursor.execute("""
            INSERT INTO feedback_analysis 
            (feedback_id, sentiment_score, sentiment_label, confidence, keywords, skill_gaps)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            feedback_id,
            analysis['sentiment']['score'],
            analysis['sentiment']['label'],
            analysis['sentiment']['confidence'],
            json.dumps(analysis['keywords']),
            json.dumps(analysis['skill_gaps'])
        ))
        
        # Generate recommendations
        recommendations = self.recommender.recommend_courses(feedback_id, employee_id, analysis)
        
        # Save recommendations
        for rec in recommendations:
            cursor.execute("""
                INSERT INTO recommendations 
                (feedback_id, course_id, relevance_score, urgency_score, explanation, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                rec.feedback_id, rec.course_id, rec.relevance_score, 
                rec.urgency_score, rec.explanation, rec.status,
                datetime.now().isoformat()
            ))
        
        conn.commit()
        conn.close()
        
        return {
            'feedback_id': feedback_id,
            'analysis': analysis,
            'recommendations': [asdict(rec) for rec in recommendations]
        }
    
    def get_employee_recommendations(self, employee_id: int) -> List[Dict]:
        """Get all recommendations for an employee"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT r.*, c.title, c.description, c.duration, c.difficulty, 
                   f.content as feedback_content, f.timestamp
            FROM recommendations r
            JOIN courses c ON r.course_id = c.id
            JOIN feedback f ON r.feedback_id = f.id
            WHERE f.employee_id = ?
            ORDER BY r.relevance_score + r.urgency_score DESC
        """, (employee_id,))
        
        recommendations = []
        for row in cursor.fetchall():
            recommendations.append({
                'recommendation_id': row[0],
                'course_id': row[2],
                'course_title': row[7],
                'course_description': row[8],
                'duration': row[9],
                'difficulty': row[10],
                'relevance_score': row[3],
                'urgency_score': row[4],
                'explanation': row[5],
                'status': row[6],
                'feedback_content': row[11],
                'feedback_date': row[12]
            })
        
        conn.close()
        return recommendations
    
    def enroll_in_course(self, employee_id: int, course_id: int) -> int:
        """Enroll employee in a course"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO enrollments (employee_id, course_id, status, enrolled_at)
            VALUES (?, ?, 'enrolled', ?)
        """, (employee_id, course_id, datetime.now().isoformat()))
        
        enrollment_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return enrollment_id
    
    def get_analytics_dashboard(self) -> Dict:
        """Get system analytics and metrics"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        # Basic counts
        cursor.execute("SELECT COUNT(*) FROM feedback")
        total_feedback = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM recommendations")
        total_recommendations = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM enrollments")
        total_enrollments = cursor.fetchone()[0]
        
        # Sentiment analysis
        cursor.execute("""
            SELECT sentiment_label, COUNT(*) 
            FROM feedback_analysis 
            GROUP BY sentiment_label
        """)
        sentiment_breakdown = dict(cursor.fetchall())
        
        # Top skill gaps
        cursor.execute("SELECT skill_gaps FROM feedback_analysis WHERE skill_gaps != '[]'")
        skill_gaps_data = cursor.fetchall()
        skill_gap_counts = defaultdict(int)
        
        for row in skill_gaps_data:
            gaps = json.loads(row[0])
            for gap in gaps:
                skill_gap_counts[gap] += 1
        
        conn.close()
        
        return {
            'total_feedback': total_feedback,
            'total_recommendations': total_recommendations,
            'total_enrollments': total_enrollments,
            'sentiment_breakdown': sentiment_breakdown,
            'top_skill_gaps': dict(sorted(skill_gap_counts.items(), 
                                        key=lambda x: x[1], reverse=True)[:10])
        }

# Demo and Testing
def run_demo():
    """Run a complete demo of the system"""
    print("🚀 HR Feedback Analysis & Course Assignment System Demo")
    print("=" * 60)
    
    # Initialize system
    hr_system = HRFeedbackSystem()
    
    # Sample feedback scenarios
    feedback_scenarios = [
        {
            'employee_id': 2,
            'manager_id': 1,
            'content': "Alice has been struggling with communication during team meetings. She often fails to articulate her ideas clearly and seems to have difficulty presenting her work to stakeholders. Her technical skills are strong, but the communication issues are affecting team collaboration.",
            'category': 'Performance Review'
        },
        {
            'employee_id': 3,
            'manager_id': 1,
            'content': "Bob consistently misses deadlines and seems to have poor time management skills. His work quality is good when completed, but the lack of punctuality is becoming a serious concern. He needs better organization and prioritization techniques.",
            'category': 'Incident Report'
        },
        {
            'employee_id': 4,
            'manager_id': 1,
            'content': "Carol is doing excellent work and shows great creativity in her designs. She collaborates well with the team and always delivers high-quality results on time. Her leadership potential is evident.",
            'category': 'Performance Review'
        }
    ]
    
    print("\n📝 Submitting Sample Feedback...")
    for i, scenario in enumerate(feedback_scenarios, 1):
        print(f"\nScenario {i}:")
        print(f"Employee: {scenario['employee_id']}")
        print(f"Feedback: {scenario['content'][:100]}...")
        
        feedback_id = hr_system.submit_feedback(**scenario)
        print(f"✅ Feedback submitted with ID: {feedback_id}")
    
    print("\n" + "=" * 60)
    print("📊 Analysis Results for Employee 2 (Alice - Communication Issues):")
    
    # Get recommendations for Alice
    recommendations = hr_system.get_employee_recommendations(2)
    
    if recommendations:
        print(f"\n🎯 Found {len(recommendations)} course recommendations:")
        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. {rec['course_title']}")
            print(f"   📚 Duration: {rec['duration']} hours")
            print(f"   🎚️  Difficulty: {rec['difficulty']}")
            print(f"   📈 Relevance Score: {rec['relevance_score']:.2f}")
            print(f"   ⚡ Urgency Score: {rec['urgency_score']:.2f}")
            print(f"   💡 Explanation: {rec['explanation']}")
    
    print("\n" + "=" * 60)
    print("📊 System Analytics Dashboard:")
    
    analytics = hr_system.get_analytics_dashboard()
    
    print(f"📈 Total Feedback: {analytics['total_feedback']}")
    print(f"🎯 Total Recommendations: {analytics['total_recommendations']}")
    print(f"📚 Total Enrollments: {analytics['total_enrollments']}")
    
    print(f"\n😊 Sentiment Breakdown:")
    for sentiment, count in analytics['sentiment_breakdown'].items():
        print(f"   {sentiment}: {count}")
    
    print(f"\n🔍 Top Skill Gaps Identified:")
    for skill, count in list(analytics['top_skill_gaps'].items())[:5]:
        print(f"   {skill.replace('_', ' ').title()}: {count}")
    
    print("\n" + "=" * 60)
    print("✨ Demo completed successfully!")
    print("\nThe system has:")
    print("✅ Analyzed manager feedback using NLP")
    print("✅ Identified skill gaps and sentiment")
    print("✅ Recommended relevant courses")
    print("✅ Provided analytics and insights")
    print("\nReady for integration into your HR platform! 🎉")

if __name__ == "__main__":
    run_demo()