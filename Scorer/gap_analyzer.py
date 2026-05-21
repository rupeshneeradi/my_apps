"""
Skill Gap Analyzer
────────────────────────────────────────────────────────────────────────────
Rule-based, 100% local, no AI.
Maps a target job title + current skills → readiness score + learning plan.

Usage:
    from gap_analyzer import analyze_gap
    result = analyze_gap("data engineer", ["python", "sql", "spark"])
"""
import re

# ── Skill aliases ──────────────────────────────────────────────────────────────
SKILL_ALIASES: dict[str, str] = {
    # JS / TS
    "js": "javascript", "ts": "typescript",
    "reactjs": "react", "react.js": "react",
    "vuejs": "vue.js", "vue": "vue.js",
    "angularjs": "angular",
    "nodejs": "node.js", "node": "node.js",
    "nextjs": "next.js", "next": "next.js",
    "expressjs": "express.js", "express": "express.js",
    # Python
    "py": "python", "python3": "python",
    # Cloud
    "amazon web services": "aws",
    "microsoft azure": "azure",
    "google cloud platform": "gcp", "google cloud": "gcp",
    # Databases
    "postgres": "postgresql", "pg": "postgresql",
    "mssql": "sql server", "microsoft sql server": "sql server",
    "mongo": "mongodb", "mongo db": "mongodb",
    "elastic": "elasticsearch", "elastic search": "elasticsearch",
    "redis cache": "redis",
    # Containers / orchestration
    "k8s": "kubernetes", "kube": "kubernetes",
    "docker compose": "docker",
    # Data
    "apache kafka": "kafka", "apache spark": "spark",
    "apache airflow": "airflow", "pyspark": "spark",
    "scikit": "scikit-learn", "sklearn": "scikit-learn", "scikit learn": "scikit-learn",
    "tensorflow2": "tensorflow", "tf": "tensorflow",
    "torch": "pytorch",
    # DevOps
    "cicd": "ci/cd", "ci cd": "ci/cd",
    "jenkins ci": "jenkins",
    "gitlab ci": "gitlab ci/cd",
    # Java
    "spring": "spring boot", "springboot": "spring boot", "spring framework": "spring boot",
    "jpa": "hibernate/jpa", "hibernate": "hibernate/jpa",
    # API
    "restful": "rest api", "rest": "rest api",
    # Agile
    "agile": "agile/scrum", "scrum": "agile/scrum",
    # Oracle
    "oracle hcm": "oracle hcm", "hcm cloud": "oracle hcm", "fusion hcm": "oracle hcm",
    "oic": "oracle oic", "oracle integration cloud": "oracle oic",
    "oracle apex": "oracle apex", "apex": "oracle apex",
    "oracle ebs": "oracle ebs", "e-business suite": "oracle ebs",
    "plsql": "pl/sql", "pl sql": "pl/sql",
    # Testing
    "playwright": "playwright",
    "cypress": "cypress",
    # Mobile
    "react native": "react native",
}


def _normalize(skill: str) -> str:
    s = skill.lower().strip()
    s = re.sub(r'\s+', ' ', s)
    return SKILL_ALIASES.get(s, s)


# ── Role profiles ──────────────────────────────────────────────────────────────
# core      → must-have (60 % weight in readiness score)
# important → high value (35 % weight)
# nice      → differentiators (5 % weight)

