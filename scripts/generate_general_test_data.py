#!/usr/bin/env python3
"""
Generalized Test Data Generator

Creates diverse test data for IT, Business, and Marketing domains:
- 100 resumes with varying experience levels (Entry/Junior/Mid/Senior/Lead/Director/VP)
- 30 job descriptions across IT, Marketing, Business Analysis, Management, and Executive levels

This complements the healthcare-specific test data for domain generalization testing.

Author: Engineering Team
Version: 1.0.0
"""

import json
import os
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Seed for reproducibility
random.seed(42)

# =============================================================================
# CONFIGURATION
# =============================================================================

OUTPUT_DIR = Path("data/general")
RESUMES_DIR = OUTPUT_DIR / "resumes"
JOBS_DIR = OUTPUT_DIR / "job_descriptions"

# Experience levels and their characteristics
EXPERIENCE_LEVELS = {
    "entry": {"years": (0, 2), "title_prefix": "", "weight": 0.15},
    "junior": {"years": (1, 3), "title_prefix": "Junior ", "weight": 0.20},
    "mid": {"years": (3, 6), "title_prefix": "", "weight": 0.25},
    "senior": {"years": (5, 10), "title_prefix": "Senior ", "weight": 0.20},
    "lead": {"years": (7, 12), "title_prefix": "Lead ", "weight": 0.10},
    "director": {"years": (10, 18), "title_prefix": "Director of ", "weight": 0.07},
    "vp": {"years": (12, 25), "title_prefix": "VP of ", "weight": 0.03},
}

# =============================================================================
# DOMAIN DATA: IT
# =============================================================================

IT_TECH_STACKS = {
    "cloud": {
        "primary": ["AWS", "Azure", "Google Cloud", "Multi-Cloud"],
        "skills": ["EC2", "S3", "Lambda", "CloudFormation", "Terraform", "Kubernetes",
                   "Docker", "Azure DevOps", "GKE", "IAM", "VPC", "CloudWatch"],
        "certifications": [
            "AWS Solutions Architect - Associate",
            "AWS Solutions Architect - Professional",
            "AWS DevOps Engineer",
            "Azure Administrator Associate",
            "Azure Solutions Architect Expert",
            "Google Cloud Professional Cloud Architect",
            "Certified Kubernetes Administrator (CKA)",
            "HashiCorp Terraform Associate",
        ]
    },
    "fullstack": {
        "primary": ["JavaScript/TypeScript", "Python", "Java", ".NET"],
        "skills": ["React", "Angular", "Vue.js", "Node.js", "Express", "Django",
                   "Flask", "Spring Boot", "PostgreSQL", "MongoDB", "Redis", "GraphQL",
                   "REST APIs", "Microservices", "Git", "CI/CD"],
        "certifications": [
            "AWS Certified Developer",
            "MongoDB Certified Developer",
            "Oracle Certified Professional Java Developer",
            "Microsoft Certified: Azure Developer Associate",
        ]
    },
    "data": {
        "primary": ["Python", "SQL", "Spark", "Data Engineering"],
        "skills": ["Pandas", "NumPy", "Scikit-learn", "TensorFlow", "PyTorch",
                   "Snowflake", "Databricks", "Airflow", "dbt", "Kafka",
                   "ETL", "Data Modeling", "Power BI", "Tableau", "Looker"],
        "certifications": [
            "Google Professional Data Engineer",
            "AWS Data Analytics Specialty",
            "Databricks Certified Data Engineer",
            "Snowflake SnowPro Core",
            "Microsoft Certified: Data Analyst Associate",
        ]
    },
    "security": {
        "primary": ["Security Engineering", "Cloud Security", "AppSec"],
        "skills": ["SIEM", "Penetration Testing", "Vulnerability Assessment",
                   "SOC Operations", "Incident Response", "Firewall", "IDS/IPS",
                   "OWASP", "Security Compliance", "Risk Assessment", "IAM"],
        "certifications": [
            "CISSP",
            "CEH (Certified Ethical Hacker)",
            "CompTIA Security+",
            "AWS Security Specialty",
            "CISM",
            "OSCP",
        ]
    },
    "devops": {
        "primary": ["DevOps", "SRE", "Platform Engineering"],
        "skills": ["Jenkins", "GitLab CI", "GitHub Actions", "ArgoCD",
                   "Ansible", "Puppet", "Chef", "Prometheus", "Grafana",
                   "ELK Stack", "Helm", "Service Mesh", "Istio"],
        "certifications": [
            "AWS DevOps Engineer Professional",
            "Certified Kubernetes Administrator",
            "HashiCorp Vault Associate",
            "GitLab Certified Associate",
        ]
    }
}

IT_ROLES = [
    "Software Engineer", "Software Developer", "Backend Developer", "Frontend Developer",
    "Full Stack Developer", "DevOps Engineer", "Site Reliability Engineer",
    "Cloud Engineer", "Data Engineer", "Data Scientist", "ML Engineer",
    "Security Engineer", "Platform Engineer", "Solutions Architect",
    "Systems Administrator", "Network Engineer", "Database Administrator",
    "QA Engineer", "Test Automation Engineer", "Technical Lead",
    "Engineering Manager", "IT Project Manager", "Scrum Master"
]

IT_EMPLOYERS = [
    "Google", "Amazon", "Microsoft", "Meta", "Apple", "Netflix", "Salesforce",
    "Oracle", "IBM", "Cisco", "VMware", "ServiceNow", "Workday", "Splunk",
    "Datadog", "Snowflake", "Databricks", "Stripe", "Square", "Shopify",
    "Uber", "Lyft", "Airbnb", "DoorDash", "Instacart", "Robinhood",
    "Accenture", "Deloitte", "McKinsey Digital", "BCG Platinion",
    "Capital One", "JPMorgan Chase", "Goldman Sachs", "Morgan Stanley",
    "Fidelity", "Charles Schwab", "Bloomberg", "Thomson Reuters"
]

IT_ACHIEVEMENTS = [
    "Reduced system latency by {percent}% through optimization of database queries and caching strategies",
    "Led migration of {count} microservices to Kubernetes, improving deployment frequency by {percent}%",
    "Architected data pipeline processing {volume}+ events per day with 99.9% reliability",
    "Implemented CI/CD pipeline reducing deployment time from {old_time} to {new_time}",
    "Built machine learning model achieving {percent}% accuracy for fraud detection",
    "Designed API serving {volume}+ requests per second with sub-{latency}ms latency",
    "Reduced infrastructure costs by ${amount}K annually through cloud optimization",
    "Mentored team of {count} engineers, improving code review quality by {percent}%",
    "Implemented security controls achieving SOC 2 Type II certification",
    "Developed automation reducing manual operations by {percent}%",
    "Led incident response for critical outage, reducing MTTR from {old_time} to {new_time}",
    "Architected event-driven system handling {volume}+ daily transactions",
]

