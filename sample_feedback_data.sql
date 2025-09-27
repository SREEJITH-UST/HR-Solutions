-- Sample data for testing feedback functionality
-- Run this after creating migrations for the new models

-- First, create some sample users (managers)
INSERT INTO auth_user (username, first_name, last_name, email, is_staff, is_active, date_joined, password)
VALUES 
('manager1', 'John', 'Smith', 'john.smith@company.com', 0, 1, NOW(), 'pbkdf2_sha256$260000$test'),
('manager2', 'Sarah', 'Johnson', 'sarah.johnson@company.com', 0, 1, NOW(), 'pbkdf2_sha256$260000$test');

-- Create UserProfiles for managers
INSERT INTO hr_app_userprofile (user_id, user_type, country_code, mobile_number, profile_created_at, profile_updated_at, resume)
VALUES 
((SELECT id FROM auth_user WHERE username='manager1'), 'manager', '+91', '9876543210', NOW(), NOW(), ''),
((SELECT id FROM auth_user WHERE username='manager2'), 'manager', '+91', '9876543211', NOW(), NOW(), '');

-- Sample feedback data (adjust employee_id to match your actual user ID)
INSERT INTO hr_app_managerfeedback (employee_id, manager_id, subject, message, rating, areas_of_concern, created_at, updated_at)
VALUES 
(
    1, -- Replace with actual employee user ID
    (SELECT id FROM auth_user WHERE username='manager1'),
    'Performance Review - Q4 2024',
    'Great work on the recent project deliverables. However, there are some areas where we can improve communication and time management.',
    4,
    '["Communication", "Time Management", "Technical Documentation"]',
    NOW(),
    NOW()
),
(
    1, -- Replace with actual employee user ID  
    (SELECT id FROM auth_user WHERE username='manager2'),
    'Mid-year Performance Check',
    'Shows strong technical skills but needs improvement in presentation skills and stakeholder management.',
    3,
    '["Presentation Skills", "Stakeholder Management", "Leadership"]',
    DATE_SUB(NOW(), INTERVAL 30 DAY),
    DATE_SUB(NOW(), INTERVAL 30 DAY)
);

-- Sample recommended actions
INSERT INTO hr_app_feedbackaction (feedback_id, employee_id, title, description, priority, estimated_time_hours, is_completed, created_at)
VALUES 
(
    1, -- Feedback ID from above
    1, -- Employee user ID
    'Improve Daily Standup Communication',
    'Prepare structured updates for daily standups including what you worked on, current blockers, and next steps.',
    'high',
    2,
    0,
    NOW()
),
(
    1,
    1,
    'Complete Time Management Training',
    'Enroll in and complete the company time management course to better prioritize tasks and meet deadlines.',
    'medium',
    8,
    0,
    NOW()
),
(
    2,
    1,
    'Practice Presentation Skills',
    'Join the internal presentation club and practice presenting technical topics to non-technical audiences.',
    'high',
    5,
    0,
    NOW()
);

-- Sample course recommendations (requires existing courses in LearningCourse table)
-- You'll need to adjust course IDs based on your actual course data
INSERT INTO hr_app_feedbackcourserecommendation (feedback_id, employee_id, course_id, feedback_area_addressed, is_enrolled, created_at)
VALUES 
(
    1,
    1,
    1, -- Course ID - adjust based on your actual courses
    'Communication',
    0,
    NOW()
),
(
    1,
    1,
    2, -- Course ID - adjust based on your actual courses  
    'Time Management',
    0,
    NOW()
),
(
    2,
    1,
    3, -- Course ID - adjust based on your actual courses
    'Presentation Skills',
    1,
    NOW()
);

-- Sample learning courses (if you don't have any)
INSERT INTO hr_app_learningcourse (title, description, provider, course_url, duration_hours, difficulty_level, rating, price, skills_covered, created_at, updated_at)
VALUES 
(
    'Effective Communication for Tech Professionals',
    'Learn to communicate complex technical concepts clearly and effectively to diverse audiences.',
    'TechEd Pro',
    'https://example.com/comm-course',
    12,
    'beginner',
    4.5,
    49.99,
    '["Communication", "Public Speaking", "Technical Writing"]',
    NOW(),
    NOW()
),
(
    'Time Management and Productivity',
    'Master time management techniques specifically designed for software developers and technical professionals.',
    'ProductivityMax',
    'https://example.com/time-course',
    8,
    'intermediate',
    4.7,
    0.00,
    '["Time Management", "Productivity", "Planning"]',
    NOW(),
    NOW()
),
(
    'Presentation Skills for Technical Teams',
    'Build confidence in presenting technical information to stakeholders and team members.',
    'SpeakWell Academy',
    'https://example.com/presentation-course',
    15,
    'beginner',
    4.3,
    79.99,
    '["Presentation", "Public Speaking", "Stakeholder Management"]',
    NOW(),
    NOW()
);