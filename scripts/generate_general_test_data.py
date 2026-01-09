#!/usr/bin/env python3
"""
Generate test data for General IT/Business Resume Matching System.

Creates:
- 100 generalized IT and Business professional resumes with varying experience levels
- 30 job descriptions for IT, marketing, business analysis, managers, directors, VPs
"""

import json
import random
import os
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# =============================================================================
# RESUME DATA POOLS
# =============================================================================

FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
    "Kenneth", "Dorothy", "Kevin", "Carol", "Brian", "Amanda", "George", "Melissa",
    "Timothy", "Deborah", "Ronald", "Stephanie", "Edward", "Rebecca", "Jason", "Sharon",
    "Jeffrey", "Laura", "Ryan", "Cynthia", "Jacob", "Kathleen", "Gary", "Amy",
    "Nicholas", "Angela", "Eric", "Shirley", "Jonathan", "Anna", "Stephen", "Brenda",
    "Larry", "Pamela", "Justin", "Emma", "Scott", "Nicole", "Brandon", "Helen",
    "Benjamin", "Samantha", "Samuel", "Katherine", "Raymond", "Christine", "Gregory", "Debra",
    "Frank", "Rachel", "Alexander", "Carolyn", "Patrick", "Janet"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas",
    "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson", "White",
    "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker", "Young",
    "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts", "Patel", "Chen", "Kim", "Park", "Wong", "Zhang",
    "Singh", "Kumar", "Sharma", "Gupta", "Shah", "O'Brien", "Murphy", "Kelly"
]

# Experience levels with characteristics
EXPERIENCE_LEVELS = {
    "beginner": {
        "years_range": (0, 2),
        "title_prefixes": ["Junior ", "Associate ", "Entry-Level ", ""],
        "skill_count": (5, 8),
        "cert_count": (0, 2),
        "achievement_scale": "small"
    },
    "intermediate": {
        "years_range": (3, 5),
        "title_prefixes": ["", "Mid-Level "],
        "skill_count": (8, 12),
        "cert_count": (1, 3),
        "achievement_scale": "medium"
    },
    "advanced": {
        "years_range": (6, 10),
        "title_prefixes": ["Senior ", "Lead ", "Staff "],
        "skill_count": (12, 18),
        "cert_count": (2, 5),
        "achievement_scale": "large"
    },
    "expert": {
        "years_range": (11, 20),
        "title_prefixes": ["Principal ", "Senior ", "Lead ", "Staff "],
        "skill_count": (15, 25),
        "cert_count": (3, 7),
        "achievement_scale": "enterprise"
    }
}

# =============================================================================
# IT SKILLS AND TECHNOLOGIES
# =============================================================================

PROGRAMMING_LANGUAGES = [
    "Python", "JavaScript", "TypeScript", "Java", "C#", "C++", "Go", "Rust",
    "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R", "MATLAB", "SQL", "Bash"
]

FRAMEWORKS_LIBRARIES = [
    "React", "Angular", "Vue.js", "Node.js", "Django", "Flask", "Spring Boot",
    ".NET Core", "Express.js", "FastAPI", "Ruby on Rails", "Laravel", "Next.js",
    "TensorFlow", "PyTorch", "Pandas", "NumPy", "Scikit-learn", "Keras"
]

CLOUD_PLATFORMS = [
    "AWS", "Azure", "Google Cloud Platform", "Heroku", "DigitalOcean",
    "AWS Lambda", "Azure Functions", "Google Cloud Functions", "Kubernetes",
    "Docker", "Terraform", "CloudFormation", "Ansible", "Jenkins", "GitLab CI/CD"
]

DATABASES = [
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "Oracle",
    "SQL Server", "DynamoDB", "Cassandra", "Neo4j", "SQLite", "MariaDB"
]

IT_TOOLS = [
    "Git", "GitHub", "GitLab", "Bitbucket", "Jira", "Confluence", "Slack",
    "VS Code", "IntelliJ IDEA", "Postman", "Figma", "Adobe XD", "Sketch",
    "Splunk", "Datadog", "New Relic", "Grafana", "Prometheus", "ELK Stack"
]

DATA_SKILLS = [
    "Data Analysis", "Data Visualization", "ETL", "Data Warehousing",
    "Business Intelligence", "Tableau", "Power BI", "Looker", "Qlik",
    "Apache Spark", "Hadoop", "Airflow", "dbt", "Snowflake", "Databricks"
]

# =============================================================================
# BUSINESS SKILLS
# =============================================================================

BUSINESS_SKILLS = [
    "Project Management", "Agile Methodology", "Scrum", "Kanban", "Waterfall",
    "Business Analysis", "Requirements Gathering", "Stakeholder Management",
    "Strategic Planning", "Budget Management", "Resource Planning", "Risk Management",
    "Process Improvement", "Change Management", "Vendor Management", "Contract Negotiation",
    "Team Leadership", "Cross-functional Collaboration", "Executive Communication",
    "KPI Development", "Performance Metrics", "ROI Analysis", "Cost-Benefit Analysis"
]

MARKETING_SKILLS = [
    "Digital Marketing", "SEO", "SEM", "PPC Advertising", "Social Media Marketing",
    "Content Marketing", "Email Marketing", "Marketing Automation", "CRM Management",
    "Google Analytics", "HubSpot", "Salesforce Marketing Cloud", "Marketo",
    "Brand Management", "Market Research", "Competitive Analysis", "Campaign Management",
    "Lead Generation", "Conversion Optimization", "A/B Testing", "Customer Segmentation"
]