# =============================================================================
# DOMAIN DATA: BUSINESS
# =============================================================================

BUSINESS_SPECIALTIES = {
    "analysis": {
        "primary": ["Business Analysis", "Process Improvement", "Requirements"],
        "skills": ["Requirements Gathering", "Process Mapping", "BPMN", "User Stories",
                   "Stakeholder Management", "Gap Analysis", "Use Cases", "UAT",
                   "Agile", "Scrum", "JIRA", "Confluence", "SQL", "Excel"],
        "certifications": [
            "CBAP (Certified Business Analysis Professional)",
            "PMI-PBA",
            "IIBA Entry Certificate in Business Analysis",
            "Six Sigma Green Belt",
            "Agile Certified Practitioner (PMI-ACP)",
        ]
    },
    "product": {
        "primary": ["Product Management", "Product Strategy", "Product Development"],
        "skills": ["Product Roadmapping", "A/B Testing", "User Research", "Competitive Analysis",
                   "OKRs", "KPIs", "PRDs", "Feature Prioritization", "Go-to-Market",
                   "Figma", "Amplitude", "Mixpanel", "Segment"],
        "certifications": [
            "Certified Scrum Product Owner (CSPO)",
            "Product School Certification",
            "Pragmatic Marketing Certified",
        ]
    },
    "project": {
        "primary": ["Project Management", "Program Management", "PMO"],
        "skills": ["Project Planning", "Risk Management", "Budget Management",
                   "Resource Allocation", "Gantt Charts", "MS Project", "Smartsheet",
                   "Stakeholder Communication", "Change Management", "RAID Log"],
        "certifications": [
            "PMP (Project Management Professional)",
            "PRINCE2 Practitioner",
            "Certified ScrumMaster (CSM)",
            "PMI-ACP",
            "CAPM",
        ]
    },
    "operations": {
        "primary": ["Operations Management", "Process Excellence", "Supply Chain"],
        "skills": ["Process Optimization", "Lean Management", "Six Sigma",
                   "Vendor Management", "Contract Negotiation", "SLA Management",
                   "Capacity Planning", "Quality Assurance", "KPI Tracking"],
        "certifications": [
            "Six Sigma Black Belt",
            "Lean Six Sigma Master Black Belt",
            "APICS CSCP",
            "CPSM (Certified Supply Management)",
        ]
    }
}

BUSINESS_ROLES = [
    "Business Analyst", "Senior Business Analyst", "Lead Business Analyst",
    "Product Manager", "Senior Product Manager", "Principal Product Manager",
    "Project Manager", "Senior Project Manager", "Program Manager",
    "Operations Manager", "Operations Director", "Chief Operating Officer",
    "Strategy Analyst", "Strategy Manager", "Strategy Director",
    "Process Improvement Specialist", "Business Process Manager",
    "Business Development Manager", "Partnership Manager",
    "Chief of Staff", "Management Consultant"
]

BUSINESS_EMPLOYERS = [
    "McKinsey & Company", "Boston Consulting Group", "Bain & Company",
    "Deloitte Consulting", "Accenture Strategy", "KPMG Advisory",
    "EY-Parthenon", "PwC Strategy&", "Oliver Wyman", "A.T. Kearney",
    "Amazon", "Google", "Microsoft", "Salesforce", "Adobe",
    "Walmart", "Target", "Home Depot", "Costco",
    "JPMorgan Chase", "Bank of America", "Citigroup", "Wells Fargo",
    "UnitedHealth Group", "CVS Health", "Anthem", "Humana",
    "Procter & Gamble", "Johnson & Johnson", "Pfizer", "Merck"
]

BUSINESS_ACHIEVEMENTS = [
    "Led digital transformation initiative resulting in ${amount}M annual savings",
    "Developed requirements for system serving {count}+ users across {regions} regions",
    "Managed ${amount}M project budget with delivery {percent}% under budget",
    "Improved process efficiency by {percent}% through Lean Six Sigma implementation",
    "Launched product feature increasing user engagement by {percent}%",
    "Negotiated vendor contracts saving ${amount}K annually",
    "Facilitated {count}+ stakeholder workshops for enterprise requirements",
    "Reduced project delivery time by {percent}% through Agile transformation",
    "Built business case for ${amount}M technology investment with {percent}% ROI",
    "Managed cross-functional team of {count} across {regions} time zones",
]

# =============================================================================
# DOMAIN DATA: MARKETING
# =============================================================================

MARKETING_SPECIALTIES = {
    "digital": {
        "primary": ["Digital Marketing", "Performance Marketing", "Growth"],
        "skills": ["SEO", "SEM", "PPC", "Google Ads", "Facebook Ads", "LinkedIn Ads",
                   "Email Marketing", "Marketing Automation", "A/B Testing",
                   "Google Analytics", "HubSpot", "Marketo", "Salesforce Marketing Cloud"],
        "certifications": [
            "Google Ads Certification",
            "Google Analytics Certification",
            "HubSpot Inbound Marketing",
            "Facebook Blueprint Certification",
            "Hootsuite Social Marketing",
        ]
    },
    "content": {
        "primary": ["Content Marketing", "Content Strategy", "Brand"],
        "skills": ["Content Strategy", "Copywriting", "SEO Content", "Editorial Planning",
                   "Brand Voice", "Storytelling", "Video Production", "Podcasting",
                   "WordPress", "Webflow", "Adobe Creative Suite"],
        "certifications": [
            "Content Marketing Institute Certification",
            "HubSpot Content Marketing",
            "Copyblogger Certified Content Marketer",
        ]
    },
    "analytics": {
        "primary": ["Marketing Analytics", "Customer Insights", "Market Research"],
        "skills": ["Data Analysis", "Marketing Attribution", "Customer Segmentation",
                   "CLV Analysis", "Cohort Analysis", "SQL", "Tableau", "Looker",
                   "Google Analytics 4", "Amplitude", "Mixpanel"],
        "certifications": [
            "Google Analytics 4 Certification",
            "Tableau Desktop Specialist",
            "Marketing Research Association (MRA)",
        ]
    },
    "product_marketing": {
        "primary": ["Product Marketing", "Go-to-Market", "Positioning"],
        "skills": ["Product Positioning", "Competitive Analysis", "Sales Enablement",
                   "Launch Planning", "Messaging", "Customer Research", "Pricing Strategy",
                   "Battle Cards", "Demo Development"],
        "certifications": [
            "Product Marketing Alliance Certification",
            "Pragmatic Marketing Certified",
        ]
    }
}

