"""Configuration for OPT DevOps Job Scraper."""
import os
from dotenv import load_dotenv

load_dotenv()

VERSION = "1.0.0"

# ── Portals ───────────────────────────────────────────────────────────────────
# zip_recruiter → 403 blocked; glassdoor → 400 location parse error; dice → KeyError
PORTALS = ["linkedin", "indeed"]

RESULTS_PER_QUERY = 30
DAYS_LOOKBACK     = 3
COUNTRY           = "USA"
LOCATION          = "United States"

# ── Job categories and their scoring keywords ─────────────────────────────────
JOB_TYPES: dict[str, list[str]] = {
    "DevOps Engineer": [
        "devops", "dev ops", "ci/cd", "cicd", "continuous integration",
        "continuous delivery", "continuous deployment",
        "jenkins", "github actions", "gitlab ci", "circleci", "teamcity",
        "argocd", "argo cd", "flux", "tekton",
        "ansible", "puppet", "chef", "saltstack",
        "terraform", "pulumi", "cloudformation", "bicep",
        "docker", "containers", "containerization",
        "kubernetes", "k8s", "helm", "kustomize",
        "linux", "bash", "shell scripting", "python",
        "monitoring", "prometheus", "grafana", "datadog", "newrelic",
        "elk stack", "elasticsearch", "logstash", "kibana",
        "infrastructure as code", "iac",
        "gitops", "devsecops", "platform engineering",
    ],
    "Cloud Engineer": [
        "aws", "amazon web services", "ec2", "s3", "lambda", "rds",
        "eks", "ecs", "fargate", "cloudwatch", "iam", "vpc",
        "aws certified", "solutions architect",
        "azure", "microsoft azure", "aks", "azure devops", "azure pipelines",
        "azure functions", "azure blob", "arm templates",
        "gcp", "google cloud", "gke", "cloud run", "bigquery",
        "google kubernetes engine",
        "cloud engineer", "cloud infrastructure", "cloud architect",
        "cloud operations", "cloud native", "multi-cloud", "hybrid cloud",
        "iaas", "paas", "saas", "serverless",
    ],
    "Site Reliability Engineer": [
        "sre", "site reliability", "reliability engineer",
        "slo", "sli", "sla", "error budget",
        "on-call", "incident management", "incident response",
        "postmortem", "runbook", "playbook",
        "chaos engineering", "chaos monkey",
        "capacity planning", "performance engineering",
        "observability", "tracing", "jaeger", "zipkin", "opentelemetry",
        "high availability", "fault tolerance", "disaster recovery",
        "scalability", "distributed systems",
    ],
    "Platform Engineer": [
        "platform engineer", "platform engineering",
        "internal developer platform", "idp", "developer platform",
        "developer experience", "devex", "dx",
        "backstage", "crossplane", "port",
        "golden path", "paved road",
        "service mesh", "istio", "linkerd", "consul",
        "api gateway", "kong", "nginx", "envoy",
        "vault", "hashicorp", "secrets management",
    ],
    "Infrastructure Engineer": [
        "infrastructure engineer", "infrastructure developer",
        "systems engineer", "systems administrator",
        "network engineer", "network administrator",
        "linux administrator", "unix administrator",
        "vmware", "vsphere", "hyper-v", "virtualization",
        "load balancer", "haproxy", "f5",
        "dns", "dhcp", "tcp/ip", "networking",
        "data center", "colocation", "bare metal",
        "storage engineer", "san", "nas",
    ],
    "Cloud Consultant": [
        "cloud consultant", "cloud solutions", "cloud advisor",
        "cloud migration", "cloud transformation", "cloud strategy",
        "cloud architecture", "solutions architect",
        "aws consultant", "azure consultant", "gcp consultant",
        "cloud computing", "cloud adoption", "landing zone",
        "cloud governance", "cloud cost", "finops",
        "cloud security posture", "cloud native",
        "terraform", "cloudformation", "bicep", "pulumi",
        "well-architected", "cloud best practices",
    ],
    "MLOps Engineer": [
        "mlops", "ml ops", "machine learning ops",
        "mlflow", "kubeflow", "airflow", "prefect", "dagster",
        "model deployment", "model serving", "model registry",
        "feature store", "feature engineering pipeline",
        "data pipeline", "data engineering",
        "spark", "hadoop", "databricks",
        "pytorch", "tensorflow", "model monitoring",
        "vertex ai", "sagemaker", "azure ml",
        "llmops", "llm", "generative ai deployment",
    ],
    "DevSecOps Engineer": [
        "devsecops", "dev sec ops", "security engineer",
        "application security", "appsec",
        "sast", "dast", "sca", "snyk", "sonarqube", "veracode",
        "container security", "image scanning", "trivy", "clair",
        "secrets scanning", "vault", "aws secrets manager",
        "compliance as code", "policy as code", "opa", "open policy agent",
        "penetration testing", "vulnerability management",
        "zero trust", "identity access management",
        "soc 2", "pci dss", "hipaa compliance",
    ],
}