SOFT_SKILLS = [
    "Communication", "Leadership", "Problem Solving", "Critical Thinking",
    "Teamwork", "Adaptability", "Time Management", "Attention to Detail",
    "Presentation Skills", "Negotiation", "Conflict Resolution", "Mentoring",
    "Decision Making", "Creativity", "Emotional Intelligence", "Active Listening"
]

# =============================================================================
# CERTIFICATIONS
# =============================================================================

IT_CERTIFICATIONS = [
    "AWS Certified Solutions Architect - Associate",
    "AWS Certified Solutions Architect - Professional",
    "AWS Certified Developer - Associate",
    "Azure Administrator Associate",
    "Azure Solutions Architect Expert",
    "Google Cloud Professional Cloud Architect",
    "Certified Kubernetes Administrator (CKA)",
    "Certified Information Systems Security Professional (CISSP)",
    "CompTIA Security+",
    "CompTIA Network+",
    "CompTIA A+",
    "Cisco Certified Network Associate (CCNA)",
    "Oracle Certified Professional",
    "Microsoft Certified: Azure Developer Associate",
    "HashiCorp Certified: Terraform Associate",
    "Certified ScrumMaster (CSM)",
    "Professional Scrum Master (PSM I)",
    "ITIL Foundation",
    "PMP (Project Management Professional)"
]

BUSINESS_CERTIFICATIONS = [
    "PMP (Project Management Professional)",
    "Certified Business Analysis Professional (CBAP)",
    "Six Sigma Green Belt",
    "Six Sigma Black Belt",
    "Lean Six Sigma Certification",
    "Certified Scrum Product Owner (CSPO)",
    "SAFe Agilist Certification",
    "PRINCE2 Foundation",
    "PRINCE2 Practitioner",
    "Certified Management Consultant (CMC)",
    "Certified Financial Analyst (CFA)",
    "Google Analytics Certification",
    "HubSpot Inbound Marketing Certification",
    "Salesforce Administrator Certification",
    "Certified Digital Marketing Professional"
]

# =============================================================================
# COMPANIES AND INDUSTRIES
# =============================================================================

TECH_COMPANIES = [
    "Google", "Microsoft", "Amazon", "Apple", "Meta", "Netflix", "Salesforce",
    "Adobe", "Oracle", "IBM", "Cisco", "Intel", "NVIDIA", "VMware", "ServiceNow",
    "Workday", "Splunk", "Atlassian", "Twilio", "Stripe", "Square", "Shopify",
    "Zoom", "Slack", "Dropbox", "DocuSign", "Cloudflare", "Datadog", "MongoDB"
]

CONSULTING_FIRMS = [
    "Deloitte", "McKinsey & Company", "Boston Consulting Group", "Bain & Company",
    "Accenture", "PwC", "EY", "KPMG", "Capgemini", "Cognizant", "Infosys",
    "Wipro", "Tata Consultancy Services", "HCL Technologies", "Tech Mahindra"
]

FORTUNE_500 = [
    "Walmart", "ExxonMobil", "Berkshire Hathaway", "UnitedHealth Group", "CVS Health",
    "General Motors", "Ford Motor", "AT&T", "Verizon", "JPMorgan Chase",
    "Bank of America", "Citigroup", "Wells Fargo", "Goldman Sachs", "Morgan Stanley",
    "Procter & Gamble", "Johnson & Johnson", "Pfizer", "Merck", "AbbVie",
    "Target", "Home Depot", "Lowe's", "Costco", "Kroger", "Walgreens"
]

STARTUPS = [
    "TechVenture Labs", "InnovateCo", "DataDriven Inc", "CloudFirst Solutions",
    "AI Dynamics", "NextGen Software", "Digital Horizons", "Agile Systems",
    "Smart Analytics", "Rapid Growth Tech", "Disrupt Technologies", "Scale Up Inc",
    "Future Forward", "Tech Pioneers", "Innovation Hub", "Growth Engine"
]

UNIVERSITIES = [
    "MIT", "Stanford University", "Harvard University", "UC Berkeley",
    "Carnegie Mellon University", "Georgia Tech", "University of Michigan",
    "University of Texas at Austin", "University of Illinois", "Purdue University",
    "Cornell University", "Columbia University", "UCLA", "University of Washington",
    "Northwestern University", "Duke University", "University of Pennsylvania",
    "New York University", "Boston University", "University of Southern California",
    "University of Wisconsin", "Ohio State University", "Penn State University",
    "Arizona State University", "University of Florida", "University of Colorado"
]

# =============================================================================
# JOB TITLES BY CATEGORY
# =============================================================================

IT_TITLES = {
    "development": [
        "Software Engineer", "Software Developer", "Full Stack Developer",
        "Backend Developer", "Frontend Developer", "Mobile Developer",
        "DevOps Engineer", "Site Reliability Engineer", "Platform Engineer",
        "Data Engineer", "Machine Learning Engineer", "AI Engineer"
    ],
    "infrastructure": [
        "Systems Administrator", "Network Engineer", "Cloud Engineer",
        "Security Engineer", "Database Administrator", "IT Support Specialist",
        "Infrastructure Engineer", "Solutions Architect", "Technical Architect"
    ],
    "data": [
        "Data Analyst", "Data Scientist", "Business Intelligence Analyst",
        "Data Architect", "Analytics Engineer", "Quantitative Analyst"
    ],
    "product": [
        "Product Manager", "Technical Product Manager", "Product Owner",
        "Program Manager", "Technical Program Manager", "Scrum Master"
    ]
}