MARKETING_ROLES = [
    "Marketing Coordinator", "Marketing Specialist", "Marketing Manager",
    "Digital Marketing Manager", "Growth Marketing Manager",
    "Content Marketing Manager", "Content Strategist",
    "Brand Manager", "Brand Director", "VP of Brand",
    "Demand Generation Manager", "Marketing Operations Manager",
    "Product Marketing Manager", "Senior Product Marketing Manager",
    "Marketing Analytics Manager", "Customer Insights Manager",
    "CMO", "VP of Marketing", "Director of Marketing"
]

MARKETING_EMPLOYERS = [
    "Google", "Meta", "Amazon", "Apple", "Netflix", "Spotify", "Adobe",
    "HubSpot", "Salesforce", "Mailchimp", "Hootsuite", "Buffer",
    "Nike", "Coca-Cola", "PepsiCo", "Unilever", "P&G",
    "Ogilvy", "Wieden+Kennedy", "BBDO", "DDB", "Leo Burnett",
    "VaynerMedia", "R/GA", "Huge", "AKQA", "Droga5"
]

MARKETING_ACHIEVEMENTS = [
    "Increased organic traffic by {percent}% through SEO optimization strategy",
    "Generated ${amount}M in pipeline through demand generation campaigns",
    "Achieved {percent}% improvement in email open rates through A/B testing",
    "Launched product to {count}K customers with {percent}% activation rate",
    "Reduced customer acquisition cost by {percent}% while scaling spend ${amount}K",
    "Built marketing analytics dashboard tracking {count}+ KPIs across channels",
    "Led rebranding initiative increasing brand awareness by {percent}%",
    "Managed ${amount}M annual marketing budget across {count} channels",
    "Developed content strategy resulting in {count}K monthly blog visitors",
    "Created sales enablement materials improving win rate by {percent}%",
]

# =============================================================================
# COMMON DATA
# =============================================================================

FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Lisa", "Daniel", "Nancy",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
    "Kenneth", "Dorothy", "Kevin", "Carol", "Brian", "Amanda", "George", "Melissa",
    "Timothy", "Deborah", "Ronald", "Stephanie", "Edward", "Rebecca", "Jason", "Sharon",
    "Jeffrey", "Laura", "Ryan", "Cynthia", "Jacob", "Kathleen", "Gary", "Amy",
    "Nicholas", "Angela", "Eric", "Shirley", "Jonathan", "Anna", "Stephen", "Brenda",
    "Larry", "Pamela", "Justin", "Emma", "Scott", "Nicole", "Brandon", "Helen",
    "Benjamin", "Samantha", "Samuel", "Katherine", "Raymond", "Christine", "Gregory", "Debra",
    "Frank", "Rachel", "Alexander", "Carolyn", "Patrick", "Janet", "Jack", "Catherine",
    "Wei", "Priya", "Mohammed", "Fatima", "Raj", "Aisha", "Chen", "Mei",
    "Hiroshi", "Yuki", "Carlos", "Maria", "Ahmed", "Leila", "Dmitri", "Olga",
    "Sanjay", "Deepika", "Kwame", "Ama", "Tao", "Xiu", "Jamal", "Zara"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill",
    "Flores", "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell",
    "Mitchell", "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz",
    "Parker", "Cruz", "Edwards", "Collins", "Reyes", "Stewart", "Morris", "Morales",
    "Murphy", "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan", "Cooper", "Peterson",
    "Bailey", "Reed", "Kelly", "Howard", "Ramos", "Kim", "Cox", "Ward",
    "Richardson", "Watson", "Brooks", "Chavez", "Wood", "James", "Bennett", "Gray",
    "Patel", "Singh", "Chen", "Wang", "Li", "Zhang", "Liu", "Yang",
    "Kumar", "Shah", "Sharma", "Gupta", "Joshi", "Desai", "Mehta", "Rao",
    "Yamamoto", "Tanaka", "Suzuki", "Watanabe", "Nakamura", "Kobayashi"
]

LOCATIONS = [
    "San Francisco, CA", "New York, NY", "Seattle, WA", "Austin, TX",
    "Boston, MA", "Chicago, IL", "Los Angeles, CA", "Denver, CO",
    "Atlanta, GA", "Miami, FL", "Dallas, TX", "San Diego, CA",
    "Phoenix, AZ", "Portland, OR", "Minneapolis, MN", "Detroit, MI",
    "Philadelphia, PA", "Washington, DC", "Raleigh, NC", "Nashville, TN",
    "Salt Lake City, UT", "Charlotte, NC", "Tampa, FL", "Orlando, FL",
    "Remote", "Remote", "Remote"  # Higher weight for remote
]

DEGREES = [
    ("BS", "Computer Science"),
    ("BS", "Information Technology"),
    ("BS", "Software Engineering"),
    ("BS", "Data Science"),
    ("BS", "Business Administration"),
    ("BS", "Marketing"),
    ("BS", "Economics"),
    ("BS", "Finance"),
    ("BA", "Communications"),
    ("BA", "Psychology"),
    ("BS", "Mathematics"),
    ("BS", "Statistics"),
    ("MBA", "Business Administration"),
    ("MS", "Computer Science"),
    ("MS", "Data Science"),
    ("MS", "Information Systems"),
    ("MS", "Business Analytics"),
]

UNIVERSITIES = [
    "Stanford University", "MIT", "Harvard University", "UC Berkeley",
    "Carnegie Mellon University", "Georgia Tech", "University of Washington",
    "University of Texas at Austin", "University of Michigan", "UCLA",
    "Columbia University", "NYU", "University of Pennsylvania", "Cornell University",
    "Northwestern University", "Duke University", "USC", "University of Illinois",
    "Purdue University", "Penn State", "Ohio State University", "University of Florida",
    "Arizona State University", "University of Colorado", "University of Maryland",
    "Boston University", "Northeastern University", "University of Virginia"
]

SOFT_SKILLS = [
    "Team Leadership", "Cross-functional Collaboration", "Strategic Thinking",
    "Problem Solving", "Communication", "Stakeholder Management",
    "Mentoring", "Conflict Resolution", "Negotiation", "Presentation Skills",
    "Time Management", "Adaptability", "Critical Thinking", "Decision Making",
    "Emotional Intelligence", "Influence", "Coaching", "Change Management"
]


