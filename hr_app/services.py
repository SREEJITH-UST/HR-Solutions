import os
import json
import PyPDF2
import docx
from django.conf import settings
from .models import CandidateProfile
import openai
import re

class ResumeProcessingService:
    def __init__(self):
        # Initialize OpenAI with your API key from environment
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if self.openai_api_key:
            openai.api_key = self.openai_api_key
        else:
            print("Warning: OPENAI_API_KEY not found. Will use fallback analysis.")
    
    def extract_text_from_pdf(self, pdf_path):
        """Extract text from PDF file"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            raise Exception(f"Error reading PDF: {str(e)}")
    
    def extract_text_from_docx(self, docx_path):
        """Extract text from DOCX file"""
        try:
            doc = docx.Document(docx_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            raise Exception(f"Error reading DOCX: {str(e)}")
    
    def extract_text_from_resume(self, resume_file):
        """Extract text from resume file (PDF or DOCX)"""
        file_path = resume_file.path
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif file_extension in ['.docx', '.doc']:
            return self.extract_text_from_docx(file_path)
        else:
            raise Exception("Unsupported file format")
    
    def analyze_resume_with_ai(self, resume_text):
        """Analyze resume text using OpenAI API"""
        
        # Check if OpenAI is available
        if not self.openai_api_key:
            print("OpenAI API key not available, using fallback analysis")
            return self.fallback_analysis(resume_text)
        
        prompt = f"""
        Analyze the following resume and extract detailed information in JSON format. 
        Please be thorough and accurate in your analysis.

        Resume Text:
        {resume_text}

        Please extract and return the following information in valid JSON format:
        {{
            "personal_info": {{
                "name": "",
                "email": "",
                "phone": "",
                "location": ""
            }},
            "experience": {{
                "total_years": 0.0,
                "total_months": 0,
                "level": "fresher|junior|mid|senior|lead|principal",
                "current_role": "",
                "domain_experience": {{
                    "domain_name": "years_of_experience"
                }}
            }},
            "skills": {{
                "primary_skills": ["skill1", "skill2"],
                "secondary_skills": ["skill1", "skill2"],
                "soft_skills": ["skill1", "skill2"]
            }},
            "education": [
                {{
                    "degree": "",
                    "institution": "",
                    "year": "",
                    "grade": ""
                }}
            ],
            "certifications": [
                {{
                    "name": "",
                    "issuer": "",
                    "year": ""
                }}
            ],
            "projects": [
                {{
                    "name": "",
                    "description": "",
                    "technologies": ["tech1", "tech2"],
                    "duration": ""
                }}
            ],
            "career_preferences": {{
                "desired_roles": ["role1", "role2"],
                "current_salary": "",
                "expected_salary": "",
                "preferred_locations": ["location1", "location2"]
            }},
            "analysis": {{
                "resume_summary": "",
                "strengths": ["strength1", "strength2"],
                "areas_for_improvement": ["area1", "area2"],
                "resume_score": 85
            }}
        }}

        Make sure to:
        1. Calculate total experience accurately
        2. Categorize skills appropriately
        3. Extract all educational qualifications
        4. Identify key projects and technologies
        5. Provide a comprehensive analysis
        6. Give a realistic resume score (0-100)
        """

        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert HR analyst and resume parser. Extract information accurately and return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            result = response.choices[0].message.content
            print("[AI RAW RESUME ANALYSIS]", result)
            # Clean the response to ensure it's valid JSON
            result = result.strip()
            if result.startswith('```json'):
                result = result[7:]
            if result.endswith('```'):
                result = result[:-3]
            return json.loads(result)
            
        except Exception as e:
            # Fallback analysis if AI fails
            print(f"AI analysis failed: {str(e)}, using fallback analysis")
            return self.fallback_analysis(resume_text)
    
    def fallback_analysis(self, resume_text):
        """Enhanced fallback analysis using regex patterns"""
        
        # Extract skills more comprehensively
        skills = self.extract_skills(resume_text)
        primary_skills = skills[:8]  # First 8 as primary
        secondary_skills = skills[8:15] if len(skills) > 8 else []
        
        # Extract education information
        education = self.extract_education(resume_text)
        
        # Extract experience more accurately
        experience_years = self.estimate_experience(resume_text)
        
        # Determine experience level based on years
        level = self.determine_experience_level(experience_years)
        
        # Extract certifications
        certifications = self.extract_certifications(resume_text)
        
        # Extract domain experience
        domain_exp = self.extract_domain_experience(resume_text, experience_years)
        
        return {
            "personal_info": {
                "name": self.extract_name(resume_text),
                "email": self.extract_email(resume_text),
                "phone": self.extract_phone(resume_text),
                "location": self.extract_location(resume_text)
            },
            "experience": {
                "total_years": experience_years,
                "total_months": int(experience_years * 12),
                "level": level,
                "current_role": self.extract_current_role(resume_text),
                "domain_experience": domain_exp
            },
            "skills": {
                "primary_skills": primary_skills,
                "secondary_skills": secondary_skills,
                "soft_skills": self.extract_soft_skills(resume_text)
            },
            "education": education,
            "certifications": certifications,
            "projects": self.extract_projects(resume_text),
            "career_preferences": {
                "desired_roles": [],
                "current_salary": "",
                "expected_salary": "",
                "preferred_locations": []
            },
            "analysis": {
                "resume_summary": self.generate_resume_summary(resume_text, experience_years, primary_skills),
                "strengths": self.identify_strengths(resume_text, primary_skills, experience_years),
                "areas_for_improvement": self.suggest_improvements(resume_text, primary_skills),
                "resume_score": self.calculate_resume_score(resume_text, primary_skills, education, experience_years)
            }
        }
    
    def extract_email(self, text):
        """Extract email using regex"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        return emails[0] if emails else ""
    
    def extract_phone(self, text):
        """Extract phone number using regex"""
        phone_pattern = r'(\+91|91)?\s*[6-9]\d{9}'
        phones = re.findall(phone_pattern, text)
        return phones[0] if phones else ""
    
    def estimate_experience(self, text):
        """Estimate experience from text"""
        experience_patterns = [
            r'(\d+)\s*years?\s*(?:of\s*)?experience',
            r'experience\s*(?:of\s*)?(\d+)\s*years?',
            r'(\d+)\s*yrs?\s*experience'
        ]
        
        for pattern in experience_patterns:
            matches = re.findall(pattern, text.lower())
            if matches:
                return float(matches[0])
        
        return 2.0  # Default assumption
    
    def extract_skills(self, text):
        """Extract skills using common technology keywords"""
        common_skills = [
            'Python', 'Java', 'JavaScript', 'React', 'Angular', 'Node.js',
            'Django', 'Flask', 'Spring', 'HTML', 'CSS', 'SQL', 'MongoDB',
            'AWS', 'Azure', 'Docker', 'Kubernetes', 'Git', 'Jenkins',
            'Machine Learning', 'AI', 'Data Science', 'TensorFlow', 'PyTorch',
            'C++', 'C#', '.NET', 'PHP', 'Ruby', 'Go', 'Swift', 'Kotlin',
            'PostgreSQL', 'MySQL', 'Redis', 'Elasticsearch', 'GraphQL',
            'Microservices', 'REST API', 'DevOps', 'CI/CD', 'Agile',
            'Scrum', 'JIRA', 'Confluence', 'Linux', 'Unix', 'Windows'
        ]
        
        found_skills = []
        text_lower = text.lower()
        
        for skill in common_skills:
            if skill.lower() in text_lower:
                found_skills.append(skill)
        
        return found_skills
    
    def extract_name(self, text):
        """Extract name from resume text"""
        lines = text.split('\n')
        # Usually name is in the first few lines
        for line in lines[:5]:
            line = line.strip()
            # Skip common resume sections
            if any(keyword in line.lower() for keyword in ['resume', 'curriculum', 'cv', 'profile', 'summary', 'email', 'phone']):
                continue
            # Look for lines that might be names (2-4 words, mostly alphabetic)
            words = line.split()
            if 2 <= len(words) <= 4 and all(word.replace('.', '').isalpha() for word in words):
                return line
        return "Name not found"
    
    def extract_location(self, text):
        """Extract location information"""
        location_patterns = [
            r'(?:Address|Location|Based in|Located in)[:\s]*([A-Za-z\s,]+)',
            r'([A-Za-z\s]+,\s*[A-Za-z\s]+,\s*\d{6})',
            r'([A-Za-z\s]+,\s*India)',
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0].strip()
        return ""
    
    def extract_education(self, text):
        """Extract education information"""
        education = []
        education_keywords = ['bachelor', 'master', 'phd', 'diploma', 'degree', 'b.tech', 'm.tech', 'mba', 'bca', 'mca', 'engineering']
        
        lines = text.split('\n')
        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in education_keywords):
                # Try to extract degree, institution, and year
                degree = line.strip()
                institution = ""
                year = ""
                
                # Look for year patterns
                year_matches = re.findall(r'\b(19|20)\d{2}\b', line)
                if year_matches:
                    year = year_matches[-1]
                
                # Look for institution in nearby lines
                for j in range(max(0, i-2), min(len(lines), i+3)):
                    if 'university' in lines[j].lower() or 'college' in lines[j].lower() or 'institute' in lines[j].lower():
                        institution = lines[j].strip()
                        break
                
                education.append({
                    "degree": degree,
                    "institution": institution,
                    "year": year,
                    "grade": ""
                })
        
        return education[:3]  # Return top 3 education entries
    
    def extract_certifications(self, text):
        """Extract certifications"""
        certifications = []
        cert_keywords = ['certified', 'certification', 'certificate', 'aws', 'azure', 'google cloud', 'oracle', 'microsoft']
        
        lines = text.split('\n')
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in cert_keywords):
                # Extract year if present
                year_matches = re.findall(r'\b(19|20)\d{2}\b', line)
                year = year_matches[-1] if year_matches else ""
                
                certifications.append({
                    "name": line.strip(),
                    "issuer": "",
                    "year": year
                })
        
        return certifications[:5]  # Return top 5 certifications
    
    def extract_current_role(self, text):
        """Extract current job role"""
        role_patterns = [
            r'(?:Current Role|Position|Designation)[:\s]*([A-Za-z\s]+)',
            r'(?:Working as|Currently)[:\s]*([A-Za-z\s]+)',
        ]
        
        for pattern in role_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0].strip()
        
        # Look for common job titles at the beginning of lines
        job_titles = ['software engineer', 'developer', 'analyst', 'manager', 'consultant', 'architect', 'lead', 'senior']
        lines = text.split('\n')
        for line in lines[:20]:  # Check first 20 lines
            line_lower = line.lower()
            for title in job_titles:
                if title in line_lower:
                    return line.strip()
        
        return ""
    
    def extract_projects(self, text):
        """Extract project information"""
        projects = []
        project_keywords = ['project', 'developed', 'built', 'created', 'implemented']
        
        lines = text.split('\n')
        current_project = None
        
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in project_keywords):
                if current_project:
                    projects.append(current_project)
                
                current_project = {
                    "name": line.strip(),
                    "description": "",
                    "technologies": [],
                    "duration": ""
                }
        
        if current_project:
            projects.append(current_project)
        
        return projects[:3]  # Return top 3 projects
    
    def extract_soft_skills(self, text):
        """Extract soft skills"""
        soft_skills_list = ['communication', 'leadership', 'teamwork', 'problem solving', 'analytical', 'creative', 'adaptable', 'organized']
        found_soft_skills = []
        
        text_lower = text.lower()
        for skill in soft_skills_list:
            if skill in text_lower:
                found_soft_skills.append(skill.title())
        
        return found_soft_skills
    
    def determine_experience_level(self, years):
        """Determine experience level based on years"""
        if years <= 1:
            return 'fresher'
        elif years <= 3:
            return 'junior'
        elif years <= 5:
            return 'mid'
        elif years <= 8:
            return 'senior'
        elif years <= 12:
            return 'lead'
        else:
            return 'principal'
    
    def extract_domain_experience(self, text, total_years):
        """Extract domain-specific experience"""
        domains = {
            'Web Development': ['web', 'frontend', 'backend', 'fullstack'],
            'Mobile Development': ['mobile', 'android', 'ios', 'flutter', 'react native'],
            'Data Science': ['data science', 'machine learning', 'analytics', 'ai'],
            'DevOps': ['devops', 'deployment', 'ci/cd', 'kubernetes', 'docker'],
            'Cloud': ['aws', 'azure', 'cloud', 'gcp'],
            'Database': ['database', 'sql', 'mongodb', 'postgresql']
        }
        
        domain_exp = {}
        text_lower = text.lower()
        
        for domain, keywords in domains.items():
            if any(keyword in text_lower for keyword in keywords):
                # Assign proportional experience
                domain_exp[domain] = round(total_years * 0.7, 1)  # 70% of total experience
        
        return domain_exp
    
    def generate_resume_summary(self, text, experience_years, skills):
        """Generate a resume summary"""
        summary_parts = []
        
        if experience_years > 0:
            summary_parts.append(f"Professional with {experience_years} years of experience")
        
        if skills:
            summary_parts.append(f"skilled in {', '.join(skills[:3])}")
        
        summary_parts.append("seeking opportunities to contribute technical expertise and drive innovation")
        
        return ". ".join(summary_parts) + "."
    
    def identify_strengths(self, text, skills, experience_years):
        """Identify candidate strengths"""
        strengths = []
        
        if experience_years >= 3:
            strengths.append("Solid professional experience")
        
        if len(skills) >= 5:
            strengths.append("Diverse technical skill set")
        
        text_lower = text.lower()
        if 'project' in text_lower and 'lead' in text_lower:
            strengths.append("Project leadership experience")
        
        if any(keyword in text_lower for keyword in ['award', 'recognition', 'achievement']):
            strengths.append("Proven track record of achievements")
        
        if any(keyword in text_lower for keyword in ['team', 'collaboration', 'mentoring']):
            strengths.append("Strong teamwork and collaboration skills")
        
        return strengths[:5]
    
    def suggest_improvements(self, text, skills):
        """Suggest areas for improvement"""
        improvements = []
        
        text_lower = text.lower()
        
        if len(skills) < 5:
            improvements.append("Consider expanding technical skill set")
        
        if 'quantif' not in text_lower and 'metric' not in text_lower:
            improvements.append("Add quantifiable achievements and metrics")
        
        if 'certificate' not in text_lower and 'certification' not in text_lower:
            improvements.append("Consider adding relevant certifications")
        
        if 'project' not in text_lower:
            improvements.append("Include more project details")
        
        improvements.append("Enhance resume formatting and presentation")
        
        return improvements[:3]
    
    def calculate_resume_score(self, text, skills, education, experience_years):
        """Calculate resume score based on various factors"""
        score = 0
        
        # Base score
        score += 20
        
        # Experience points
        score += min(experience_years * 5, 25)
        
        # Skills points
        score += min(len(skills) * 2, 20)
        
        # Education points
        score += min(len(education) * 5, 15)
        
        # Content quality
        if len(text) > 500:
            score += 10
        
        # Keywords presence
        keywords = ['project', 'achievement', 'responsibility', 'accomplishment']
        keyword_count = sum(1 for keyword in keywords if keyword in text.lower())
        score += keyword_count * 2
        
        return min(score, 100)
    
    def process_resume(self, user_profile):
        """Main method to process resume and update candidate profile"""
        try:
            # Extract text from resume
            resume_text = self.extract_text_from_resume(user_profile.resume)
            
            # Analyze with AI
            analysis_result = self.analyze_resume_with_ai(resume_text)
            
            # Create or update candidate profile
            candidate_profile, created = CandidateProfile.objects.get_or_create(
                user_profile=user_profile
            )
            
            # Update candidate profile with extracted information
            self.update_candidate_profile(candidate_profile, analysis_result)
            
            # Mark as processed
            candidate_profile.resume_processed = True
            candidate_profile.processing_status = 'completed'
            candidate_profile.save()
            
            return candidate_profile
            
        except Exception as e:
            # Mark as failed
            candidate_profile = CandidateProfile.objects.get_or_create(
                user_profile=user_profile
            )[0]
            candidate_profile.processing_status = 'failed'
            candidate_profile.processing_error = str(e)
            candidate_profile.save()
            raise e
    
    def update_candidate_profile(self, candidate_profile, analysis_result):
        """Update candidate profile with analysis results"""
        exp = analysis_result.get('experience', {})
        skills = analysis_result.get('skills', {})
        education = analysis_result.get('education', [])
        certs = analysis_result.get('certifications', [])
        projects = analysis_result.get('projects', [])
        prefs = analysis_result.get('career_preferences', {})
        analysis = analysis_result.get('analysis', {})
        
        # Experience information
        candidate_profile.total_experience_years = exp.get('total_years', 0.0)
        candidate_profile.total_experience_months = exp.get('total_months', 0)
        candidate_profile.experience_level = exp.get('level', 'fresher')
        candidate_profile.current_role = exp.get('current_role', '')
        candidate_profile.domain_experience = exp.get('domain_experience', {})
        
        # Skills
        candidate_profile.primary_skills = skills.get('primary_skills', [])
        candidate_profile.secondary_skills = skills.get('secondary_skills', [])
        candidate_profile.soft_skills = skills.get('soft_skills', [])
        
        # Education and certifications
        candidate_profile.education_details = education
        candidate_profile.certifications = certs
        candidate_profile.notable_projects = projects
        
        # Career preferences
        candidate_profile.desired_roles = prefs.get('desired_roles', [])
        candidate_profile.current_salary = prefs.get('current_salary', '')
        candidate_profile.expected_salary = prefs.get('expected_salary', '')
        candidate_profile.preferred_locations = prefs.get('preferred_locations', [])
        
        # Analysis results
        candidate_profile.resume_summary = analysis.get('resume_summary', '')
        candidate_profile.strengths = analysis.get('strengths', [])
        candidate_profile.areas_for_improvement = analysis.get('areas_for_improvement', [])
        candidate_profile.resume_score = analysis.get('resume_score', 70)
        
        candidate_profile.save()