BUSINESS_TITLES = {
    "analysis": [
        "Business Analyst", "Systems Analyst", "Process Analyst",
        "Operations Analyst", "Strategy Analyst", "Financial Analyst"
    ],
    "marketing": [
        "Marketing Manager", "Digital Marketing Specialist", "Content Strategist",
        "SEO Specialist", "Marketing Analyst", "Brand Manager",
        "Social Media Manager", "Growth Marketing Manager", "Product Marketing Manager"
    ],
    "management": [
        "Project Manager", "Operations Manager", "Account Manager",
        "Customer Success Manager", "Delivery Manager", "Engagement Manager"
    ]
}

LEADERSHIP_TITLES = {
    "manager": [
        "Engineering Manager", "IT Manager", "Marketing Manager",
        "Business Development Manager", "Operations Manager", "Analytics Manager"
    ],
    "director": [
        "Director of Engineering", "IT Director", "Director of Marketing",
        "Director of Business Development", "Director of Operations",
        "Director of Product", "Director of Analytics", "Director of Data Science"
    ],
    "vp": [
        "VP of Engineering", "VP of Technology", "VP of Marketing",
        "VP of Sales", "VP of Operations", "VP of Product",
        "VP of Business Development", "VP of Strategy", "VP of Data"
    ],
    "c_level": [
        "CTO", "CIO", "CMO", "COO", "Chief Data Officer", "Chief Digital Officer"
    ]
}

# =============================================================================
# ACHIEVEMENT TEMPLATES
# =============================================================================

TECH_ACHIEVEMENTS = {
    "small": [
        "Developed {feature_count} new features for the company's main product",
        "Improved code test coverage from {old_pct}% to {new_pct}%",
        "Resolved {ticket_count}+ production issues within SLA targets",
        "Created technical documentation for {doc_count} internal tools",
        "Participated in code reviews, providing feedback on {pr_count}+ pull requests"
    ],
    "medium": [
        "Reduced application load time by {pct}% through performance optimization",
        "Led migration of {service_count} microservices to Kubernetes",
        "Implemented CI/CD pipeline reducing deployment time by {pct}%",
        "Mentored {mentee_count} junior developers in best practices",
        "Designed and built RESTful APIs serving {req_count}M+ requests daily"
    ],
    "large": [
        "Architected scalable system handling {user_count}M+ daily active users",
        "Led team of {team_size} engineers in delivering critical platform features",
        "Reduced infrastructure costs by ${savings}K annually through optimization",
        "Established engineering best practices adopted by {team_count} teams",
        "Drove technical strategy resulting in {pct}% improvement in system reliability"
    ],
    "enterprise": [
        "Led organization-wide digital transformation initiative impacting {emp_count}+ employees",
        "Managed ${budget}M technology budget across {dept_count} departments",
        "Built and scaled engineering organization from {start_size} to {end_size} engineers",
        "Delivered platform serving {customer_count}M+ customers globally",
        "Drove strategic initiatives resulting in ${revenue}M revenue growth"
    ]
}

BUSINESS_ACHIEVEMENTS = {
    "small": [
        "Analyzed {report_count} business reports to identify improvement opportunities",
        "Supported {project_count} project implementations successfully",
        "Created process documentation improving team efficiency by {pct}%",
        "Managed stakeholder communications for {stakeholder_count} departments"
    ],
    "medium": [
        "Led process improvement initiative saving {hours} hours weekly",
        "Managed projects totaling ${budget}K in annual budget",
        "Increased customer satisfaction scores by {pct}% through service improvements",
        "Developed business cases securing ${funding}K in project funding"
    ],
    "large": [
        "Directed cross-functional initiatives across {dept_count} departments",
        "Managed portfolio of {project_count} projects worth ${budget}M",
        "Delivered {pct}% improvement in operational efficiency",
        "Built and led team of {team_size} analysts and specialists"
    ],
    "enterprise": [
        "Drove strategic initiatives contributing ${revenue}M to bottom line",
        "Led M&A integration program spanning {location_count} global locations",
        "Managed P&L responsibility for ${budget}M business unit",
        "Transformed business operations resulting in {pct}% cost reduction"
    ]
}