# =============================================================================
# RESUME GENERATION
# =============================================================================

def generate_experience_dates(years_exp: int, num_roles: int) -> List[Tuple[str, str]]:
    """Generate realistic experience date ranges."""
    dates = []
    current_year = datetime.now().year
    current_month = datetime.now().month

    # Start from present and work backwards
    end_date = "Present"
    years_remaining = years_exp

    for i in range(num_roles):
        if i == 0:
            # Current role: started 1-4 years ago
            tenure = min(random.randint(1, 4), years_remaining)
            start_year = current_year - tenure
            start_month = random.randint(1, 12)
            start_date = f"{start_year}-{start_month:02d}"
            dates.append((start_date, end_date))
            years_remaining -= tenure
        else:
            # Previous roles
            if years_remaining <= 0:
                break

            # Gap between jobs (0-6 months)
            gap_months = random.randint(0, 6)
            prev_start = datetime.strptime(dates[-1][0], "%Y-%m")
            role_end = prev_start - timedelta(days=gap_months * 30)

            # Role duration (1-5 years)
            tenure = min(random.randint(1, 5), years_remaining)
            role_start = role_end - timedelta(days=tenure * 365)

            dates.append((
                role_start.strftime("%Y-%m"),
                role_end.strftime("%Y-%m")
            ))
            years_remaining -= tenure

    return dates


def generate_achievements(templates: List[str], count: int) -> List[str]:
    """Generate random achievements from templates."""
    achievements = []
    selected = random.sample(templates, min(count, len(templates)))

    for template in selected:
        achievement = template.format(
            percent=random.randint(15, 75),
            count=random.choice([3, 5, 8, 10, 15, 20, 50, 100]),
            volume=random.choice(["10K", "50K", "100K", "500K", "1M", "5M", "10M"]),
            amount=random.choice([50, 100, 150, 200, 300, 500, 750, 1000]),
            regions=random.randint(2, 8),
            old_time=random.choice(["4 hours", "2 days", "1 week", "2 weeks"]),
            new_time=random.choice(["30 minutes", "2 hours", "1 day", "3 days"]),
            latency=random.choice([10, 50, 100, 200]),
        )
        achievements.append(achievement)

    return achievements


def select_experience_level() -> str:
    """Select experience level based on weighted distribution."""
    levels = list(EXPERIENCE_LEVELS.keys())
    weights = [EXPERIENCE_LEVELS[l]["weight"] for l in levels]
    return random.choices(levels, weights=weights)[0]