ROLE_PROFILES: dict[str, dict] = {

    "software engineer": {
        "aliases": ["software developer", "swe", "application developer", "programmer"],
        "core":      ["python", "javascript", "git", "sql", "data structures",
                      "algorithms", "oop", "rest api", "testing", "debugging"],
        "important": ["docker", "ci/cd", "agile/scrum", "typescript", "react",
                      "node.js", "aws", "linux", "microservices", "design patterns"],
        "nice":      ["kubernetes", "graphql", "redis", "elasticsearch",
                      "system design", "grpc", "terraform", "kafka"],
        "certs": ["AWS Certified Developer – Associate",
                  "Google Professional Cloud Developer",
                  "Oracle Certified Professional Java SE"],
        "resources": ["CS50x – Harvard OpenCourseWare (free)",
                      "The Odin Project – full-stack, free",
                      "LeetCode – algorithms & data structures"],
    },

    "backend developer": {
        "aliases": ["backend engineer", "api developer", "server-side developer",
                    "python backend", "node backend"],
        "core":      ["python", "rest api", "sql", "git", "docker",
                      "authentication/jwt", "oop", "testing", "linux", "postgresql"],
        "important": ["node.js", "redis", "message queues", "microservices",
                      "ci/cd", "aws", "mongodb", "elasticsearch", "spring boot", "kafka"],
        "nice":      ["kubernetes", "graphql", "grpc", "terraform",
                      "celery", "fastapi", "django", "flask"],
        "certs": ["AWS Certified Developer – Associate",
                  "HashiCorp Certified: Terraform Associate"],
        "resources": ["Real Python (free backend tutorials)",
                      "FastAPI docs (free)",
                      "roadmap.sh/backend (free visual roadmap)"],
    },

    "frontend developer": {
        "aliases": ["frontend engineer", "ui developer", "react developer",
                    "vue developer", "angular developer", "web developer"],
        "core":      ["html", "css", "javascript", "react", "responsive design",
                      "git", "rest api", "npm/yarn", "accessibility", "browser devtools"],
        "important": ["typescript", "next.js", "testing", "state management",
                      "css frameworks", "performance optimization", "graphql",
                      "ci/cd", "webpack/vite", "design systems"],
        "nice":      ["vue.js", "angular", "react native", "web components",
                      "animations", "storybook", "figma", "web performance"],
        "certs": ["Meta Front-End Developer Certificate",
                  "Google UX Design Certificate"],
        "resources": ["The Odin Project (free HTML/CSS/JS/React)",
                      "web.dev – Google's free fundamentals",
                      "Frontend Mentor – free practice projects"],
    },

    "full stack developer": {
        "aliases": ["full-stack developer", "full stack engineer",
                    "full-stack engineer", "fullstack developer"],
        "core":      ["javascript", "react", "node.js", "sql", "rest api",
                      "git", "html", "css", "postgresql", "docker"],
        "important": ["typescript", "next.js", "mongodb", "redis", "ci/cd",
                      "aws", "testing", "agile/scrum", "microservices", "authentication/jwt"],
        "nice":      ["kubernetes", "graphql", "terraform",
                      "react native", "system design", "webpack/vite"],
        "certs": ["AWS Certified Developer – Associate",
                  "Full Stack Open Certificate (University of Helsinki)"],
        "resources": ["Full Stack Open – University of Helsinki, free",
                      "The Odin Project – free full-stack",
                      "roadmap.sh – free visual roadmaps"],
    },

    "data engineer": {
        "aliases": ["data pipeline engineer", "etl developer", "data platform engineer",
                    "big data engineer", "analytics engineer"],
        "core":      ["python", "sql", "spark", "data warehouse", "etl/elt",
                      "git", "linux", "postgresql", "data modeling", "airflow"],
        "important": ["kafka", "dbt", "aws", "docker", "snowflake",
                      "redshift", "bigquery", "delta lake", "ci/cd", "pandas"],
        "nice":      ["kubernetes", "terraform", "flink", "duckdb",
                      "apache iceberg", "databricks", "spark streaming", "great expectations"],
        "certs": ["AWS Certified Data Analytics – Specialty",
                  "Databricks Certified Associate Developer for Apache Spark",
                  "dbt Analytics Engineering Certificate"],
        "resources": ["DataTalks.Club Data Engineering Zoomcamp (free)",
                      "dbt Learn – free fundamentals course",
                      "Apache Spark docs + PySpark examples (free)"],
    },

    "data analyst": {
        "aliases": ["business analyst", "analytics analyst", "reporting analyst",
                    "bi analyst", "business intelligence analyst"],
        "core":      ["sql", "excel", "data visualization", "python", "tableau",
                      "statistical analysis", "data cleaning", "reporting", "powerbi", "git"],
        "important": ["pandas", "a/b testing", "dashboards", "data storytelling",
                      "bigquery", "snowflake", "dbt", "looker", "matplotlib", "business intelligence"],
        "nice":      ["r language", "spark", "machine learning basics",
                      "airflow", "aws", "advanced statistics", "google analytics"],
        "certs": ["Google Data Analytics Certificate",
                  "Tableau Desktop Specialist",
                  "Microsoft Power BI Data Analyst Associate"],
        "resources": ["Google Data Analytics Certificate – Coursera (free audit)",
                      "Mode Analytics SQL Tutorial (free)",
                      "Kaggle Learn – free Python/Pandas/SQL"],
    },

    "data scientist": {
        "aliases": ["ml engineer", "machine learning engineer", "ai engineer",
                    "research scientist", "applied scientist", "ai/ml engineer"],
        "core":      ["python", "machine learning", "sql", "statistics",
                      "scikit-learn", "pandas", "numpy", "data preprocessing",
                      "model evaluation", "jupyter"],
        "important": ["tensorflow", "pytorch", "feature engineering", "nlp",
                      "deep learning", "git", "docker", "aws", "experiment tracking", "spark"],
        "nice":      ["mlops", "kubernetes", "airflow", "dbt",
                      "llm fine-tuning", "computer vision", "rag", "vector databases"],
        "certs": ["Google Professional ML Engineer",
                  "AWS Certified Machine Learning – Specialty",
                  "DeepLearning.AI ML Specialization"],
        "resources": ["fast.ai – free practical deep learning",
                      "Kaggle – free competitions + notebooks",
                      "DeepLearning.AI – Coursera (free audit)"],
    },

    "devops engineer": {
        "aliases": ["sre", "site reliability engineer", "platform engineer",
                    "infrastructure engineer", "cloud devops", "devops"],
        "core":      ["linux", "docker", "kubernetes", "ci/cd", "git",
                      "terraform", "ansible", "bash scripting", "monitoring", "aws"],
        "important": ["helm", "github actions", "jenkins", "prometheus/grafana",
                      "python", "networking", "security", "azure devops",
                      "elk stack", "service mesh"],
        "nice":      ["argocd", "gitops", "chaos engineering", "cost optimization",
                      "crossplane", "pulumi", "istio", "ebpf"],
        "certs": ["AWS Certified DevOps Engineer – Professional",
                  "Certified Kubernetes Administrator (CKA)",
                  "HashiCorp Certified: Terraform Associate"],
        "resources": ["KodeKloud – free Kubernetes/DevOps labs",
                      "Play with Kubernetes – free browser labs",
                      "roadmap.sh/devops – free visual roadmap"],
    },

    "cloud engineer": {
        "aliases": ["aws engineer", "azure engineer", "gcp engineer",
                    "cloud architect", "cloud solutions architect",
                    "cloud infrastructure engineer"],
        "core":      ["aws", "linux", "networking", "docker", "terraform",
                      "iam/security", "compute", "storage", "databases", "ci/cd"],
        "important": ["kubernetes", "azure", "gcp", "python", "ansible",
                      "monitoring", "cost management", "serverless", "vpc", "load balancing"],
        "nice":      ["multi-cloud", "cloud native", "service mesh", "gitops",
                      "pulumi", "finops", "disaster recovery", "crossplane"],
        "certs": ["AWS Solutions Architect – Associate",
                  "Google Professional Cloud Architect",
                  "Microsoft Azure Administrator (AZ-104)"],
        "resources": ["AWS Skill Builder – free tier",
                      "Google Cloud Skills Boost – free credits",
                      "A Cloud Guru – free trial"],
    },

    "qa engineer": {
        "aliases": ["quality assurance engineer", "test engineer", "sdet",
                    "software test engineer", "automation engineer", "testing engineer"],
        "core":      ["selenium", "test planning", "sql", "git", "api testing",
                      "bug tracking", "test case design", "regression testing",
                      "agile/scrum", "python"],
        "important": ["cypress", "pytest", "postman", "ci/cd", "performance testing",
                      "bdd/cucumber", "test automation", "docker", "playwright", "rest api"],
        "nice":      ["kubernetes", "load testing", "security testing",
                      "mobile testing", "appium", "chaos testing"],
        "certs": ["ISTQB Foundation Level",
                  "AWS Certified DevOps Engineer",
                  "Selenium WebDriver Certification"],
        "resources": ["Test Automation University – free courses",
                      "Playwright docs (free)",
                      "ISTQB Foundation syllabus (free PDF)"],
    },

    "java developer": {
        "aliases": ["java engineer", "java backend developer", "j2ee developer",
                    "java software engineer", "java full stack"],
        "core":      ["java", "spring boot", "hibernate/jpa", "sql", "rest api",
                      "maven/gradle", "git", "oop", "design patterns", "junit"],
        "important": ["microservices", "docker", "kafka", "postgresql", "redis",
                      "ci/cd", "aws", "spring security", "swagger/openapi", "agile/scrum"],
        "nice":      ["kubernetes", "graphql", "grpc", "spring cloud",
                      "reactive programming", "quarkus", "kotlin", "elasticsearch"],
        "certs": ["Oracle Certified Professional Java SE Developer",
                  "Spring Certified Professional",
                  "AWS Certified Developer – Associate"],
        "resources": ["Baeldung.com – free Java/Spring tutorials",
                      "Spring.io Guides (free)",
                      "roadmap.sh/java – free visual roadmap"],
    },

    "python developer": {
        "aliases": ["python engineer", "django developer", "flask developer",
                    "fastapi developer", "python backend developer"],
        "core":      ["python", "rest api", "sql", "git", "oop",
                      "testing (pytest)", "linux", "virtual environments", "debugging", "docker"],
        "important": ["django", "fastapi", "flask", "postgresql", "redis",
                      "celery", "aws", "ci/cd", "pandas", "async programming"],
        "nice":      ["kubernetes", "graphql", "kafka", "elasticsearch",
                      "machine learning basics", "pydantic", "sqlalchemy", "alembic"],
        "certs": ["Python Institute PCAP – Certified Associate",
                  "AWS Certified Developer – Associate"],
        "resources": ["Real Python – free tutorials",
                      "Python docs official (free)",
                      "roadmap.sh/python – free roadmap"],
    },

    "oracle developer": {
        "aliases": ["oracle consultant", "oracle techno-functional",
                    "oracle technical consultant", "oracle hcm consultant",
                    "oracle ebs developer", "oracle fusion developer",
                    "oracle oic developer", "oracle apex developer"],
        "core":      ["pl/sql", "sql", "oracle hcm", "oracle ebs", "oracle oic",
                      "oracle apex", "data migration", "integration", "bi publisher", "otbi"],
        "important": ["hcm data loader", "fast formula", "oracle reports",
                      "rest api", "oracle workflow", "performance tuning",
                      "oracle forms", "oracle fusion", "vbcs", "git"],
        "nice":      ["oracle goldengate", "oracle dba", "odi", "adf",
                      "oracle analytics cloud", "apex office print", "kubernetes"],
        "certs": ["Oracle Cloud Infrastructure 2023 Certified Foundations Associate",
                  "Oracle HCM Cloud 2023 Implementation Certified Associate",
                  "Oracle APEX Developer Certified Professional"],
        "resources": ["Oracle University – some free courses",
                      "LiveSQL – free Oracle SQL practice environment",
                      "Oracle APEX Tutorial (free on oracle.com)"],
    },

    "product manager": {
        "aliases": ["product owner", "pm", "associate product manager",
                    "technical product manager", "digital product manager"],
        "core":      ["product strategy", "roadmap planning", "user research",
                      "agile/scrum", "stakeholder management", "data analysis",
                      "product metrics", "jira", "wireframing", "prioritization"],
        "important": ["sql", "a/b testing", "go-to-market", "figma",
                      "competitive analysis", "user story writing", "okrs",
                      "api understanding", "customer discovery", "analytics tools"],
        "nice":      ["python", "machine learning basics", "growth hacking",
                      "technical architecture", "pricing strategy", "ux writing"],
        "certs": ["Certified Scrum Product Owner (CSPO)",
                  "Product School Certificate",
                  "Google UX Design Certificate"],
        "resources": ["Lenny's Newsletter – free PM resources",
                      "Product School – free ebooks",
                      "Reforge Blog – free articles"],
    },

    "cybersecurity engineer": {
        "aliases": ["security engineer", "information security engineer",
                    "cybersecurity analyst", "security analyst",
                    "penetration tester", "soc analyst"],
        "core":      ["networking (tcp/ip)", "linux", "python", "siem tools",
                      "vulnerability assessment", "incident response", "iam",
                      "firewall/ids/ips", "cryptography", "owasp"],
        "important": ["cloud security", "penetration testing", "threat modeling",
                      "soc/soar", "log analysis", "docker security",
                      "zero trust", "devsecops", "cve analysis", "git"],
        "nice":      ["malware analysis", "reverse engineering", "red team",
                      "threat intelligence", "kubernetes security", "bug bounty"],
        "certs": ["CompTIA Security+",
                  "Certified Ethical Hacker (CEH)",
                  "AWS Certified Security – Specialty"],
        "resources": ["TryHackMe – free tier cybersecurity labs",
                      "HackTheBox – free tier",
                      "OWASP Top 10 documentation (free)"],
    },

    "mobile developer": {
        "aliases": ["ios developer", "android developer", "react native developer",
                    "flutter developer", "mobile app developer"],
        "core":      ["react native", "swift", "kotlin", "javascript", "rest api",
                      "git", "mobile ui", "app store deployment", "testing", "xcode"],
        "important": ["flutter", "typescript", "state management",
                      "push notifications", "offline sync", "firebase",
                      "performance optimization", "ci/cd", "analytics", "accessibility"],
        "nice":      ["swiftui", "jetpack compose", "ar/vr mobile",
                      "ml on device", "bluetooth/iot", "payment integration"],
        "certs": ["Google Associate Android Developer",
                  "Meta React Native Certificate"],
        "resources": ["React Native docs (free)",
                      "Flutter docs (free)",
                      "Expo – free React Native starter"],
    },
}