ALL_DEVOPS_KEYWORDS: set[str] = {kw for kws in JOB_TYPES.values() for kw in kws}

# ── Search queries ────────────────────────────────────────────────────────────
# Kept tight — 3-4 per category, entry/mid-level OPT focused.
# Broad terms like "DevOps Engineer" alone pull too many irrelevant results.
SEARCH_QUERIES: dict[str, list[str]] = {
    "DevOps Engineer": [
        "Junior DevOps Engineer",
        "Entry Level DevOps Engineer",
        "Associate DevOps Engineer",
        "DevOps Engineer Kubernetes Docker",
        "CI CD Engineer Jenkins GitHub Actions",
        "Build Release Engineer Terraform Ansible",
    ],
    "Cloud Engineer": [
        "Junior Cloud Engineer AWS",
        "Entry Level Cloud Engineer Azure GCP",
        "Associate Cloud Engineer",
        "AWS Cloud Engineer entry level OPT",
        "Azure Cloud Engineer junior",
        "GCP Cloud Infrastructure Engineer entry level",
        "Cloud Computing Engineer entry level",
    ],
    "Cloud Consultant": [
        "Junior Cloud Consultant AWS Azure",
        "Entry Level Cloud Solutions Consultant",
        "Cloud Consultant entry level OPT",
        "Associate Cloud Architect",
        "Cloud Migration Consultant junior",
    ],
    "Site Reliability Engineer": [
        "Junior Site Reliability Engineer",
        "Entry Level SRE Kubernetes",
        "Associate SRE DevOps",
        "SRE Engineer entry level OPT",
    ],
    "Platform Engineer": [
        "Junior Platform Engineer Kubernetes",
        "Entry Level Platform Engineer DevOps",
        "Cloud Platform Engineer associate",
    ],
    "Infrastructure Engineer": [
        "Junior Cloud Infrastructure Engineer",
        "Entry Level Linux Infrastructure Engineer",
        "Infrastructure Engineer Terraform AWS entry level",
        "Systems Engineer Cloud entry level",
    ],
    "MLOps Engineer": [
        "Junior MLOps Engineer",
        "Entry Level MLOps Machine Learning",
        "ML Platform Engineer entry level",
    ],
    "DevSecOps Engineer": [
        "Junior DevSecOps Engineer",
        "Entry Level Cloud Security Engineer",
        "Application Security Engineer DevOps entry level",
    ],
}

# ── Defense contractor blocklist (always require clearance → ineligible for OPT)
DEFENSE_COMPANY_BLOCKLIST: list[str] = [
    # Prime defense contractors
    "general dynamics", "gdit", "leidos", "peraton", "saic",
    "booz allen", "northrop grumman", "raytheon", "rtx corporation",
    "mantech", "bae systems", "l3harris", "caci", "parsons corporation",
    "mitre corporation", "mitre corp",
    "science applications international",
    # Federal consulting arms of large firms
    "accenture federal", "deloitte government", "deloitte federal",
    "ibm federal", "kpmg federal",
    # Other frequent clearance shops
    "anduril", "palantir", "titan defense",
    "sierra nevada corporation", "cubic defense",
    "dxc federal", "nci information systems",
    "engility", "maximus federal", "perspecta",
    "chenega", "amentum", "vectrus",
]

# ── OPT eligibility filters ───────────────────────────────────────────────────
OPT_HARD_EXCLUDE: list[str] = [
    # Citizenship / PR requirements
    "us citizen only", "u.s. citizen only", "united states citizen only",
    "must be a us citizen", "must be us citizen", "citizens only",
    "green card only", "green card holder only", "permanent resident only",
    "pr only", "usc only", "usc/gc only", "us citizen or green card",
    "must have green card", "citizenship required",
    "authorized to work in the us without sponsorship",
    "work authorization without sponsorship",
    "must be authorized to work without sponsorship",
    # Security clearance variants
    "security clearance required", "clearance required", "active clearance",
    "secret clearance", "top secret", "ts/sci", "ts-sci", "secret/sci",
    "public trust clearance", "dod clearance", "must have clearance",
    "must hold clearance", "must possess clearance",
    "clearance is required", "clearance required for this role",
    "active security clearance", "current security clearance",
    "must be clearance eligible", "clearance eligible required",
    "q clearance", "sci eligible", "eligible for clearance",
    # Polygraph
    "polygraph required", "polygraph test required",
    "must pass polygraph", "lie detector", "full scope polygraph",
    # ITAR / DoD / federal program restrictions
    "itar", "itar restricted", "itar compliance required", "ear compliance",
    "itar regulations", "subject to itar",
    "department of defense contract", "dod project", "dod program",
    "federal contract", "classified contract", "classified environment",
    "classified information", "classified projects",
    "nsa", "cia clearance", "dhs clearance",
    # OPT explicit rejections
    "no opt", "no cpt", "no f1", "opt not accepted", "no opt/cpt",
    "opt/cpt not accepted", "no f1 opt", "no f-1",
    "not eligible for opt", "opt is not supported",
]