def generate_it_resume(resume_id: int) -> Dict[str, Any]:
    """Generate an IT professional resume."""
    level = select_experience_level()
    level_config = EXPERIENCE_LEVELS[level]
    years_exp = random.randint(*level_config["years"])

    # Select tech stack
    stack_name = random.choice(list(IT_TECH_STACKS.keys()))
    stack = IT_TECH_STACKS[stack_name]

    # Generate personal info
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)

    # Select role appropriate to level
    if level in ["director", "vp"]:
        base_role = random.choice(["Engineering", "Technology", "IT", "Platform", "Data"])
    else:
        base_role = random.choice(IT_ROLES)

    current_title = f"{level_config['title_prefix']}{base_role}"

    # Generate experience
    num_roles = min(years_exp // 2 + 1, 5)  # 1-5 roles based on experience
    dates = generate_experience_dates(years_exp, num_roles)

    experience = []
    for i, (start, end) in enumerate(dates):
        if i == 0:
            title = current_title
            employer = random.choice(IT_EMPLOYERS)
        else:
            # Previous roles at lower levels
            prev_level = list(EXPERIENCE_LEVELS.keys())[max(0, list(EXPERIENCE_LEVELS.keys()).index(level) - i)]
            prev_config = EXPERIENCE_LEVELS[prev_level]
            title = f"{prev_config['title_prefix']}{random.choice(IT_ROLES)}"
            employer = random.choice(IT_EMPLOYERS)

        experience.append({
            "title": title,
            "employer": employer,
            "start_date": start,
            "end_date": end,
            "tech_stack": [random.choice(stack["primary"])] + random.sample(stack["skills"], min(4, len(stack["skills"]))),
            "achievements": generate_achievements(IT_ACHIEVEMENTS, random.randint(2, 4))
        })

    # Select certifications based on experience
    num_certs = min(years_exp // 3, 4)
    certifications = random.sample(stack["certifications"], min(num_certs, len(stack["certifications"]))) if num_certs > 0 else []

    # Education
    degree = random.choice([d for d in DEGREES if d[1] in ["Computer Science", "Information Technology", "Software Engineering", "Data Science", "Mathematics"]])
    if years_exp > 8 and random.random() > 0.6:
        # Add MBA for senior folks
        education = [
            {"degree": "MBA", "field": "Business Administration", "university": random.choice(UNIVERSITIES)},
            {"degree": degree[0], "field": degree[1], "university": random.choice(UNIVERSITIES)}
        ]
    else:
        education = [{"degree": degree[0], "field": degree[1], "university": random.choice(UNIVERSITIES)}]

    # Skills
    technical_skills = [random.choice(stack["primary"])] + random.sample(stack["skills"], min(8, len(stack["skills"])))
    soft_skills = random.sample(SOFT_SKILLS, random.randint(3, 6))

    return {
        "id": f"gen_it_resume_{resume_id:03d}",
        "domain": "technology",
        "personal_info": {
            "name": f"{first_name} {last_name}",
            "email": f"{first_name.lower()}.{last_name.lower()}@email.com",
            "phone": f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}",
            "location": random.choice(LOCATIONS),
            "linkedin": f"linkedin.com/in/{first_name.lower()}{last_name.lower()}"
        },
        "summary": f"{years_exp}+ years of experience in {stack_name} technologies. "
                   f"Expertise in {', '.join(random.sample(stack['skills'], min(3, len(stack['skills']))))}. "
                   f"Proven track record of delivering scalable solutions and leading technical teams.",
        "experience_level": level,
        "years_experience": years_exp,
        "primary_tech_stack": random.choice(stack["primary"]),
        "tech_specialization": stack_name,
        "experience": experience,
        "education": education,
        "certifications": certifications,
        "skills": {
            "technical": technical_skills,
            "soft": soft_skills
        }
    }


def generate_business_resume(resume_id: int) -> Dict[str, Any]:
    """Generate a Business professional resume."""
    level = select_experience_level()
    level_config = EXPERIENCE_LEVELS[level]
    years_exp = random.randint(*level_config["years"])

    # Select specialty
    specialty_name = random.choice(list(BUSINESS_SPECIALTIES.keys()))
    specialty = BUSINESS_SPECIALTIES[specialty_name]

    # Generate personal info
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)

    # Select role appropriate to level
    if level in ["director", "vp"]:
        if specialty_name == "operations":
            base_role = random.choice(["Operations", "Business Operations", "Strategy"])
        else:
            base_role = random.choice(["Business", "Strategy", "Product", "Program"])
    else:
        base_role = random.choice([r for r in BUSINESS_ROLES if specialty_name.replace("_", " ") in r.lower() or "business" in r.lower() or "manager" in r.lower()])

    current_title = f"{level_config['title_prefix']}{base_role}" if level not in ["entry", "junior", "mid"] else base_role

    # Generate experience
    num_roles = min(years_exp // 2 + 1, 5)
    dates = generate_experience_dates(years_exp, num_roles)

    experience = []
    for i, (start, end) in enumerate(dates):
        if i == 0:
            title = current_title
            employer = random.choice(BUSINESS_EMPLOYERS)
        else:
            title = random.choice(BUSINESS_ROLES)
            employer = random.choice(BUSINESS_EMPLOYERS)

        experience.append({
            "title": title,
            "employer": employer,
            "start_date": start,
            "end_date": end,
            "focus_areas": random.sample(specialty["skills"], min(4, len(specialty["skills"]))),
            "achievements": generate_achievements(BUSINESS_ACHIEVEMENTS, random.randint(2, 4))
        })

    # Certifications
    num_certs = min(years_exp // 4, 3)
    certifications = random.sample(specialty["certifications"], min(num_certs, len(specialty["certifications"]))) if num_certs > 0 else []

    # Education
    degree = random.choice([d for d in DEGREES if d[1] in ["Business Administration", "Economics", "Finance", "Marketing"]])
    if years_exp > 6 and random.random() > 0.4:
        education = [
            {"degree": "MBA", "field": "Business Administration", "university": random.choice(UNIVERSITIES)},
            {"degree": degree[0], "field": degree[1], "university": random.choice(UNIVERSITIES)}
        ]
    else:
        education = [{"degree": degree[0], "field": degree[1], "university": random.choice(UNIVERSITIES)}]

    # Skills
    technical_skills = random.sample(specialty["skills"], min(8, len(specialty["skills"])))
    soft_skills = random.sample(SOFT_SKILLS, random.randint(4, 7))

    return {
        "id": f"gen_biz_resume_{resume_id:03d}",
        "domain": "business",
        "personal_info": {
            "name": f"{first_name} {last_name}",
            "email": f"{first_name.lower()}.{last_name.lower()}@email.com",
            "phone": f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}",
            "location": random.choice(LOCATIONS),
            "linkedin": f"linkedin.com/in/{first_name.lower()}{last_name.lower()}"
        },
        "summary": f"Results-driven {specialty_name.replace('_', ' ')} professional with {years_exp}+ years of experience. "
                   f"Expertise in {', '.join(random.sample(specialty['skills'], min(3, len(specialty['skills']))))}. "
                   f"Track record of driving business outcomes and leading cross-functional initiatives.",
        "experience_level": level,
        "years_experience": years_exp,
        "primary_specialty": specialty_name,
        "experience": experience,
        "education": education,
        "certifications": certifications,
        "skills": {
            "professional": technical_skills,
            "soft": soft_skills
        }
    }


def generate_marketing_resume(resume_id: int) -> Dict[str, Any]:
    """Generate a Marketing professional resume."""
    level = select_experience_level()
    level_config = EXPERIENCE_LEVELS[level]
    years_exp = random.randint(*level_config["years"])

    # Select specialty
    specialty_name = random.choice(list(MARKETING_SPECIALTIES.keys()))
    specialty = MARKETING_SPECIALTIES[specialty_name]

    # Generate personal info
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)

    # Select role
    if level in ["director", "vp"]:
        base_role = random.choice(["Marketing", "Growth", "Brand", "Demand Generation"])
    else:
        base_role = random.choice([r for r in MARKETING_ROLES if specialty_name.replace("_", " ") in r.lower() or "marketing" in r.lower()])

    current_title = f"{level_config['title_prefix']}{base_role}" if level not in ["entry", "junior", "mid"] else base_role

    # Generate experience
    num_roles = min(years_exp // 2 + 1, 5)
    dates = generate_experience_dates(years_exp, num_roles)

    experience = []
    for i, (start, end) in enumerate(dates):
        if i == 0:
            title = current_title
            employer = random.choice(MARKETING_EMPLOYERS)
        else:
            title = random.choice(MARKETING_ROLES)
            employer = random.choice(MARKETING_EMPLOYERS)

        experience.append({
            "title": title,
            "employer": employer,
            "start_date": start,
            "end_date": end,
            "channels": random.sample(specialty["skills"], min(4, len(specialty["skills"]))),
            "achievements": generate_achievements(MARKETING_ACHIEVEMENTS, random.randint(2, 4))
        })

    # Certifications
    num_certs = min(years_exp // 3, 3)
    certifications = random.sample(specialty["certifications"], min(num_certs, len(specialty["certifications"]))) if num_certs > 0 else []

    # Education
    degree = random.choice([d for d in DEGREES if d[1] in ["Marketing", "Communications", "Business Administration", "Psychology"]])
    if years_exp > 8 and random.random() > 0.5:
        education = [
            {"degree": "MBA", "field": "Marketing", "university": random.choice(UNIVERSITIES)},
            {"degree": degree[0], "field": degree[1], "university": random.choice(UNIVERSITIES)}
        ]
    else:
        education = [{"degree": degree[0], "field": degree[1], "university": random.choice(UNIVERSITIES)}]

    # Skills
    technical_skills = random.sample(specialty["skills"], min(8, len(specialty["skills"])))
    soft_skills = random.sample(SOFT_SKILLS, random.randint(4, 6))

    return {
        "id": f"gen_mkt_resume_{resume_id:03d}",
        "domain": "marketing",
        "personal_info": {
            "name": f"{first_name} {last_name}",
            "email": f"{first_name.lower()}.{last_name.lower()}@email.com",
            "phone": f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}",
            "location": random.choice(LOCATIONS),
            "linkedin": f"linkedin.com/in/{first_name.lower()}{last_name.lower()}"
        },
        "summary": f"Creative and data-driven {specialty_name.replace('_', ' ')} professional with {years_exp}+ years of experience. "
                   f"Expert in {', '.join(random.sample(specialty['skills'], min(3, len(specialty['skills']))))}. "
                   f"Proven ability to drive growth and build brand awareness.",
        "experience_level": level,
        "years_experience": years_exp,
        "primary_specialty": specialty_name,
        "experience": experience,
        "education": education,
        "certifications": certifications,
        "skills": {
            "marketing": technical_skills,
            "soft": soft_skills
        }
    }


# =============================================================================
# JOB DESCRIPTION GENERATION
# =============================================================================

JOB_TEMPLATES = {
    # IT Jobs (10)
    "it": [
        {
            "title": "Senior Software Engineer",
            "level": "senior",
            "department": "Engineering",
            "requirements": {
                "years_min": 5,
                "years_max": 10,
                "education": "BS in Computer Science or related field",
                "skills_required": ["Python", "Java", "Microservices", "REST APIs", "SQL"],
                "skills_preferred": ["Kubernetes", "AWS", "GraphQL"],
            }
        },
        {
            "title": "Staff Software Engineer",
            "level": "lead",
            "department": "Engineering",
            "requirements": {
                "years_min": 8,
                "years_max": 15,
                "education": "BS/MS in Computer Science",
                "skills_required": ["System Design", "Architecture", "Python", "Java", "Cloud"],
                "skills_preferred": ["Team Leadership", "Technical Strategy"],
            }
        },
        {
            "title": "Junior Data Analyst",
            "level": "junior",
            "department": "Data",
            "requirements": {
                "years_min": 0,
                "years_max": 2,
                "education": "BS in Statistics, Math, or related field",
                "skills_required": ["SQL", "Excel", "Python", "Data Visualization"],
                "skills_preferred": ["Tableau", "Power BI"],
            }
        },
        {
            "title": "Data Engineer",
            "level": "mid",
            "department": "Data",
            "requirements": {
                "years_min": 3,
                "years_max": 6,
                "education": "BS in Computer Science or related field",
                "skills_required": ["Python", "SQL", "ETL", "Spark", "Airflow"],
                "skills_preferred": ["Databricks", "Snowflake", "dbt"],
            }
        },
        {
            "title": "DevOps Engineer",
            "level": "mid",
            "department": "Platform",
            "requirements": {
                "years_min": 3,
                "years_max": 7,
                "education": "BS in Computer Science or equivalent experience",
                "skills_required": ["Kubernetes", "Docker", "CI/CD", "Terraform", "AWS/GCP"],
                "skills_preferred": ["ArgoCD", "Prometheus", "Grafana"],
            }
        },
        {
            "title": "Security Engineer",
            "level": "senior",
            "department": "Security",
            "requirements": {
                "years_min": 5,
                "years_max": 10,
                "education": "BS in Cybersecurity or related field",
                "skills_required": ["Security Architecture", "Penetration Testing", "SIEM", "IAM"],
                "skills_preferred": ["CISSP", "AWS Security Specialty"],
            }
        },
        {
            "title": "Engineering Manager",
            "level": "director",
            "department": "Engineering",
            "requirements": {
                "years_min": 8,
                "years_max": 15,
                "education": "BS/MS in Computer Science, MBA preferred",
                "skills_required": ["Team Leadership", "Agile", "Technical Strategy", "Hiring"],
                "skills_preferred": ["Budget Management", "Executive Communication"],
            }
        },
        {
            "title": "VP of Engineering",
            "level": "vp",
            "department": "Engineering",
            "requirements": {
                "years_min": 12,
                "years_max": 20,
                "education": "BS/MS in Computer Science, MBA preferred",
                "skills_required": ["Org Design", "Technical Strategy", "Executive Leadership", "P&L"],
                "skills_preferred": ["Public Company Experience", "Board Presentation"],
            }
        },
        {
            "title": "Solutions Architect",
            "level": "senior",
            "department": "Engineering",
            "requirements": {
                "years_min": 7,
                "years_max": 12,
                "education": "BS in Computer Science or related field",
                "skills_required": ["Cloud Architecture", "System Design", "Customer Facing", "AWS/Azure/GCP"],
                "skills_preferred": ["Pre-sales Experience", "Technical Writing"],
            }
        },
        {
            "title": "QA Automation Engineer",
            "level": "mid",
            "department": "Engineering",
            "requirements": {
                "years_min": 3,
                "years_max": 6,
                "education": "BS in Computer Science or related field",
                "skills_required": ["Selenium", "Python", "API Testing", "CI/CD Integration"],
                "skills_preferred": ["Playwright", "Performance Testing"],
            }
        },
    ],
    # Marketing Jobs (8)
    "marketing": [
        {
            "title": "Digital Marketing Manager",
            "level": "mid",
            "department": "Marketing",
            "requirements": {
                "years_min": 4,
                "years_max": 7,
                "education": "BS in Marketing or related field",
                "skills_required": ["Google Ads", "Facebook Ads", "SEO", "Marketing Automation"],
                "skills_preferred": ["HubSpot", "Marketo"],
            }
        },
        {
            "title": "Content Marketing Specialist",
            "level": "junior",
            "department": "Marketing",
            "requirements": {
                "years_min": 1,
                "years_max": 3,
                "education": "BS in Communications, Marketing, or English",
                "skills_required": ["Content Writing", "SEO", "Social Media", "WordPress"],
                "skills_preferred": ["Video Production", "Graphic Design"],
            }
        },
        {
            "title": "Senior Product Marketing Manager",
            "level": "senior",
            "department": "Marketing",
            "requirements": {
                "years_min": 6,
                "years_max": 10,
                "education": "BS in Marketing/Business, MBA preferred",
                "skills_required": ["Product Positioning", "Go-to-Market", "Sales Enablement", "Competitive Analysis"],
                "skills_preferred": ["B2B SaaS Experience", "Technical Background"],
            }
        },
        {
            "title": "Growth Marketing Lead",
            "level": "lead",
            "department": "Marketing",
            "requirements": {
                "years_min": 5,
                "years_max": 9,
                "education": "BS in Marketing, Analytics, or related field",
                "skills_required": ["A/B Testing", "User Acquisition", "Analytics", "Paid Media"],
                "skills_preferred": ["SQL", "Product Analytics Tools"],
            }
        },
        {
            "title": "Director of Brand Marketing",
            "level": "director",
            "department": "Marketing",
            "requirements": {
                "years_min": 10,
                "years_max": 15,
                "education": "BS in Marketing, MBA preferred",
                "skills_required": ["Brand Strategy", "Campaign Management", "Team Leadership", "Agency Management"],
                "skills_preferred": ["Consumer Brand Experience", "Global Campaigns"],
            }
        },
        {
            "title": "Marketing Analytics Manager",
            "level": "mid",
            "department": "Marketing",
            "requirements": {
                "years_min": 4,
                "years_max": 7,
                "education": "BS in Statistics, Analytics, or Marketing",
                "skills_required": ["SQL", "Google Analytics", "Tableau", "Marketing Attribution"],
                "skills_preferred": ["Python", "Looker", "Amplitude"],
            }
        },
        {
            "title": "VP of Marketing",
            "level": "vp",
            "department": "Marketing",
            "requirements": {
                "years_min": 12,
                "years_max": 20,
                "education": "MBA preferred",
                "skills_required": ["Marketing Strategy", "Team Building", "Budget Management", "Executive Presence"],
                "skills_preferred": ["Public Company Experience", "IPO Experience"],
            }
        },
        {
            "title": "Demand Generation Manager",
            "level": "mid",
            "department": "Marketing",
            "requirements": {
                "years_min": 3,
                "years_max": 6,
                "education": "BS in Marketing or Business",
                "skills_required": ["Lead Generation", "Email Marketing", "Marketing Automation", "CRM"],
                "skills_preferred": ["Salesforce", "Account-Based Marketing"],
            }
        },
    ],
    # Business Jobs (12)
    "business": [
        {
            "title": "Business Analyst",
            "level": "mid",
            "department": "Business Operations",
            "requirements": {
                "years_min": 2,
                "years_max": 5,
                "education": "BS in Business, Analytics, or related field",
                "skills_required": ["Requirements Gathering", "SQL", "Process Mapping", "Stakeholder Management"],
                "skills_preferred": ["JIRA", "Confluence", "Agile"],
            }
        },
        {
            "title": "Senior Business Analyst",
            "level": "senior",
            "department": "Business Operations",
            "requirements": {
                "years_min": 5,
                "years_max": 9,
                "education": "BS in Business, CBAP preferred",
                "skills_required": ["Complex Requirements", "Business Case Development", "UAT", "Process Improvement"],
                "skills_preferred": ["Six Sigma", "Product Management"],
            }
        },
        {
            "title": "Product Manager",
            "level": "mid",
            "department": "Product",
            "requirements": {
                "years_min": 3,
                "years_max": 6,
                "education": "BS in Computer Science, Business, or related field",
                "skills_required": ["Product Roadmapping", "User Research", "Agile", "Prioritization"],
                "skills_preferred": ["Technical Background", "Data Analysis"],
            }
        },
        {
            "title": "Senior Product Manager",
            "level": "senior",
            "department": "Product",
            "requirements": {
                "years_min": 6,
                "years_max": 10,
                "education": "BS in technical field, MBA preferred",
                "skills_required": ["Product Strategy", "Cross-functional Leadership", "Metrics-driven", "Go-to-Market"],
                "skills_preferred": ["Platform Experience", "B2B SaaS"],
            }
        },
        {
            "title": "Project Manager",
            "level": "mid",
            "department": "PMO",
            "requirements": {
                "years_min": 3,
                "years_max": 6,
                "education": "BS in Business, PMP preferred",
                "skills_required": ["Project Planning", "Risk Management", "Stakeholder Communication", "MS Project"],
                "skills_preferred": ["Agile Certification", "Technology Projects"],
            }
        },
        {
            "title": "Program Manager",
            "level": "senior",
            "department": "PMO",
            "requirements": {
                "years_min": 7,
                "years_max": 12,
                "education": "BS/MBA, PMP required",
                "skills_required": ["Program Management", "Portfolio Management", "Executive Reporting", "Budget Management"],
                "skills_preferred": ["Technology Transformation", "Change Management"],
            }
        },
        {
            "title": "Operations Manager",
            "level": "mid",
            "department": "Operations",
            "requirements": {
                "years_min": 4,
                "years_max": 8,
                "education": "BS in Business or Operations",
                "skills_required": ["Process Optimization", "Team Management", "KPI Tracking", "Vendor Management"],
                "skills_preferred": ["Six Sigma", "Lean Management"],
            }
        },
        {
            "title": "Director of Operations",
            "level": "director",
            "department": "Operations",
            "requirements": {
                "years_min": 10,
                "years_max": 15,
                "education": "BS/MBA in Operations or Business",
                "skills_required": ["Operations Strategy", "P&L Management", "Team Building", "Process Excellence"],
                "skills_preferred": ["Global Operations", "M&A Integration"],
            }
        },
        {
            "title": "Chief of Staff",
            "level": "senior",
            "department": "Executive",
            "requirements": {
                "years_min": 6,
                "years_max": 12,
                "education": "MBA preferred",
                "skills_required": ["Executive Support", "Strategic Planning", "Cross-functional Coordination", "Communication"],
                "skills_preferred": ["Consulting Background", "Board Experience"],
            }
        },
        {
            "title": "VP of Business Development",
            "level": "vp",
            "department": "Business Development",
            "requirements": {
                "years_min": 12,
                "years_max": 20,
                "education": "MBA preferred",
                "skills_required": ["Partnership Strategy", "Deal Negotiation", "Revenue Growth", "Executive Relationships"],
                "skills_preferred": ["M&A Experience", "International Expansion"],
            }
        },
        {
            "title": "Strategy Manager",
            "level": "mid",
            "department": "Strategy",
            "requirements": {
                "years_min": 3,
                "years_max": 7,
                "education": "MBA or top consulting experience",
                "skills_required": ["Strategic Analysis", "Financial Modeling", "Market Research", "Executive Presentation"],
                "skills_preferred": ["Top-tier Consulting", "Private Equity"],
            }
        },
        {
            "title": "Director of Strategy",
            "level": "director",
            "department": "Strategy",
            "requirements": {
                "years_min": 8,
                "years_max": 14,
                "education": "MBA from top program",
                "skills_required": ["Corporate Strategy", "M&A Due Diligence", "Board Presentation", "Team Leadership"],
                "skills_preferred": ["Industry Expertise", "Investment Banking"],
            }
        },
    ]
}


def generate_job_description(job_template: Dict, job_id: int, domain: str) -> Dict[str, Any]:
    """Generate a full job description from a template."""

    employer = random.choice(
        IT_EMPLOYERS if domain == "it" else
        MARKETING_EMPLOYERS if domain == "marketing" else
        BUSINESS_EMPLOYERS
    )

    location = random.choice(LOCATIONS)
    is_remote = "Remote" in location or random.random() > 0.7

    # Salary ranges by level
    salary_ranges = {
        "entry": (50000, 75000),
        "junior": (65000, 95000),
        "mid": (90000, 140000),
        "senior": (130000, 200000),
        "lead": (160000, 240000),
        "director": (200000, 320000),
        "vp": (280000, 500000),
    }

    level = job_template["level"]
    salary_min, salary_max = salary_ranges.get(level, (100000, 150000))

    # Generate description
    responsibilities = [
        f"Lead and execute {job_template['department'].lower()} initiatives aligned with company strategy",
        f"Collaborate with cross-functional teams to deliver high-impact projects",
        f"Develop and maintain relationships with key stakeholders",
        f"Drive continuous improvement in processes and outcomes",
        f"Mentor and develop team members" if level in ["senior", "lead", "director", "vp"] else "Contribute to team goals and learn from senior colleagues",
    ]

    if level in ["director", "vp"]:
        responsibilities.extend([
            "Set strategic direction and priorities for the organization",
            "Manage budget and resource allocation",
            "Report to executive leadership on progress and outcomes",
        ])

    return {
        "id": f"gen_{domain}_job_{job_id:03d}",
        "domain": domain,
        "title": job_template["title"],
        "employer": employer,
        "department": job_template["department"],
        "location": location,
        "remote": is_remote,
        "employment_type": "Full-time",
        "experience_level": level,
        "requirements": job_template["requirements"],
        "salary_range": {
            "min": salary_min,
            "max": salary_max,
            "currency": "USD"
        },
        "responsibilities": responsibilities,
        "benefits": [
            "Competitive salary and equity",
            "Comprehensive health, dental, and vision insurance",
            "401(k) with company match",
            "Flexible PTO policy",
            "Professional development budget",
            "Remote work options" if is_remote else "Hybrid work environment"
        ],
        "posted_date": (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d"),
    }


# =============================================================================
# MAIN GENERATION
# =============================================================================

def generate_all_resumes(count: int = 100) -> List[Dict]:
    """Generate all resumes with domain distribution."""
    resumes = []

    # Distribution: 40% IT, 35% Business, 25% Marketing
    it_count = int(count * 0.40)
    biz_count = int(count * 0.35)
    mkt_count = count - it_count - biz_count

    print(f"Generating {it_count} IT resumes...")
    for i in range(it_count):
        resumes.append(generate_it_resume(i + 1))

    print(f"Generating {biz_count} Business resumes...")
    for i in range(biz_count):
        resumes.append(generate_business_resume(i + 1))

    print(f"Generating {mkt_count} Marketing resumes...")
    for i in range(mkt_count):
        resumes.append(generate_marketing_resume(i + 1))

    return resumes


def generate_all_jobs() -> List[Dict]:
    """Generate all job descriptions."""
    jobs = []
    job_id = 1

    for domain, templates in JOB_TEMPLATES.items():
        print(f"Generating {len(templates)} {domain} jobs...")
        for template in templates:
            jobs.append(generate_job_description(template, job_id, domain))
            job_id += 1

    return jobs


def save_data(resumes: List[Dict], jobs: List[Dict]):
    """Save generated data to JSON files."""
    # Create directories
    RESUMES_DIR.mkdir(parents=True, exist_ok=True)
    JOBS_DIR.mkdir(parents=True, exist_ok=True)

    # Save individual resume files
    for resume in resumes:
        filepath = RESUMES_DIR / f"{resume['id']}.json"
        with open(filepath, 'w') as f:
            json.dump(resume, f, indent=2)

    # Save individual job files
    for job in jobs:
        filepath = JOBS_DIR / f"{job['id']}.json"
        with open(filepath, 'w') as f:
            json.dump(job, f, indent=2)

    # Save combined files for easy loading
    with open(OUTPUT_DIR / "all_resumes.json", 'w') as f:
        json.dump(resumes, f, indent=2)

    with open(OUTPUT_DIR / "all_jobs.json", 'w') as f:
        json.dump(jobs, f, indent=2)

    print(f"\nSaved {len(resumes)} resumes to {RESUMES_DIR}")
    print(f"Saved {len(jobs)} jobs to {JOBS_DIR}")


def print_statistics(resumes: List[Dict], jobs: List[Dict]):
    """Print statistics about generated data."""
    print("\n" + "=" * 60)
    print("GENERATION STATISTICS")
    print("=" * 60)

    # Resume stats
    print("\nRESUMES:")
    print(f"  Total: {len(resumes)}")

    # By domain
    domains = {}
    for r in resumes:
        domains[r['domain']] = domains.get(r['domain'], 0) + 1
    for domain, count in sorted(domains.items()):
        print(f"  - {domain.title()}: {count}")

    # By experience level
    print("\n  By Experience Level:")
    levels = {}
    for r in resumes:
        level = r['experience_level']
        levels[level] = levels.get(level, 0) + 1
    for level in EXPERIENCE_LEVELS.keys():
        count = levels.get(level, 0)
        print(f"    - {level.title()}: {count}")

    # Years experience stats
    years = [r['years_experience'] for r in resumes]
    print(f"\n  Years Experience: {min(years)}-{max(years)} (avg: {sum(years)/len(years):.1f})")

    # Job stats
    print("\nJOBS:")
    print(f"  Total: {len(jobs)}")

    job_domains = {}
    for j in jobs:
        job_domains[j['domain']] = job_domains.get(j['domain'], 0) + 1
    for domain, count in sorted(job_domains.items()):
        print(f"  - {domain.title()}: {count}")

    # By level
    print("\n  By Level:")
    job_levels = {}
    for j in jobs:
        level = j['experience_level']
        job_levels[level] = job_levels.get(level, 0) + 1
    for level, count in sorted(job_levels.items(), key=lambda x: list(EXPERIENCE_LEVELS.keys()).index(x[0]) if x[0] in EXPERIENCE_LEVELS else 99):
        print(f"    - {level.title()}: {count}")

    print("\n" + "=" * 60)


def main():
    """Main entry point."""
    print("=" * 60)
    print("GENERALIZED TEST DATA GENERATOR")
    print("=" * 60)
    print("\nGenerating IT, Business, and Marketing test data...\n")

    # Generate data
    resumes = generate_all_resumes(100)
    jobs = generate_all_jobs()

    # Save data
    save_data(resumes, jobs)

    # Print statistics
    print_statistics(resumes, jobs)

    print("\nGeneration complete!")
    print(f"Data saved to: {OUTPUT_DIR.absolute()}")


if __name__ == "__main__":
    main()
