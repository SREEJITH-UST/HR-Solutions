# NextGenHR - Setup Guide

## Quick Setup Instructions

### 1. Database Setup
Run the following commands to set up the database:

```bash
python manage.py makemigrations
python manage.py migrate
```

### 2. Environment Configuration
1. Copy `.env.example` to `.env`
2. Update the following variables in `.env`:

**Email Configuration:**
- `EMAIL_HOST_USER`: Your Gmail address
- `EMAIL_HOST_PASSWORD`: Your Gmail app password (not regular password)

**OpenAI Configuration:**
- `OPENAI_API_KEY`: Your OpenAI API key for resume processing

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Create Superuser (Optional)
```bash
python manage.py createsuperuser
```

### 5. Run the Development Server
```bash
python manage.py runserver
```

## System Features

### 🎯 Comprehensive HR Solution
- **AI-Powered Resume Analysis**: Automatic skill extraction, experience mapping, and resume scoring
- **Role-Based Dashboards**: Separate interfaces for candidates, managers, and administrators
- **Real-Time Processing**: Background resume processing with live status updates
- **Advanced Validation**: Mobile number validation, password strength checking, email format validation

### 📊 Dashboard Features

**Candidate Dashboard:**
- Personal profile summary with AI-generated insights
- Resume score with improvement suggestions
- Skills breakdown (primary and secondary)
- Domain experience mapping
- Education and certifications tracking

**Manager Dashboard:**
- Team overview and candidate pool management
- Performance analytics and reporting
- Quick actions for interview scheduling
- Recent activity tracking

**Admin Dashboard:**
- Complete system overview and user management
- System health monitoring
- Analytics and reporting tools
- Maintenance and configuration options

### 🔧 Technical Architecture
- **Backend**: Django 5.2.6 with SQLite database
- **AI Integration**: OpenAI API for resume analysis
- **Document Processing**: PyPDF2 and python-docx for file parsing
- **Background Processing**: Threading for non-blocking operations
- **Security**: Environment-based configuration, role-based access

### 🚀 Getting Started
1. Complete the setup steps above
2. Visit `http://localhost:8000/signup/` to create your first account
3. Upload a resume during registration to see AI processing in action
4. Access role-specific dashboards based on user type

### 📝 User Types
- **Candidate**: Job seekers with resume analysis and profile management
- **Manager**: Team leads with candidate oversight and analytics
- **Admin**: System administrators with full access and control

### 🔄 Resume Processing Workflow
1. User uploads PDF/Word resume during signup
2. System extracts text from document
3. AI analyzes content for skills, experience, and insights
4. Results are structured and stored in the database
5. User receives comprehensive profile with actionable insights

For support or questions, contact the development team.