# ── Role matching ──────────────────────────────────────────────────────────────

def _find_profile(title: str) -> tuple[str, dict] | tuple[None, None]:
    t = title.lower().strip()

    if t in ROLE_PROFILES:
        return t, ROLE_PROFILES[t]

    for key, prof in ROLE_PROFILES.items():
        if t in prof.get("aliases", []):
            return key, prof

    for key, prof in ROLE_PROFILES.items():
        if key in t or t in key:
            return key, prof
        for alias in prof.get("aliases", []):
            if alias in t or t in alias:
                return key, prof

    # Keyword fallback
    kw_map = {
        "data engineer":        ["pipeline", "etl", "elt", "airflow", "dbt"],
        "data scientist":       ["machine learning", "ml", "ai", "deep learning", "nlp"],
        "data analyst":         ["analyst", "analytics", "business intelligence", "bi"],
        "devops engineer":      ["devops", "sre", "site reliability", "platform engineer"],
        "cloud engineer":       ["cloud", "aws", "azure", "gcp"],
        "frontend developer":   ["frontend", "front-end", "ui", "react", "angular", "vue"],
        "backend developer":    ["backend", "back-end", "api"],
        "qa engineer":          ["qa", "qe", "quality", "test", "automation"],
        "java developer":       ["java", "spring", "j2ee"],
        "oracle developer":     ["oracle", "hcm", "ebs", "apex", "oic", "pl/sql"],
        "cybersecurity engineer":["security", "cyber", "infosec", "soc", "pentest"],
        "mobile developer":     ["mobile", "ios", "android", "flutter"],
        "product manager":      ["product", "product owner"],
        "python developer":     ["python", "django", "fastapi", "flask"],
        "full stack developer": ["full stack", "fullstack", "full-stack"],
        "software engineer":    ["software", "developer", "engineer", "programmer"],
    }
    for key, kws in kw_map.items():
        if any(kw in t for kw in kws) and key in ROLE_PROFILES:
            return key, ROLE_PROFILES[key]

    return None, None