MARKETING_ACHIEVEMENTS = {
    "small": [
        "Grew social media following by {pct}% across {platform_count} platforms",
        "Created {content_count}+ pieces of marketing content",
        "Improved email open rates by {pct}% through A/B testing",
        "Supported {campaign_count} marketing campaigns"
    ],
    "medium": [
        "Generated {lead_count}+ qualified leads through digital campaigns",
        "Managed ${budget}K marketing budget with {roi}x ROI",
        "Increased website traffic by {pct}% through SEO optimization",
        "Led rebranding initiative across {channel_count} marketing channels"
    ],
    "large": [
        "Drove {pct}% increase in marketing-attributed revenue",
        "Built and led marketing team of {team_size} specialists",
        "Managed ${budget}M integrated marketing budget",
        "Launched {product_count} successful product launches"
    ],
    "enterprise": [
        "Led global marketing transformation across {region_count} regions",
        "Managed ${budget}M marketing budget driving ${revenue}M pipeline",
        "Built marketing organization from {start_size} to {end_size} professionals",
        "Established brand as market leader with {pct}% awareness increase"
    ]
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def generate_phone():
    """Generate a random phone number."""
    return f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"


def generate_email(first_name, last_name):
    """Generate email address."""
    domains = ["gmail.com", "outlook.com", "yahoo.com", "protonmail.com", "icloud.com"]
    formats = [
        f"{first_name.lower()}.{last_name.lower()}",
        f"{first_name.lower()}{last_name.lower()}",
        f"{first_name[0].lower()}{last_name.lower()}",
        f"{first_name.lower()}.{last_name.lower()}{random.randint(1, 99)}"
    ]
    return f"{random.choice(formats)}@{random.choice(domains)}"


def generate_linkedin(first_name, last_name):
    """Generate LinkedIn URL."""
    return f"linkedin.com/in/{first_name.lower()}-{last_name.lower()}-{random.randint(1000, 9999)}"


def generate_address():
    """Generate random address."""
    cities = [
        ("San Francisco", "CA"), ("New York", "NY"), ("Seattle", "WA"), ("Austin", "TX"),
        ("Boston", "MA"), ("Chicago", "IL"), ("Los Angeles", "CA"), ("Denver", "CO"),
        ("Atlanta", "GA"), ("Dallas", "TX"), ("San Jose", "CA"), ("Portland", "OR"),
        ("Miami", "FL"), ("Phoenix", "AZ"), ("San Diego", "CA"), ("Minneapolis", "MN"),
        ("Philadelphia", "PA"), ("Washington", "DC"), ("Raleigh", "NC"), ("Salt Lake City", "UT"),
        ("Nashville", "TN"), ("Charlotte", "NC"), ("Pittsburgh", "PA"), ("Detroit", "MI")
    ]
    city, state = random.choice(cities)
    return f"{city}, {state}"


def get_experience_level(years):
    """Determine experience level based on years."""
    if years <= 2:
        return "beginner"
    elif years <= 5:
        return "intermediate"
    elif years <= 10:
        return "advanced"
    else:
        return "expert"


def generate_skills_for_role(role_category, level):
    """Generate appropriate skills based on role and level."""
    skills = []
    level_config = EXPERIENCE_LEVELS[level]
    skill_count = random.randint(*level_config["skill_count"])

    if role_category in ["development", "infrastructure", "data"]:
        # Technical IT roles
        skills.extend(random.sample(PROGRAMMING_LANGUAGES, min(4, skill_count // 3)))
        skills.extend(random.sample(FRAMEWORKS_LIBRARIES, min(3, skill_count // 4)))
        skills.extend(random.sample(CLOUD_PLATFORMS, min(3, skill_count // 4)))
        skills.extend(random.sample(DATABASES, min(2, skill_count // 5)))
        skills.extend(random.sample(IT_TOOLS, min(3, skill_count // 4)))
        if role_category == "data":
            skills.extend(random.sample(DATA_SKILLS, min(4, skill_count // 3)))
    elif role_category in ["analysis", "management", "product"]:
        # Business/Analysis roles
        skills.extend(random.sample(BUSINESS_SKILLS, min(6, skill_count // 2)))
        skills.extend(random.sample(IT_TOOLS[:10], min(3, skill_count // 4)))
        skills.extend(random.sample(DATA_SKILLS[:8], min(3, skill_count // 4)))
    elif role_category == "marketing":
        skills.extend(random.sample(MARKETING_SKILLS, min(8, skill_count // 2)))
        skills.extend(random.sample(BUSINESS_SKILLS[:10], min(4, skill_count // 3)))

    # Add soft skills based on level
    soft_skill_count = min(3, skill_count // 4) if level in ["beginner", "intermediate"] else min(5, skill_count // 3)
    skills.extend(random.sample(SOFT_SKILLS, soft_skill_count))

    return list(set(skills))[:skill_count]


def generate_certifications_for_role(role_category, level):
    """Generate appropriate certifications based on role and level."""
    level_config = EXPERIENCE_LEVELS[level]
    cert_count = random.randint(*level_config["cert_count"])

    if cert_count == 0:
        return []

    if role_category in ["development", "infrastructure", "data"]:
        certs = random.sample(IT_CERTIFICATIONS, min(cert_count, len(IT_CERTIFICATIONS)))
    else:
        # Mix of business and IT certs
        business_certs = random.sample(BUSINESS_CERTIFICATIONS, min(cert_count // 2 + 1, len(BUSINESS_CERTIFICATIONS)))
        it_certs = random.sample(IT_CERTIFICATIONS[:10], min(cert_count // 2, 10))
        certs = business_certs + it_certs

    return certs[:cert_count]


def generate_achievement(category, scale):
    """Generate an achievement based on category and scale."""
    if category == "tech":
        templates = TECH_ACHIEVEMENTS[scale]
    elif category == "marketing":
        templates = MARKETING_ACHIEVEMENTS[scale]
    else:
        templates = BUSINESS_ACHIEVEMENTS[scale]

    template = random.choice(templates)

    # Fill in template values based on scale
    scale_multipliers = {"small": 1, "medium": 5, "large": 20, "enterprise": 100}
    mult = scale_multipliers.get(scale, 1)

    return template.format(
        feature_count=random.randint(5, 15) * mult // 5,
        old_pct=random.randint(40, 60),
        new_pct=random.randint(75, 95),
        ticket_count=random.randint(50, 200) * mult // 5,
        doc_count=random.randint(5, 20) * mult // 5,
        pr_count=random.randint(100, 500) * mult // 5,
        pct=random.randint(15, 50),
        service_count=random.randint(3, 10) * mult // 5,
        mentee_count=random.randint(2, 8),
        req_count=random.choice([1, 5, 10, 50, 100]) * mult // 5,
        user_count=random.choice([1, 5, 10, 50]) * mult // 5,
        team_size=random.randint(3, 15) * mult // 5,
        savings=random.choice([50, 100, 200, 500]) * mult,
        team_count=random.randint(3, 10) * mult // 5,
        emp_count=random.choice([100, 500, 1000, 5000]) * mult // 5,
        budget=random.choice([1, 5, 10, 50]) * mult,
        dept_count=random.randint(3, 10),
        start_size=random.randint(5, 20),
        end_size=random.randint(30, 100) * mult // 5,
        customer_count=random.choice([1, 10, 50, 100]) * mult // 5,
        revenue=random.choice([1, 5, 10, 50]) * mult,
        report_count=random.randint(10, 50),
        project_count=random.randint(3, 15) * mult // 5,
        stakeholder_count=random.randint(3, 10),
        hours=random.randint(10, 50) * mult // 5,
        funding=random.choice([50, 100, 250, 500]) * mult // 5,
        location_count=random.randint(5, 20),
        platform_count=random.randint(3, 6),
        content_count=random.randint(20, 100) * mult // 5,
        campaign_count=random.randint(5, 20) * mult // 5,
        lead_count=random.choice([100, 500, 1000, 5000]) * mult // 5,
        roi=random.choice([2, 3, 5, 8, 10]),
        channel_count=random.randint(3, 8),
        product_count=random.randint(2, 10),
        region_count=random.randint(3, 10)
    )


def generate_work_experience(years_experience, role_category):
    """Generate work history for a resume."""
    experiences = []
    current_year = 2024
    years_remaining = years_experience

    while years_remaining > 0 and len(experiences) < 5:
        duration = min(random.randint(1, 4), years_remaining)
        end_year = current_year
        start_year = end_year - duration

        is_current = len(experiences) == 0

        # Progress through career levels
        career_progress = years_experience - years_remaining
        level = get_experience_level(career_progress + duration)
        level_config = EXPERIENCE_LEVELS[level]

        # Choose employer type based on career stage
        if career_progress < 3:
            employer_pool = STARTUPS + FORTUNE_500[:10]
        elif career_progress < 7:
            employer_pool = TECH_COMPANIES + FORTUNE_500
        else:
            employer_pool = TECH_COMPANIES + CONSULTING_FIRMS + FORTUNE_500

        employer = random.choice(employer_pool)

        # Get appropriate title
        if role_category in IT_TITLES:
            base_title = random.choice(IT_TITLES[role_category])
        elif role_category in BUSINESS_TITLES:
            base_title = random.choice(BUSINESS_TITLES[role_category])
        else:
            base_title = random.choice(IT_TITLES["development"])

        prefix = random.choice(level_config["title_prefixes"])
        title = prefix + base_title

        # Generate achievements
        achievement_category = "tech" if role_category in ["development", "infrastructure", "data"] else \
                             "marketing" if role_category == "marketing" else "business"

        achievements = []
        for _ in range(random.randint(2, 4)):
            achievement = generate_achievement(achievement_category, level_config["achievement_scale"])
            if achievement not in achievements:
                achievements.append(achievement)

        experience = {
            "title": title,
            "employer": employer,
            "location": generate_address(),
            "start_date": f"{random.choice(['January', 'March', 'June', 'September'])} {start_year}",
            "end_date": "Present" if is_current else f"{random.choice(['February', 'May', 'August', 'December'])} {end_year}",
            "achievements": achievements
        }

        experiences.append(experience)
        current_year = start_year
        years_remaining -= duration

    return experiences


def generate_education(years_experience, role_category):
    """Generate education history."""
    education = []

    # Degree types based on role
    if role_category in ["development", "infrastructure", "data"]:
        bachelors_options = [
            "Bachelor of Science in Computer Science",
            "Bachelor of Science in Software Engineering",
            "Bachelor of Science in Information Technology",
            "Bachelor of Science in Computer Engineering",
            "Bachelor of Science in Data Science"
        ]
        masters_options = [
            "Master of Science in Computer Science",
            "Master of Science in Software Engineering",
            "Master of Science in Data Science",
            "Master of Business Administration (MBA)"
        ]
    elif role_category == "marketing":
        bachelors_options = [
            "Bachelor of Arts in Marketing",
            "Bachelor of Science in Business Administration",
            "Bachelor of Arts in Communications",
            "Bachelor of Science in Digital Marketing"
        ]
        masters_options = [
            "Master of Business Administration (MBA)",
            "Master of Science in Marketing",
            "Master of Arts in Communications"
        ]
    else:
        bachelors_options = [
            "Bachelor of Science in Business Administration",
            "Bachelor of Arts in Economics",
            "Bachelor of Science in Finance",
            "Bachelor of Science in Management Information Systems",
            "Bachelor of Arts in Business Management"
        ]
        masters_options = [
            "Master of Business Administration (MBA)",
            "Master of Science in Business Analytics",
            "Master of Science in Management",
            "Master of Science in Finance"
        ]

    grad_year = 2024 - years_experience - random.randint(0, 3)

    education.append({
        "degree": random.choice(bachelors_options),
        "institution": random.choice(UNIVERSITIES),
        "graduation_year": grad_year,
        "gpa": round(random.uniform(3.0, 4.0), 2) if random.random() > 0.4 else None
    })

    # 50% chance of master's if 5+ years, higher for advanced roles
    masters_chance = 0.5 if years_experience >= 5 else 0.2
    if random.random() < masters_chance:
        education.insert(0, {
            "degree": random.choice(masters_options),
            "institution": random.choice(UNIVERSITIES),
            "graduation_year": grad_year + random.randint(2, 5),
            "gpa": round(random.uniform(3.3, 4.0), 2) if random.random() > 0.5 else None
        })

    return education


def generate_professional_summary(name, years_exp, role_category, level, skills):
    """Generate a professional summary statement."""
    level_descriptors = {
        "beginner": ["motivated", "eager", "enthusiastic", "detail-oriented"],
        "intermediate": ["results-driven", "skilled", "accomplished", "proficient"],
        "advanced": ["seasoned", "expert", "accomplished", "strategic"],
        "expert": ["visionary", "transformational", "executive-level", "industry-leading"]
    }

    role_descriptions = {
        "development": "software development and engineering",
        "infrastructure": "IT infrastructure and cloud technologies",
        "data": "data engineering and analytics",
        "analysis": "business analysis and process improvement",
        "marketing": "digital marketing and brand strategy",
        "management": "project management and operations",
        "product": "product management and delivery"
    }

    descriptor = random.choice(level_descriptors[level])
    role_desc = role_descriptions.get(role_category, "technology and business")
    top_skills = ", ".join(skills[:3])

    templates = [
        f"{descriptor.capitalize()} professional with {years_exp}+ years of experience in {role_desc}. Skilled in {top_skills}, with a proven track record of delivering impactful results.",
        f"Experienced {role_desc} professional bringing {years_exp} years of expertise. Strong background in {top_skills}, committed to driving innovation and business value.",
        f"{descriptor.capitalize()} {role_desc} specialist with {years_exp}+ years of hands-on experience. Proficient in {top_skills}, with excellent problem-solving and communication skills."
    ]

    return random.choice(templates)


def generate_resume(resume_id):
    """Generate a single resume."""
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)

    # Distribute experience levels: 25% beginner, 30% intermediate, 30% advanced, 15% expert
    level_weights = [0.25, 0.30, 0.30, 0.15]
    level = random.choices(list(EXPERIENCE_LEVELS.keys()), weights=level_weights)[0]
    years_range = EXPERIENCE_LEVELS[level]["years_range"]
    years_experience = random.randint(*years_range)

    # Select role category
    all_categories = list(IT_TITLES.keys()) + list(BUSINESS_TITLES.keys())
    role_category = random.choice(all_categories)

    # Generate skills and certifications
    skills = generate_skills_for_role(role_category, level)
    certifications = generate_certifications_for_role(role_category, level)

    resume = {
        "id": f"resume_{resume_id:03d}",
        "personal_info": {
            "name": f"{first_name} {last_name}",
            "email": generate_email(first_name, last_name),
            "phone": generate_phone(),
            "location": generate_address(),
            "linkedin": generate_linkedin(first_name, last_name)
        },
        "summary": generate_professional_summary(first_name, years_experience, role_category, level, skills),
        "years_experience": years_experience,
        "experience_level": level,
        "role_category": role_category,
        "experience": generate_work_experience(years_experience, role_category),
        "education": generate_education(years_experience, role_category),
        "certifications": certifications,
        "skills": skills
    }

    return resume


# =============================================================================
# JOB DESCRIPTION GENERATION
# =============================================================================

def generate_job_description(job_id, job_category=None):
    """Generate a single job description."""

    # Job categories with their characteristics
    job_configs = {
        "it_individual": {
            "titles": IT_TITLES["development"] + IT_TITLES["infrastructure"] + IT_TITLES["data"],
            "prefixes": ["", "Senior ", "Staff ", "Lead "],
            "level": "individual_contributor",
            "min_years_options": [0, 2, 3, 5],
            "category": "technology"
        },
        "business_analyst": {
            "titles": BUSINESS_TITLES["analysis"],
            "prefixes": ["", "Senior ", "Lead "],
            "level": "individual_contributor",
            "min_years_options": [1, 2, 3, 5],
            "category": "business"
        },
        "marketing": {
            "titles": BUSINESS_TITLES["marketing"],
            "prefixes": ["", "Senior "],
            "level": "individual_contributor",
            "min_years_options": [1, 2, 3, 5],
            "category": "marketing"
        },
        "manager": {
            "titles": LEADERSHIP_TITLES["manager"],
            "prefixes": ["", "Senior "],
            "level": "manager",
            "min_years_options": [5, 7, 8],
            "category": "leadership"
        },
        "director": {
            "titles": LEADERSHIP_TITLES["director"],
            "prefixes": [""],
            "level": "director",
            "min_years_options": [8, 10, 12],
            "category": "leadership"
        },
        "vp": {
            "titles": LEADERSHIP_TITLES["vp"],
            "prefixes": [""],
            "level": "executive",
            "min_years_options": [12, 15, 18],
            "category": "leadership"
        }
    }

    # Select job category if not provided
    if job_category is None:
        # Distribution: 40% IT, 15% BA, 15% Marketing, 15% Manager, 10% Director, 5% VP
        weights = [0.40, 0.15, 0.15, 0.15, 0.10, 0.05]
        job_category = random.choices(list(job_configs.keys()), weights=weights)[0]

    config = job_configs[job_category]

    # Generate job details
    prefix = random.choice(config["prefixes"])
    base_title = random.choice(config["titles"])
    title = prefix + base_title

    # Employer
    employer_types = ["tech", "consulting", "fortune500", "startup"]
    employer_type = random.choice(employer_types)

    if employer_type == "tech":
        employer = random.choice(TECH_COMPANIES)
    elif employer_type == "consulting":
        employer = random.choice(CONSULTING_FIRMS)
    elif employer_type == "fortune500":
        employer = random.choice(FORTUNE_500)
    else:
        employer = random.choice(STARTUPS)

    # Employment details
    employment_type = random.choice(["Full-time", "Full-time"])  # Mostly full-time
    is_contract = random.random() < 0.2
    contract_type = "Contract" if is_contract else "Permanent"
    remote_option = random.choice(["On-site", "Hybrid", "Remote", "Hybrid (3 days in office)"])

    # Experience requirements
    min_years = random.choice(config["min_years_options"])
    max_years = min_years + random.randint(5, 10) if random.random() > 0.6 else None

    # Skills based on category
    if config["category"] == "technology":
        required_skills = random.sample(PROGRAMMING_LANGUAGES, 3) + \
                         random.sample(CLOUD_PLATFORMS[:8], 2) + \
                         random.sample(IT_TOOLS[:10], 2)
        preferred_skills = random.sample(FRAMEWORKS_LIBRARIES, 3) + \
                          random.sample(DATABASES, 2)
    elif config["category"] == "marketing":
        required_skills = random.sample(MARKETING_SKILLS, 6)
        preferred_skills = random.sample(BUSINESS_SKILLS[:10], 3) + \
                          random.sample(DATA_SKILLS[:5], 2)
    elif config["category"] == "leadership":
        required_skills = random.sample(BUSINESS_SKILLS, 5) + \
                         random.sample(SOFT_SKILLS, 4)
        preferred_skills = random.sample(IT_TOOLS[:8], 3)
    else:  # business
        required_skills = random.sample(BUSINESS_SKILLS, 5) + \
                         random.sample(DATA_SKILLS[:6], 2)
        preferred_skills = random.sample(IT_TOOLS[:10], 3)

    # Certifications
    if config["category"] == "technology":
        required_certs = random.sample(IT_CERTIFICATIONS, 1) if random.random() > 0.5 else []
        preferred_certs = random.sample(IT_CERTIFICATIONS, 2)
    else:
        required_certs = random.sample(BUSINESS_CERTIFICATIONS, 1) if random.random() > 0.6 else []
        preferred_certs = random.sample(BUSINESS_CERTIFICATIONS, 2)

    # Salary
    base_salaries = {
        "individual_contributor": 80000,
        "manager": 130000,
        "director": 175000,
        "executive": 250000
    }

    base = base_salaries[config["level"]]
    min_salary = base + (min_years * 5000) + random.randint(-10000, 10000)
    max_salary = min_salary + random.randint(20000, 50000)

    if is_contract:
        hourly_min = int(min_salary / 2000)
        hourly_max = int(max_salary / 2000)
        salary_info = {"type": "hourly", "min": hourly_min, "max": hourly_max, "currency": "USD"}
    else:
        salary_info = {"type": "annual", "min": min_salary, "max": max_salary, "currency": "USD"}

    # Generate description and responsibilities
    description = generate_job_description_text(title, employer, config["category"])
    responsibilities = generate_responsibilities_for_job(config["category"], config["level"])

    job = {
        "id": f"job_{job_id:03d}",
        "title": title,
        "employer": employer,
        "employer_type": employer_type,
        "location": generate_address(),
        "remote_option": remote_option,
        "employment_type": employment_type,
        "contract_type": contract_type,
        "posted_date": (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d"),
        "job_category": job_category,
        "seniority_level": config["level"],
        "experience_required": {
            "min_years": min_years,
            "max_years": max_years
        },
        "description": description,
        "responsibilities": responsibilities,
        "required_qualifications": {
            "education": generate_education_requirement(config["level"]),
            "experience": f"{min_years}+ years of relevant experience",
            "skills": required_skills,
            "certifications": required_certs
        },
        "preferred_qualifications": {
            "skills": preferred_skills,
            "certifications": preferred_certs
        },
        "salary": salary_info,
        "benefits": generate_benefits_for_job(is_contract)
    }

    return job


def generate_job_description_text(title, employer, category):
    """Generate the main job description text."""
    templates = {
        "technology": [
            f"{employer} is seeking a talented {title} to join our engineering team. You will work on challenging problems, build scalable systems, and collaborate with talented engineers to deliver impactful products.",
            f"Join {employer} as a {title} and help us build the next generation of technology solutions. We're looking for someone passionate about clean code, system design, and continuous improvement.",
        ],
        "marketing": [
            f"{employer} is looking for a creative {title} to drive our marketing initiatives. You'll develop strategies, execute campaigns, and analyze performance to grow our brand presence.",
            f"Join our marketing team at {employer} as a {title}. You'll have the opportunity to shape our brand story and drive customer acquisition through innovative marketing strategies.",
        ],
        "business": [
            f"{employer} seeks an analytical {title} to support strategic initiatives. You'll work with stakeholders across the organization to identify opportunities and drive process improvements.",
            f"We're looking for a {title} to join {employer}. In this role, you'll analyze business requirements, develop solutions, and help drive operational excellence.",
        ],
        "leadership": [
            f"{employer} is seeking an experienced {title} to lead and grow our team. You'll set strategic direction, mentor team members, and drive results across the organization.",
            f"Join {employer} as a {title} and help shape the future of our organization. You'll build high-performing teams, drive strategic initiatives, and deliver exceptional results.",
        ]
    }

    return random.choice(templates.get(category, templates["technology"]))


def generate_responsibilities_for_job(category, level):
    """Generate job responsibilities based on category and level."""
    base = [
        "Collaborate with cross-functional teams to achieve business objectives",
        "Communicate effectively with stakeholders at all levels",
        "Stay current with industry trends and best practices"
    ]

    if category == "technology":
        specific = [
            "Design, develop, and maintain software applications",
            "Write clean, testable, and efficient code",
            "Participate in code reviews and technical discussions",
            "Troubleshoot and debug production issues",
            "Contribute to architectural decisions and technical strategy"
        ]
    elif category == "marketing":
        specific = [
            "Develop and execute marketing strategies and campaigns",
            "Analyze campaign performance and optimize for results",
            "Create compelling content for various channels",
            "Manage marketing budget and track ROI",
            "Collaborate with sales and product teams on go-to-market initiatives"
        ]
    elif category == "leadership":
        specific = [
            "Lead, mentor, and develop team members",
            "Set strategic direction and priorities for the team",
            "Manage budgets, resources, and timelines",
            "Build relationships with key stakeholders and partners",
            "Drive organizational change and transformation initiatives"
        ]
    else:  # business
        specific = [
            "Gather and analyze business requirements",
            "Develop process improvements and efficiency recommendations",
            "Create business cases and presentations for leadership",
            "Support project implementation and change management",
            "Track KPIs and report on business performance"
        ]

    # Add level-specific responsibilities
    if level in ["manager", "director", "executive"]:
        specific.extend([
            "Recruit, hire, and retain top talent",
            "Conduct performance reviews and career development discussions",
            "Represent the team in executive meetings and steering committees"
        ])

    return base + specific


def generate_education_requirement(level):
    """Generate education requirement based on level."""
    if level == "executive":
        return "Master's degree preferred; MBA or relevant advanced degree a plus"
    elif level == "director":
        return "Bachelor's degree required; Master's degree preferred"
    else:
        return "Bachelor's degree in relevant field or equivalent experience"


def generate_benefits_for_job(is_contract):
    """Generate benefits package."""
    if is_contract:
        return ["Competitive hourly rate", "Flexible schedule"]

    return random.sample([
        "Comprehensive health, dental, and vision insurance",
        "401(k) with company match",
        "Unlimited PTO",
        "Remote work flexibility",
        "Professional development budget",
        "Stock options/equity grants",
        "Life and disability insurance",
        "Wellness programs and gym membership",
        "Parental leave",
        "Commuter benefits",
        "Annual bonus program",
        "Home office stipend"
    ], random.randint(6, 9))


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Generate generalized IT/Business test data")
    parser.add_argument("--resumes", type=int, default=100, help="Number of resumes to generate")
    parser.add_argument("--jobs", type=int, default=30, help="Number of job descriptions to generate")
    parser.add_argument("--output-dir", type=str, default="test_data", help="Output directory")
    args = parser.parse_args()

    base_dir = Path(args.output_dir)
    resume_dir = base_dir / "general_resumes"
    job_dir = base_dir / "general_jobs"

    resume_dir.mkdir(parents=True, exist_ok=True)
    job_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating {args.resumes} generalized IT/Business resumes...")
    print("  Experience levels: Beginner (25%), Intermediate (30%), Advanced (30%), Expert (15%)")

    level_counts = {"beginner": 0, "intermediate": 0, "advanced": 0, "expert": 0}

    for i in range(1, args.resumes + 1):
        resume = generate_resume(i)
        level_counts[resume["experience_level"]] += 1

        output_path = resume_dir / f"resume_{i:03d}.json"
        with open(output_path, "w") as f:
            json.dump(resume, f, indent=2)

        if i % 25 == 0:
            print(f"  Generated {i}/{args.resumes} resumes")

    print(f"\n  Level distribution: {level_counts}")

    print(f"\nGenerating {args.jobs} job descriptions...")
    print("  Categories: IT (40%), Business Analyst (15%), Marketing (15%)")
    print("             Manager (15%), Director (10%), VP (5%)")

    # Generate jobs with specific distribution
    job_categories = (
        ["it_individual"] * 12 +      # 40% of 30 = 12
        ["business_analyst"] * 5 +    # 15% of 30 = 4-5
        ["marketing"] * 5 +           # 15% of 30 = 4-5
        ["manager"] * 4 +             # 15% of 30 = 4-5
        ["director"] * 3 +            # 10% of 30 = 3
        ["vp"] * 1                    # 5% of 30 = 1-2
    )
    random.shuffle(job_categories)

    category_counts = {}
    for i in range(1, args.jobs + 1):
        category = job_categories[i-1] if i <= len(job_categories) else random.choice(list(job_categories))
        job = generate_job_description(i, category)

        cat = job["job_category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1

        output_path = job_dir / f"job_{i:03d}.json"
        with open(output_path, "w") as f:
            json.dump(job, f, indent=2)

    print(f"\n  Category distribution: {category_counts}")

    print(f"\nTest data generated successfully!")
    print(f"  Resumes: {resume_dir}")
    print(f"  Jobs: {job_dir}")


if __name__ == "__main__":
    main()
