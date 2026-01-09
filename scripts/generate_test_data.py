#!/usr/bin/env python3
"""
Generate test data for Healthcare Implementation Resume Matching System.

Creates:
- 100 healthcare implementation professional resumes
- 20 EHR/hospital implementation job descriptions
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

# Healthcare-specific EHR systems and technologies
EHR_SYSTEMS = [
    "Epic", "Cerner", "MEDITECH", "Allscripts", "athenahealth", "eClinicalWorks",
    "NextGen Healthcare", "Greenway Health", "DrChrono", "Kareo", "Practice Fusion",
    "CureMD", "ChartLogic", "Amazing Charts", "PrognoCIS"
]

EPIC_MODULES = [
    "EpicCare Ambulatory", "EpicCare Inpatient", "Cadence", "Prelude", "Resolute",
    "Willow", "Beacon", "Radiant", "OpTime", "Stork", "ASAP", "Healthy Planet",
    "MyChart", "Care Everywhere", "Cogito", "Grand Central", "Tapestry"
]

CERNER_MODULES = [
    "PowerChart", "FirstNet", "SurgiNet", "PharmNet", "RadNet", "PathNet",
    "Millennium", "CommunityWorks", "Soarian", "HealtheIntent", "ITWorks"
]

HOSPITALS = [
    "Mayo Clinic", "Cleveland Clinic", "Johns Hopkins Hospital", "Massachusetts General Hospital",
    "UCLA Medical Center", "UCSF Medical Center", "NYU Langone Health", "Stanford Health Care",
    "Northwestern Memorial Hospital", "Cedars-Sinai Medical Center", "Mount Sinai Hospital",
    "Duke University Hospital", "Brigham and Women's Hospital", "University of Michigan Health",
    "Penn Medicine", "Houston Methodist Hospital", "Emory University Hospital",
    "Barnes-Jewish Hospital", "UPMC Presbyterian", "Vanderbilt University Medical Center",
    "University of Chicago Medical Center", "Rush University Medical Center",
    "Henry Ford Hospital", "Scripps Memorial Hospital", "Providence Health",
    "Kaiser Permanente", "Intermountain Healthcare", "Geisinger Medical Center",
    "Ochsner Medical Center", "Advocate Aurora Health", "Trinity Health",
    "CommonSpirit Health", "HCA Healthcare", "Tenet Healthcare", "Community Health Systems",
    "Memorial Hermann", "Northwell Health", "Atrium Health", "Baylor Scott & White",
    "Sutter Health", "Banner Health", "Christus Health", "Ascension Health"
]

HEALTH_CLINICS = [
    "Village Family Practice", "Community Health Partners", "Premier Medical Group",
    "Sunrise Health Center", "Valley Medical Associates", "Lakeside Medical Clinic",
    "Mountain View Health Center", "Riverside Family Medicine", "Coastal Health Services",
    "Metro Internal Medicine", "Suburban Medical Associates", "Downtown Health Clinic",
    "Wellness Medical Group", "Family Care Associates", "Regional Health Partners"
]

UNIVERSITIES = [
    "Johns Hopkins University", "Harvard University", "Stanford University",
    "University of Pennsylvania", "Duke University", "University of Michigan",
    "Columbia University", "Yale University", "UCLA", "UCSF",
    "Northwestern University", "University of Chicago", "Emory University",
    "University of Washington", "Vanderbilt University", "University of Pittsburgh",
    "Ohio State University", "University of Wisconsin", "Indiana University",
    "University of Minnesota", "Boston University", "George Washington University",
    "University of North Carolina", "University of Virginia", "University of Texas",
    "Arizona State University", "University of Colorado", "University of Florida",
    "University of Illinois", "Temple University", "Drexel University"
]

DEGREES = [
    ("Bachelor of Science in Health Informatics", "BS"),
    ("Bachelor of Science in Healthcare Administration", "BS"),
    ("Bachelor of Science in Information Technology", "BS"),
    ("Bachelor of Science in Computer Science", "BS"),
    ("Bachelor of Science in Nursing", "BSN"),
    ("Bachelor of Arts in Healthcare Management", "BA"),
    ("Master of Health Informatics", "MHI"),
    ("Master of Healthcare Administration", "MHA"),
    ("Master of Business Administration", "MBA"),
    ("Master of Science in Information Systems", "MS"),
    ("Master of Science in Health Information Management", "MS"),
    ("Master of Public Health", "MPH"),
    ("Doctor of Nursing Practice", "DNP"),
    ("PhD in Health Informatics", "PhD")
]

CERTIFICATIONS = [
    "Epic Certified - EpicCare Ambulatory",
    "Epic Certified - EpicCare Inpatient",
    "Epic Certified - Cadence",
    "Epic Certified - Willow",
    "Epic Certified - Beacon",
    "Cerner Certified - PowerChart",
    "Cerner Certified - Millennium",
    "Project Management Professional (PMP)",
    "Certified Associate in Healthcare Information and Management Systems (CAHIMS)",
    "Certified Professional in Healthcare Information and Management Systems (CPHIMS)",
    "Certified Health Data Analyst (CHDA)",
    "Registered Health Information Administrator (RHIA)",
    "Certified Information Systems Security Professional (CISSP)",
    "ITIL Foundation Certification",
    "Six Sigma Green Belt",
    "Six Sigma Black Belt",
    "Certified Scrum Master (CSM)",
    "Certified ScrumMaster (CSM)",
    "AWS Certified Solutions Architect",
    "HL7 FHIR Certification"
]

JOB_TITLES = [
    "EHR Implementation Consultant",
    "Epic Implementation Analyst",
    "Cerner Implementation Specialist",
    "Healthcare IT Project Manager",
    "Clinical Informatics Specialist",
    "Health Information Systems Analyst",
    "EHR Training Specialist",
    "Healthcare Integration Engineer",
    "Clinical Applications Analyst",
    "Health IT Implementation Manager",
    "Medical Informatics Consultant",
    "Healthcare Systems Analyst",
    "EHR Support Analyst",
    "Clinical Workflow Analyst",
    "Health Information Manager",
    "Healthcare Data Analyst",
    "Revenue Cycle Implementation Specialist",
    "Practice Management Consultant"
]

SKILLS = [
    "EHR Implementation", "Clinical Workflow Analysis", "Healthcare IT",
    "Project Management", "Change Management", "Training Development",
    "Data Migration", "System Integration", "HL7 Interfaces", "FHIR APIs",
    "SQL", "Python", "Healthcare Analytics", "Revenue Cycle Management",
    "Clinical Decision Support", "Patient Portal Implementation",
    "Go-Live Support", "Optimization", "Report Writing", "Crystal Reports",
    "Business Intelligence", "Tableau", "Power BI", "Process Improvement",
    "Agile Methodology", "Scrum", "HIPAA Compliance", "ICD-10",
    "CPT Coding", "Medical Terminology", "Clinical Documentation",
    "Interoperability", "Health Information Exchange", "Population Health",
    "Value-Based Care", "Telehealth Implementation", "Mobile Health",
    "User Acceptance Testing", "System Configuration", "Build Validation"
]

IMPLEMENTATION_ACHIEVEMENTS = [
    "Led successful go-live for {beds}-bed hospital with zero critical issues",
    "Managed implementation for {clinics} ambulatory clinics across {states} states",
    "Reduced average patient wait time by {percent}% through workflow optimization",
    "Trained {users}+ end users with {satisfaction}% satisfaction rating",
    "Completed data migration of {records}M+ patient records with 99.9% accuracy",
    "Achieved {adoption}% clinician adoption rate within first {months} months",
    "Decreased claim denial rate by {percent}% through revenue cycle optimization",
    "Implemented {modules} Epic/Cerner modules on time and under budget",
    "Coordinated go-live support for {providers}+ providers across {locations} locations",
    "Designed clinical workflows that improved documentation efficiency by {percent}%",
    "Built {interfaces}+ HL7 interfaces connecting to external systems",
    "Led optimization project resulting in ${savings}K annual cost savings",
    "Managed cross-functional team of {team} analysts and trainers",
    "Developed training curriculum adopted as enterprise standard",
    "Achieved HIMSS Stage {stage} recognition for implemented facility"
]


def generate_phone():
    """Generate a random phone number."""
    return f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"


def generate_email(first_name, last_name):
    """Generate email address."""
    domains = ["gmail.com", "outlook.com", "yahoo.com", "healthcaremail.com", "consultant.net"]
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
        ("Boston", "MA"), ("New York", "NY"), ("Chicago", "IL"), ("Los Angeles", "CA"),
        ("Houston", "TX"), ("Phoenix", "AZ"), ("Philadelphia", "PA"), ("San Antonio", "TX"),
        ("San Diego", "CA"), ("Dallas", "TX"), ("San Jose", "CA"), ("Austin", "TX"),
        ("Jacksonville", "FL"), ("Fort Worth", "TX"), ("Columbus", "OH"), ("Charlotte", "NC"),
        ("Seattle", "WA"), ("Denver", "CO"), ("Nashville", "TN"), ("Baltimore", "MD"),
        ("Portland", "OR"), ("Milwaukee", "WI"), ("Las Vegas", "NV"), ("Atlanta", "GA"),
        ("Minneapolis", "MN"), ("Cleveland", "OH"), ("Detroit", "MI"), ("Salt Lake City", "UT")
    ]
    city, state = random.choice(cities)
    return f"{city}, {state}"


def generate_work_experience(years_experience):
    """Generate work history for a resume."""
    experiences = []
    current_year = 2024
    years_remaining = years_experience

    while years_remaining > 0:
        duration = min(random.randint(1, 5), years_remaining)
        end_year = current_year
        start_year = end_year - duration

        is_current = len(experiences) == 0

        # Choose employer type
        employer_type = random.choices(
            ["hospital", "clinic", "consulting", "vendor"],
            weights=[40, 20, 30, 10]
        )[0]

        if employer_type == "hospital":
            employer = random.choice(HOSPITALS)
        elif employer_type == "clinic":
            employer = random.choice(HEALTH_CLINICS)
        elif employer_type == "consulting":
            employer = random.choice([
                "Nordic Consulting", "Tegria", "Impact Advisors", "Pivot Point Consulting",
                "ECG Management Consultants", "Huron Consulting", "Deloitte Healthcare",
                "Accenture Health", "KPMG Healthcare", "PwC Health Industries",
                "Leidos Health", "Conduent Healthcare", "Optum Advisory Services"
            ])
        else:
            employer = random.choice(EHR_SYSTEMS + ["Health Catalyst", "Medidata", "Veradigm"])

        title = random.choice(JOB_TITLES)

        # Seniority based on years in career
        total_years = years_experience - years_remaining + duration
        if total_years > 10:
            title = random.choice(["Senior ", "Lead ", "Principal ", "Director of "]) + title
        elif total_years > 5:
            title = random.choice(["Senior ", "Lead ", ""]) + title

        # Generate achievements
        achievements = []
        num_achievements = random.randint(2, 4)
        used_templates = set()

        for _ in range(num_achievements):
            template = random.choice(IMPLEMENTATION_ACHIEVEMENTS)
            if template not in used_templates:
                used_templates.add(template)
                achievement = template.format(
                    beds=random.choice([150, 200, 300, 400, 500, 750, 1000]),
                    clinics=random.randint(5, 50),
                    states=random.randint(2, 10),
                    percent=random.randint(15, 45),
                    users=random.choice([100, 200, 500, 1000, 2000]),
                    satisfaction=random.randint(92, 99),
                    records=random.choice([1, 2, 5, 10]),
                    adoption=random.randint(85, 98),
                    months=random.randint(2, 6),
                    modules=random.randint(3, 12),
                    providers=random.choice([50, 100, 200, 500]),
                    locations=random.randint(3, 20),
                    interfaces=random.randint(10, 50),
                    savings=random.choice([50, 100, 200, 500, 1000]),
                    team=random.randint(3, 15),
                    stage=random.randint(5, 7)
                )
                achievements.append(achievement)

        # Add EHR-specific responsibilities
        primary_ehr = random.choice(EHR_SYSTEMS[:5])  # Focus on major systems
        if primary_ehr == "Epic":
            modules_used = random.sample(EPIC_MODULES, min(4, len(EPIC_MODULES)))
        elif primary_ehr == "Cerner":
            modules_used = random.sample(CERNER_MODULES, min(4, len(CERNER_MODULES)))
        else:
            modules_used = [f"{primary_ehr} Core", f"{primary_ehr} Analytics"]

        experience = {
            "title": title,
            "employer": employer,
            "location": generate_address(),
            "start_date": f"{random.choice(['January', 'March', 'June', 'September'])} {start_year}",
            "end_date": "Present" if is_current else f"{random.choice(['February', 'May', 'August', 'December'])} {end_year}",
            "ehr_systems": [primary_ehr],
            "modules": modules_used,
            "achievements": achievements
        }

        experiences.append(experience)
        current_year = start_year
        years_remaining -= duration

    return experiences


def generate_education(years_experience):
    """Generate education history."""
    education = []

    # Everyone has at least a bachelor's
    bachelors = random.choice([d for d in DEGREES if d[1] in ["BS", "BA", "BSN"]])
    grad_year = 2024 - years_experience - random.randint(0, 3)

    education.append({
        "degree": bachelors[0],
        "institution": random.choice(UNIVERSITIES),
        "graduation_year": grad_year,
        "gpa": round(random.uniform(3.2, 4.0), 2) if random.random() > 0.5 else None
    })

    # 60% chance of master's if 5+ years experience
    if years_experience >= 5 and random.random() < 0.6:
        masters = random.choice([d for d in DEGREES if d[1] in ["MHI", "MHA", "MBA", "MS", "MPH"]])
        education.insert(0, {
            "degree": masters[0],
            "institution": random.choice(UNIVERSITIES),
            "graduation_year": grad_year + random.randint(3, 6),
            "gpa": round(random.uniform(3.5, 4.0), 2) if random.random() > 0.6 else None
        })

    # 10% chance of doctorate if 10+ years
    if years_experience >= 10 and random.random() < 0.1:
        doctorate = random.choice([d for d in DEGREES if d[1] in ["DNP", "PhD"]])
        education.insert(0, {
            "degree": doctorate[0],
            "institution": random.choice(UNIVERSITIES),
            "graduation_year": grad_year + random.randint(6, 10),
            "gpa": None
        })

    return education


def generate_resume(resume_id):
    """Generate a single resume."""
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    years_experience = random.randint(2, 20)

    # Select certifications based on experience
    num_certs = min(random.randint(1, 6), years_experience // 2 + 1)
    certs = random.sample(CERTIFICATIONS, num_certs)

    # Select skills
    num_skills = random.randint(8, 15)
    skills = random.sample(SKILLS, num_skills)

    # Add EHR-specific skills
    primary_ehr = random.choice(EHR_SYSTEMS[:5])
    skills.insert(0, primary_ehr)
    if primary_ehr == "Epic":
        skills.extend(random.sample(EPIC_MODULES, min(3, len(EPIC_MODULES))))
    elif primary_ehr == "Cerner":
        skills.extend(random.sample(CERNER_MODULES, min(3, len(CERNER_MODULES))))

    resume = {
        "id": f"resume_{resume_id:03d}",
        "personal_info": {
            "name": f"{first_name} {last_name}",
            "email": generate_email(first_name, last_name),
            "phone": generate_phone(),
            "location": generate_address(),
            "linkedin": generate_linkedin(first_name, last_name)
        },
        "summary": generate_professional_summary(first_name, years_experience, primary_ehr),
        "years_experience": years_experience,
        "primary_ehr_system": primary_ehr,
        "experience": generate_work_experience(years_experience),
        "education": generate_education(years_experience),
        "certifications": certs,
        "skills": list(set(skills))  # Remove duplicates
    }

    return resume


def generate_professional_summary(first_name, years_exp, primary_ehr):
    """Generate a professional summary statement."""
    templates = [
        f"Results-driven healthcare IT professional with {years_exp}+ years of experience in EHR implementation and optimization. Specialized in {primary_ehr} system deployments across acute care and ambulatory settings. Proven track record of successful go-lives and high clinician adoption rates.",

        f"Experienced healthcare implementation consultant with {years_exp} years leading {primary_ehr} implementations for hospitals and health systems. Expert in clinical workflow analysis, training development, and change management. Passionate about leveraging technology to improve patient care.",

        f"Healthcare informatics specialist with {years_exp}+ years of hands-on experience implementing and optimizing {primary_ehr} EHR systems. Strong background in project management, data migration, and system integration. Committed to delivering solutions that enhance clinical efficiency.",

        f"Dedicated EHR implementation professional bringing {years_exp} years of experience in {primary_ehr} deployments. Skilled in leading cross-functional teams, managing complex projects, and ensuring successful system adoption. Track record of on-time, on-budget implementations.",

        f"Clinical informatics expert with {years_exp}+ years specializing in {primary_ehr} implementation and optimization. Extensive experience in revenue cycle, clinical documentation, and population health initiatives. Known for building strong relationships with clinical stakeholders."
    ]
    return random.choice(templates)


def generate_job_description(job_id):
    """Generate a single job description."""

    # Job types with characteristics
    job_types = [
        {
            "category": "implementation_consultant",
            "titles": ["EHR Implementation Consultant", "Healthcare Implementation Specialist", "Clinical Systems Implementation Analyst"],
            "seniority_options": ["", "Senior ", "Lead ", "Principal "],
            "focus": "implementation"
        },
        {
            "category": "project_manager",
            "titles": ["Healthcare IT Project Manager", "EHR Implementation Project Manager", "Clinical Informatics Program Manager"],
            "seniority_options": ["", "Senior ", "Director of "],
            "focus": "management"
        },
        {
            "category": "analyst",
            "titles": ["Clinical Applications Analyst", "EHR Analyst", "Healthcare Systems Analyst", "Clinical Informatics Analyst"],
            "seniority_options": ["", "Senior ", "Lead "],
            "focus": "analysis"
        },
        {
            "category": "trainer",
            "titles": ["EHR Training Specialist", "Clinical Education Specialist", "Healthcare IT Trainer"],
            "seniority_options": ["", "Senior "],
            "focus": "training"
        }
    ]

    job_type = random.choice(job_types)
    seniority = random.choice(job_type["seniority_options"])
    base_title = random.choice(job_type["titles"])
    title = seniority + base_title

    # Employment characteristics
    employment_type = random.choice(["Full-time", "Part-time"])
    is_contract = random.random() < 0.35
    contract_type = "Contract" if is_contract else "Permanent"

    if is_contract:
        contract_length = random.choice(["3 months", "6 months", "12 months", "18 months", "24 months"])
    else:
        contract_length = None

    # Remote options
    remote_option = random.choice(["On-site", "Hybrid", "Remote", "Travel Required (50-75%)"])

    # EHR System focus
    primary_ehr = random.choice(EHR_SYSTEMS[:6])
    if primary_ehr == "Epic":
        modules_required = random.sample(EPIC_MODULES, random.randint(2, 5))
    elif primary_ehr == "Cerner":
        modules_required = random.sample(CERNER_MODULES, random.randint(2, 4))
    else:
        modules_required = [f"{primary_ehr} Core"]

    # Experience requirements
    min_years = random.choice([2, 3, 5, 7, 10])
    max_years = min_years + random.randint(3, 10) if random.random() > 0.5 else None

    # Employer
    employer_type = random.choice(["hospital", "health_system", "consulting", "vendor"])
    if employer_type == "hospital":
        employer = random.choice(HOSPITALS)
        setting = "hospital"
    elif employer_type == "health_system":
        employer = random.choice(HOSPITALS).replace("Hospital", "Health System").replace("Medical Center", "Health")
        setting = "health system"
    elif employer_type == "consulting":
        employer = random.choice([
            "Nordic Consulting", "Tegria", "Impact Advisors", "Pivot Point Consulting",
            "ECG Management Consultants", "Huron Consulting", "Deloitte Healthcare",
            "Accenture Health", "KPMG Healthcare", "Optimum Healthcare IT"
        ])
        setting = "consulting"
    else:
        employer = random.choice([primary_ehr, "Health Catalyst", "Veradigm", "Medidata"])
        setting = "vendor"

    # Generate requirements
    required_skills = [primary_ehr] + random.sample(SKILLS, random.randint(5, 10))
    preferred_skills = random.sample(SKILLS, random.randint(3, 6))

    # Certifications
    required_certs = []
    if random.random() > 0.4:
        if primary_ehr == "Epic":
            required_certs.append(random.choice([c for c in CERTIFICATIONS if "Epic" in c]))
        elif primary_ehr == "Cerner":
            required_certs.append(random.choice([c for c in CERTIFICATIONS if "Cerner" in c]))

    preferred_certs = random.sample([c for c in CERTIFICATIONS if c not in required_certs], random.randint(1, 3))

    # Salary range
    base_salary = 70000 + (min_years * 8000) + random.randint(-10000, 20000)
    if seniority in ["Senior ", "Lead "]:
        base_salary += 20000
    elif seniority in ["Principal ", "Director of "]:
        base_salary += 40000

    if is_contract:
        hourly_rate = int(base_salary / 2080)  # Convert to hourly
        salary_info = {
            "type": "hourly",
            "min": hourly_rate - 10,
            "max": hourly_rate + 20,
            "currency": "USD"
        }
    else:
        salary_info = {
            "type": "annual",
            "min": base_salary,
            "max": base_salary + random.randint(15000, 40000),
            "currency": "USD"
        }

    # Location
    location = generate_address()

    job = {
        "id": f"job_{job_id:03d}",
        "title": title,
        "employer": employer,
        "employer_type": setting,
        "location": location,
        "remote_option": remote_option,
        "employment_type": employment_type,
        "contract_type": contract_type,
        "contract_length": contract_length,
        "posted_date": (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d"),
        "primary_ehr_system": primary_ehr,
        "modules": modules_required,
        "experience_required": {
            "min_years": min_years,
            "max_years": max_years
        },
        "description": generate_job_description_text(title, employer, primary_ehr, modules_required, setting),
        "responsibilities": generate_responsibilities(job_type["focus"], primary_ehr),
        "required_qualifications": {
            "education": random.choice(["Bachelor's degree in Health Informatics, Healthcare Administration, IT, or related field",
                                        "Bachelor's degree required; Master's preferred",
                                        "Bachelor's degree in relevant field"]),
            "experience": f"{min_years}+ years of healthcare IT implementation experience",
            "skills": required_skills,
            "certifications": required_certs
        },
        "preferred_qualifications": {
            "skills": preferred_skills,
            "certifications": preferred_certs
        },
        "salary": salary_info,
        "benefits": generate_benefits(is_contract)
    }

    return job


def generate_job_description_text(title, employer, ehr, modules, setting):
    """Generate the main job description text."""
    templates = [
        f"{employer} is seeking an experienced {title} to join our healthcare IT team. This role will be instrumental in the implementation and optimization of our {ehr} EHR system. The ideal candidate will have deep expertise in {', '.join(modules[:3])} and a passion for improving clinical workflows through technology.",

        f"Join {employer} as a {title} and help transform healthcare delivery through innovative technology solutions. We are implementing {ehr} across our organization and need experienced professionals to ensure successful deployment and adoption. This is an exciting opportunity to make a significant impact on patient care.",

        f"{employer} seeks a talented {title} to lead our {ehr} implementation initiatives. You will work closely with clinical stakeholders, IT teams, and executive leadership to deliver solutions that improve efficiency and patient outcomes. Experience with {', '.join(modules[:2])} is essential.",

        f"We are looking for a {title} to support our {ehr} implementation and optimization efforts at {employer}. This role requires strong technical skills, excellent communication abilities, and a deep understanding of healthcare workflows. You will be responsible for ensuring successful system adoption across our organization."
    ]
    return random.choice(templates)


def generate_responsibilities(focus, ehr):
    """Generate job responsibilities based on focus area."""
    base_responsibilities = [
        f"Collaborate with clinical stakeholders to gather requirements and design optimal workflows",
        f"Configure and customize {ehr} applications to meet organizational needs",
        "Develop and maintain project documentation, including design specifications and test plans",
        "Participate in system testing, including unit testing, integration testing, and user acceptance testing",
        "Provide go-live support and post-implementation optimization"
    ]

    if focus == "implementation":
        specific = [
            f"Lead end-to-end {ehr} implementation projects from planning through go-live",
            "Design and build clinical workflows within the EHR system",
            "Conduct workflow analysis sessions with clinical departments",
            "Manage data migration and system integration activities",
            "Coordinate with third-party vendors and interface partners"
        ]
    elif focus == "management":
        specific = [
            "Develop and manage project plans, timelines, and resource allocation",
            "Lead cross-functional implementation teams",
            "Report project status to executive leadership",
            "Manage project budget and identify risk mitigation strategies",
            "Facilitate steering committee meetings and stakeholder communications"
        ]
    elif focus == "analysis":
        specific = [
            "Analyze clinical and operational workflows to identify improvement opportunities",
            "Create detailed system specifications and configuration documents",
            "Support build and validation activities",
            "Develop reports and dashboards for clinical and operational metrics",
            "Troubleshoot system issues and implement solutions"
        ]
    else:  # training
        specific = [
            "Develop comprehensive training curricula and materials",
            "Conduct classroom and one-on-one training sessions for end users",
            "Create quick reference guides and e-learning modules",
            "Assess training effectiveness and identify knowledge gaps",
            "Provide at-the-elbow support during go-live events"
        ]

    return base_responsibilities + specific


def generate_benefits(is_contract):
    """Generate benefits package."""
    if is_contract:
        return ["Competitive hourly rate", "Professional development opportunities"]

    return random.sample([
        "Comprehensive health insurance (medical, dental, vision)",
        "401(k) with employer match",
        "Paid time off (PTO)",
        "Professional development budget",
        "Tuition reimbursement",
        "Life and disability insurance",
        "Employee wellness program",
        "Flexible spending accounts (FSA/HSA)",
        "Remote work options",
        "Relocation assistance",
        "Annual performance bonus",
        "Stock options/equity"
    ], random.randint(5, 8))


def main():
    parser = argparse.ArgumentParser(description="Generate healthcare implementation test data")
    parser.add_argument("--resumes", type=int, default=100, help="Number of resumes to generate")
    parser.add_argument("--jobs", type=int, default=20, help="Number of job descriptions to generate")
    parser.add_argument("--output-dir", type=str, default="test_data", help="Output directory")
    args = parser.parse_args()

    base_dir = Path(args.output_dir)
    resume_dir = base_dir / "resumes"
    job_dir = base_dir / "job_descriptions"

    resume_dir.mkdir(parents=True, exist_ok=True)
    job_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating {args.resumes} healthcare implementation resumes...")
    for i in range(1, args.resumes + 1):
        resume = generate_resume(i)
        output_path = resume_dir / f"resume_{i:03d}.json"
        with open(output_path, "w") as f:
            json.dump(resume, f, indent=2)
        if i % 25 == 0:
            print(f"  Generated {i}/{args.resumes} resumes")

    print(f"\nGenerating {args.jobs} EHR implementation job descriptions...")
    for i in range(1, args.jobs + 1):
        job = generate_job_description(i)
        output_path = job_dir / f"job_{i:03d}.json"
        with open(output_path, "w") as f:
            json.dump(job, f, indent=2)

    print(f"\nTest data generated successfully!")
    print(f"  Resumes: {resume_dir}")
    print(f"  Jobs: {job_dir}")


if __name__ == "__main__":
    main()
