"""Configuration for OPT DevOps Job Scraper."""
import os
from dotenv import load_dotenv

load_dotenv()

VERSION = "1.0.0"

# ── Portals ───────────────────────────────────────────────────────────────────
PORTALS = ["dice", "linkedin", "indeed", "zip_recruiter", "glassdoor"]

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
SEARCH_QUERIES: dict[str, list[str]] = {
    "DevOps Engineer": [
        "Junior DevOps Engineer",
        "Entry Level DevOps Engineer",
        "DevOps Engineer I",
        "Associate DevOps Engineer",
        "DevOps Engineer",
        "CI CD Engineer entry level",
        "Build and Release Engineer junior",
    ],
    "Cloud Engineer": [
        "Junior Cloud Engineer",
        "Entry Level Cloud Engineer",
        "Cloud Engineer AWS",
        "Cloud Engineer Azure",
        "Cloud Engineer GCP",
        "Associate Cloud Engineer",
        "Cloud Operations Engineer entry level",
    ],
    "Site Reliability Engineer": [
        "Junior SRE",
        "Entry Level Site Reliability Engineer",
        "SRE Engineer I",
        "Associate SRE",
        "Site Reliability Engineer entry level",
    ],
    "Platform Engineer": [
        "Platform Engineer entry level",
        "Junior Platform Engineer",
        "Infrastructure Platform Engineer",
        "Developer Platform Engineer",
    ],
    "Infrastructure Engineer": [
        "Junior Infrastructure Engineer",
        "Entry Level Infrastructure Engineer",
        "Systems Engineer entry level",
        "Linux Engineer junior",
        "Cloud Infrastructure Engineer",
    ],
    "MLOps Engineer": [
        "MLOps Engineer entry level",
        "Junior MLOps Engineer",
        "ML Infrastructure Engineer",
        "Machine Learning Engineer DevOps",
    ],
    "DevSecOps Engineer": [
        "DevSecOps Engineer entry level",
        "Junior Security Engineer DevOps",
        "Application Security Engineer junior",
        "Cloud Security Engineer entry level",
    ],
}

# ── OPT eligibility filters ───────────────────────────────────────────────────
OPT_HARD_EXCLUDE: list[str] = [
    "us citizen only", "u.s. citizen only", "united states citizen only",
    "must be a us citizen", "must be us citizen", "citizens only",
    "green card only", "green card holder only", "permanent resident only",
    "pr only", "usc only", "usc/gc only", "us citizen or green card",
    "must have green card",
    "security clearance required", "clearance required", "active clearance",
    "secret clearance", "top secret", "ts/sci", "ts-sci", "secret/sci",
    "public trust clearance", "dod clearance", "must have clearance",
    "must hold clearance", "must possess clearance",
    "no opt", "no cpt", "no f1", "opt not accepted", "no opt/cpt",
    "opt/cpt not accepted",
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
    "director", "vp of", "vice president", "head of",
    "engineering manager", "staff engineer", "principal engineer",
    "distinguished engineer", "fellow engineer",
    "chief", "cto", "ciso",
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