# ── Skill matching ─────────────────────────────────────────────────────────────

def _norm_set(skills: list[str]) -> set[str]:
    return {_normalize(s) for s in skills if s.strip()}


def _has(candidate: set[str], target: str) -> bool:
    t = _normalize(target)
    if t in candidate:
        return True
    for cs in candidate:
        if "/" in t:
            if any(p.strip() in candidate or p.strip() in cs for p in t.split("/")):
                return True
        if len(t) >= 3 and (t in cs or cs in t):
            return True
    return False


# ── Public API ─────────────────────────────────────────────────────────────────

def analyze_gap(target_role: str, current_skills: list[str]) -> dict:
    """
    Returns a full gap analysis dict:
      profile_found, profile_name, readiness_score,
      matched_core, matched_important,
      gap_core, gap_important, gap_nice,
      learning_priority, certs, resources, message
    """
    profile_name, profile = _find_profile(target_role)

    if not profile:
        return {
            "profile_found":    False,
            "profile_name":     None,
            "readiness_score":  0,
            "matched_core":     [],
            "matched_important":[],
            "gap_core":         [],
            "gap_important":    [],
            "gap_nice":         [],
            "learning_priority":[],
            "certs":            [],
            "resources":        [],
            "message": (
                f"No profile found for '{target_role}'. "
                "Try: Software Engineer, Data Engineer, DevOps Engineer, "
                "Frontend Developer, Data Scientist, Cloud Engineer, "
                "Java Developer, Oracle Developer, QA Engineer, Product Manager…"
            ),
        }

    candidate = _norm_set(current_skills)
    core      = profile.get("core", [])
    important = profile.get("important", [])
    nice      = profile.get("nice", [])

    matched_core      = [s for s in core      if _has(candidate, s)]
    matched_important = [s for s in important if _has(candidate, s)]
    gap_core          = [s for s in core      if not _has(candidate, s)]
    gap_important     = [s for s in important if not _has(candidate, s)]
    gap_nice          = [s for s in nice      if not _has(candidate, s)]

    core_pct  = len(matched_core)      / max(len(core),      1)
    imp_pct   = len(matched_important) / max(len(important), 1)
    nice_pct  = (len(nice) - len(gap_nice)) / max(len(nice), 1)
    readiness = round(core_pct * 60 + imp_pct * 35 + nice_pct * 5)

    learning_priority = []
    for s in gap_core:
        learning_priority.append({
            "skill": s, "priority": "HIGH",
            "reason": f"Core requirement — expected on every {profile_name} JD",
        })
    for s in gap_important:
        learning_priority.append({
            "skill": s, "priority": "MEDIUM",
            "reason": f"Significantly increases your value as a {profile_name}",
        })
    for s in gap_nice[:5]:
        learning_priority.append({
            "skill": s, "priority": "LOW",
            "reason": "Differentiator that sets you apart from other candidates",
        })

    if readiness >= 80:
        msg = f"You are well-prepared for {profile_name} roles! Polish the remaining gaps to stand out."
    elif readiness >= 55:
        msg = f"Good foundation for {profile_name}. Address HIGH priority gaps to become interview-ready."
    elif readiness >= 30:
        msg = f"Solid start. Build the HIGH priority core skills first — they unlock everything else."
    else:
        msg = f"Large gap for {profile_name} roles. Start with the core skills list — master those before moving on."

    return {
        "profile_found":     True,
        "profile_name":      profile_name,
        "readiness_score":   readiness,
        "matched_core":      matched_core,
        "matched_important": matched_important,
        "gap_core":          gap_core,
        "gap_important":     gap_important,
        "gap_nice":          gap_nice,
        "learning_priority": learning_priority,
        "certs":             profile.get("certs", []),
        "resources":         profile.get("resources", []),
        "message":           msg,
    }


# ── Available roles (for autocomplete hints) ──────────────────────────────────
AVAILABLE_ROLES = list(ROLE_PROFILES.keys())