OPT_POSITIVE: list[str] = [
    "opt", "cpt", "f1", "f-1", "stem opt",
    "opt/cpt", "f1/opt", "opt friendly",
    "visa friendly", "international students",
    "open to opt", "accepts opt",
    "all visa types", "all work authorizations",
    "h1b sponsorship available", "h1b sponsor",
    "will sponsor", "visa sponsorship provided",
    "sponsorship available",
]

OPT_SOFT_EXCLUDE: list[str] = [
    "no visa sponsorship", "no sponsorship",
    "sponsorship not available", "we do not sponsor",
    "cannot sponsor",
]

# ── Experience level ──────────────────────────────────────────────────────────
ENTRY_MID_SIGNALS: list[str] = [
    "entry level", "entry-level", "junior", "jr.", "jr ",
    "associate", "associate engineer",
    "new grad", "new graduate", "recent graduate", "recent grad",
    "0-2 years", "0-3 years", "1-2 years", "1-3 years",
    "2-4 years", "2-5 years", "3-5 years",
    "mid level", "mid-level", "intermediate",
    "engineer i", "engineer ii", "level 1", "level 2",
    "early career", "early-career",
]

SENIOR_HARD_EXCLUDE: list[str] = [
    # Leadership / executive — always exclude
    "director", "vp of", "vice president", "head of",
    "engineering manager", "staff engineer", "principal engineer",
    "distinguished engineer", "fellow engineer",
    "chief", "cto", "ciso",
    # Additional senior-level patterns caught by exact substring
    "senior staff", "principal staff", "chief engineer",
    "technical director", "engineering director", "director of engineering",
]

# Regex-style seniority patterns (applied as word-boundary regex, not substring)
# These catch cases like "Staff Fiber Network Engineer" where exact-string fails.
SENIOR_REGEX_PATTERNS: list[str] = [
    r"\bstaff\b",         # "Staff" as seniority prefix (any title: "Staff SRE", "Staff Fiber Network Engineer")
    r"\bprincipal\b",     # "Principal Cloud Architect" etc.
    r"\bsenior\b",        # redundant with SENIOR_SOFT but catches mis-spellings / all-caps
    r"\bsr\.\s",          # "Sr. DevOps" (with period)
    r"\bsr\s",            # "Sr DevOps" (without period)
    r"\bdistinguished\b", # Google/Amazon "Distinguished Engineer"
    r"\bfellow\b",        # "Fellow Engineer"
    r"\blead\b.{0,35}\bengineer\b",  # "Lead Controls Engineer", "Lead Design Release Engineer"
]

# Non-IT industries — titles containing these signals are NOT software engineering jobs
# Used to reject: manufacturing/automotive/telecom/biotech roles that use words like
# "engineer", "cloud", or "devops" in non-software context.
NON_IT_TITLE_SIGNALS: list[str] = [
    # Manufacturing / industrial
    "controls engineer", "controls & reliability", "reliability service engineer",
    "process engineer", "manufacturing engineer", "production engineer",
    "plant engineer", "field service engineer", "maintenance engineer",
    "quality engineer", "test engineer", "validation engineer",
    "design release engineer", "product launch engineer",
    "environmental engineer", "safety engineer", "mechanical engineer",
    "electrical engineer", "chemical engineer", "civil engineer",
    "structural engineer", "aerospace engineer", "automotive engineer",
    "hvac engineer", "facilities engineer", "operations engineer",
    # Telecom / non-software
    "fiber network engineer", "fiber engineer", "rf engineer",
    "telecom engineer", "telecommunications engineer",
    "transmission engineer", "cable engineer", "broadband engineer",
    # Healthcare / biotech
    "clinical engineer", "biomedical engineer", "medical device engineer",
    "bioinformatics engineer", "lab engineer",
    # Construction / utilities
    "construction engineer", "project engineer construction",
    "utility engineer", "power engineer", "energy engineer",
]

SENIOR_SOFT: list[str] = [
    "senior", "sr.", "sr ", "lead engineer", "tech lead",
    "7+ years", "8+ years", "10+ years", "10 years",
    "12+ years", "15+ years",
]

# ── Scoring weights ───────────────────────────────────────────────────────────
SCORE_WEIGHTS = {
    "opt_positive":     20,
    "opt_soft_exclude": -10,
    "entry_mid_signal": 15,
    "senior_soft":      -15,
    "remote":           10,
    "keyword_depth":    30,
    "recency":          10,
    "description_len":   5,
}

SCORE_MIN_NOTIFY = 35

# ── Output ────────────────────────────────────────────────────────────────────
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
DB_PATH    = os.path.join(os.path.dirname(__file__), "jobs.db")

# ── Email ─────────────────────────────────────────────────────────────────────
GMAIL_USER         = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
NOTIFY_EMAIL       = os.getenv("NOTIFY_EMAIL", GMAIL_USER)
