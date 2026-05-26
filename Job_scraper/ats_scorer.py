"""
JD-driven ATS scorer — v1.1.0

How it works
────────────
1. JD KEYWORD EXTRACTION
   Scan the actual job description for every known technical term from a
   DOMAIN-SPECIFIC keyword bank.  The domain is passed in from the caller
   (after classifying the JD via role_classifier.classify()).  This
   prevents cross-domain contamination: Oracle "packages/functions/benefits"
   keywords no longer pollute DevOps JD scoring.

2. WEIGHTED SCORING
   • Terms in the JD title            → base weight × 2  (employer's top priority)
   • Multi-word phrases ("oracle apex", "hcm data loader") → base 2.0
   • Separator terms  ("pl/sql", "suitescript 2.0")        → base 1.5
   • Single words     ("apex", "informatica", "payroll")   → base 1.0
   score = Σ weight(matched) / Σ weight(all JD terms) × 100

3. RESUME MATCHING  (word-boundary regex, not substring)
   matched = JD keywords found in resume → already covered
   missing = JD keywords absent from resume → ADD THESE to boost ATS score

4. RESUME-TYPE PRIORITY
   Each job_type maps to a primary resume.  Primary wins if it scores
   within 10 points of the best — domain fit beats marginal score edge.

5. DOMAIN PARTITIONING (v1.1.0)
   score_resume(domain="devops_cloud")  → uses only DevOps/Cloud keyword bank
   score_resume(domain="oracle_erp")    → uses only Oracle/ERP keyword bank
   score_resume(domain="")             → falls back to merged bank (backward compat)

WHY THIS IS BETTER THAN v1.0.9
   v1.0.9 still used a merged Oracle+ETL bank.  When a DevOps JD mentioned
   "benefits package" in its HR boilerplate, the Oracle resume matched
   "benefits" and "packages" → false 85-100% scores.  v1.1.0 routes each
   JD to the correct single-domain bank so mismatches are impossible.
"""
import re
import logging
from typing import NamedTuple

from config import JOB_TYPES, SCORE_LOW, SCORE_HIGH

log = logging.getLogger(__name__)

# ── Resume-type priority map ──────────────────────────────────────────────────
_PRIMARY_RESUME: dict[str, str] = {
    "oracle pl/sql developer":    "RoopeshN_sql.docx",
    "oracle hcm developer":       "Roopesh_HCM.docx",
    "oracle oic developer":       "Roopesh_OIC.docx",
    "oracle netsuite consultant": "R4_NetSuite_Consultant.docx",
    "oracle fusion developer":    "Roopesh_fusion.docx",
    "oracle apex developer":      "Roopesh_APEX.docx",
    "oracle apps developer":      "Roopesh_Apps.docx",
    "etl developer":              "Roopesh_ETL.docx",
}

_PRIORITY_TOLERANCE = 10.0  # primary wins within this many points of best

# ── Merged keyword bank (all Oracle/ETL job types — backward-compat default) ──
_KEYWORD_BANK: list[str] = sorted(
    {kw for terms in JOB_TYPES.values() for kw in terms},
    key=lambda k: -len(k),   # match "informatica powercenter" before "informatica"
)

# ── Domain-partitioned keyword banks ──────────────────────────────────────────
# Keys MUST match role_classifier.DOMAINS keys exactly.
# Each bank covers only that domain — no cross-contamination.
# DevOps/Cloud keywords are inlined here (sourced from opt_jobscraper/config.py)
# to avoid import-path complexity.

_DEVOPS_CLOUD_KEYWORDS: set[str] = {
    # Core DevOps workflow
    "devops", "dev ops", "ci/cd", "cicd", "continuous integration",
    "continuous delivery", "continuous deployment",
    "jenkins", "github actions", "gitlab ci", "circleci", "teamcity",
    "argocd", "argo cd", "flux", "tekton",
    # Config management / IaC
    "ansible", "puppet", "chef", "saltstack",
    "terraform", "pulumi", "cloudformation", "bicep",
    "infrastructure as code", "iac", "gitops",
    # Containers & orchestration
    "docker", "containers", "containerization",
    "kubernetes", "k8s", "helm", "kustomize",
    # Cloud platforms
    "aws", "amazon web services", "ec2", "s3", "lambda", "rds",
    "eks", "ecs", "fargate", "cloudwatch", "iam", "vpc",
    "aws certified", "solutions architect",
    "azure", "microsoft azure", "aks", "azure devops", "azure pipelines",
    "azure functions", "azure blob", "arm templates",
    "gcp", "google cloud", "gke", "cloud run",
    "cloud engineer", "cloud infrastructure", "cloud architect",
    "cloud operations", "cloud native", "multi-cloud", "hybrid cloud",
    "iaas", "paas", "saas", "serverless",
    # Observability
    "monitoring", "prometheus", "grafana", "datadog", "newrelic",
    "elk stack", "elasticsearch", "logstash", "kibana",
    "observability", "tracing", "jaeger", "zipkin", "opentelemetry",
    # SRE
    "sre", "site reliability", "reliability engineer",
    "slo", "sli", "sla", "error budget",
    "on-call", "incident management", "incident response",
    "postmortem", "runbook", "playbook",
    "chaos engineering", "chaos monkey", "high availability",
    "fault tolerance", "disaster recovery", "scalability", "distributed systems",
    # Platform engineering
    "platform engineer", "platform engineering",
    "internal developer platform", "idp", "developer platform",
    "developer experience", "devex", "backstage", "crossplane",
    "service mesh", "istio", "linkerd", "consul",
    "api gateway", "kong", "nginx", "envoy",
    "vault", "hashicorp", "secrets management",
    # Infrastructure
    "infrastructure engineer",
    "linux administrator", "unix administrator", "systems engineer",
    "vmware", "vsphere", "virtualization",
    "load balancer", "haproxy", "f5",
    "dns", "dhcp", "tcp/ip", "networking",
    "data center", "bare metal",
    # MLOps
    "mlops", "ml ops", "machine learning ops",
    "mlflow", "kubeflow", "airflow", "prefect", "dagster",
    "model deployment", "model serving", "model registry",
    "feature store", "model monitoring",
    "pytorch", "tensorflow",
    "vertex ai", "sagemaker", "azure ml",
    "llmops", "llm", "generative ai deployment",
    # DevSecOps
    "devsecops", "dev sec ops", "platform engineering",
    "application security", "appsec",
    "sast", "dast", "sca", "snyk", "sonarqube", "veracode",
    "container security", "image scanning", "trivy", "clair",
    "secrets scanning", "aws secrets manager",
    "compliance as code", "policy as code", "opa", "open policy agent",
    "vulnerability management", "zero trust", "identity access management",
    # General scripting
    "linux", "bash", "shell scripting", "python",
}

_SOFTWARE_DEV_KEYWORDS: set[str] = {
    # Frameworks
    "spring boot", "spring framework", "hibernate", "jpa", "jakarta ee",
    "react", "angular", "vue", "next.js", "nuxt", "svelte",
    "node.js", "express", "nestjs", "fastapi", "django", "flask",
    # API styles
    "graphql", "rest api", "grpc", "microservices", "event-driven", "websocket",
    # Testing
    "unit testing", "jest", "junit", "pytest", "tdd", "bdd", "integration testing",
    # Auth
    "oauth", "jwt", "saml", "authentication", "authorization", "openid connect",
    # Architecture
    "solid principles", "design patterns", "clean architecture", "ddd",
    "event sourcing", "cqrs", "hexagonal architecture",
    # Languages
    "java", "python", "javascript", "typescript", "c#", "dotnet",
    "go", "golang", "kotlin", "swift", "rust", "scala",
    # Paradigms / roles
    "backend", "frontend", "full stack", "web application", "mobile",
    "android", "ios", "react native", "flutter",
    # Databases (software context)
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "dynamodb",
    # Tooling
    "git", "github", "gitlab", "bitbucket", "jira", "agile", "scrum", "kanban",
    "docker", "kubernetes", "aws", "azure", "ci/cd",
}

_DATA_ENGINEERING_KEYWORDS: set[str] = {
    # Processing engines
    "apache spark", "pyspark", "hadoop", "hdfs", "hive", "pig",
    "apache kafka", "kafka", "apache flink", "flink",
    # Orchestration
    "apache airflow", "airflow", "dagster", "prefect", "luigi", "dbt", "data build tool",
    # Cloud data platforms
    "databricks", "snowflake", "bigquery", "redshift", "azure synapse",
    "synapse analytics", "aws glue", "amazon emr",
    # Storage formats / patterns
    "data warehouse", "data lake", "data lakehouse", "delta lake", "apache iceberg",
    "parquet", "avro", "orc",
    # ETL tools
    "etl", "elt", "data pipeline", "data ingestion", "data transformation",
    "informatica", "informatica powercenter", "informatica iics", "informatica idmc",
    "datastage", "ibm datastage", "talend", "ssis", "azure data factory",
    "oracle data integrator", "odi", "oracle goldengate", "goldengate",
    "nifi", "apache nifi", "pentaho",
    # Streaming
    "spark streaming", "kinesis", "pub/sub", "event streaming", "real-time streaming",
    # Visualization / BI
    "looker", "tableau", "power bi", "qlik", "metabase", "superset",
    # Languages & libs
    "python", "sql", "scala", "java", "pandas", "numpy", "dask",
    # Modeling
    "data modeling", "dimensional modeling", "star schema", "snowflake schema",
    "kimball", "inmon", "data vault", "slowly changing dimension", "scd",
    "fact table", "dimension table",
    # Governance
    "data quality", "data governance", "data catalog", "data lineage",
    "data observability", "great expectations",
    # Databases
    "mysql", "postgresql", "mongodb", "cassandra", "hbase", "redis",
}

_CYBERSECURITY_KEYWORDS: set[str] = {
    # Offense / defense
    "penetration testing", "pentest", "pentesting", "vulnerability assessment",
    "red team", "blue team", "purple team", "threat modeling",
    "exploit", "cve", "cvss", "owasp", "bug bounty",
    # SIEM / monitoring
    "siem", "splunk", "ibm qradar", "elastic siem", "microsoft sentinel",
    # SAST / DAST
    "sast", "dast", "sca", "snyk", "sonarqube", "veracode", "checkmarx",
    "fortify", "semgrep", "bandit",
    # Incident & forensics
    "incident response", "digital forensics", "threat hunting", "threat intelligence",
    "malware analysis", "reverse engineering", "ioc", "mitre att&ck",
    # Identity
    "iam", "pam", "privileged access", "mfa", "saml", "sso",
    "zero trust", "ztna", "identity governance",
    # Compliance
    "pci dss", "hipaa", "soc 2", "iso 27001", "nist", "fedramp", "cmmc",
    "gdpr", "ccpa", "fips",
    # Network security
    "firewall", "ids", "ips", "endpoint", "edr", "xdr", "vpn",
    "network security", "network monitoring", "packet analysis", "wireshark",
    # Cloud security
    "cloud security", "container security", "trivy", "clair", "aqua",
    "aws security", "azure security", "gcp security",
    "devsecops", "secrets management", "vault", "kms",
    # Crypto
    "encryption", "pki", "certificate management", "tls", "ssl",
    "key management", "hsm",
}

_DATABASE_ADMIN_KEYWORDS: set[str] = {
    # Role titles / identity
    "dba", "database administrator", "oracle dba", "sql server dba",
    "mysql dba", "postgresql dba",
    # Oracle-specific DBA
    "rman", "dataguard", "data guard", "oracle rac", "rac",
    "oracle exadata", "data pump", "exp imp", "awr", "ash", "statspack",
    "tablespace", "redo log", "archive log",
    # HA / DR
    "backup and recovery", "replication", "mirroring", "log shipping",
    "always on", "availability group", "failover", "clustering",
    "high availability", "disaster recovery",
    # Tuning
    "performance tuning", "query optimization", "execution plan",
    "index tuning", "explain plan", "partitioning", "indexing",
    # Operations
    "patching", "upgrade", "database migration", "database monitoring",
    # Technologies
    "oracle", "sql server", "mysql", "postgresql", "mongodb",
    "cassandra", "redis", "db2",
    # Languages
    "sql", "pl/sql", "t-sql", "stored procedure", "trigger", "function",
    "view", "materialized view", "index",
    # Design
    "database design", "schema design", "normalization",
    "sharding", "partitioning",
}

# Map role_classifier domain keys → sorted keyword bank
DOMAIN_KEYWORD_BANKS: dict[str, list[str]] = {
    "non_it":           [],              # non-IT jobs are skipped before scoring; 0% if somehow reached
    "oracle_erp":       _KEYWORD_BANK,   # uses the imported Job_scraper/config.py keywords
    "data_engineering": sorted(
        {kw for name, terms in JOB_TYPES.items()
         if "etl" in name.lower()
         for kw in terms}
        | _DATA_ENGINEERING_KEYWORDS,
        key=lambda k: -len(k),
    ),
    "devops_cloud":     sorted(_DEVOPS_CLOUD_KEYWORDS,    key=lambda k: -len(k)),
    "software_dev":     sorted(_SOFTWARE_DEV_KEYWORDS,    key=lambda k: -len(k)),
    "cybersecurity":    sorted(_CYBERSECURITY_KEYWORDS,   key=lambda k: -len(k)),
    "database_admin":   sorted(_DATABASE_ADMIN_KEYWORDS,  key=lambda k: -len(k)),
}

# ── Stopwords (not scored even if found in JD) ───────────────────────────────
_STOPWORDS = {
    "and", "or", "the", "a", "an", "in", "on", "at", "to", "for",
    "of", "with", "is", "are", "be", "will", "must", "have", "has",
    "been", "we", "our", "your", "you", "this", "that", "these",
    "those", "can", "may", "should", "would", "could", "not", "no",
    "as", "by", "from", "up", "about", "into", "through", "during",
    "including", "use", "using", "used", "work", "working", "experience",
    "years", "year", "strong", "good", "excellent", "preferred",
    "required", "ability", "skills", "skill", "knowledge", "team",
    "position", "role", "candidate", "responsibilities", "requirements",
    "qualifications", "minimum", "plus", "bachelor", "degree", "master",
    "certification", "etc", "also", "other", "related", "relevant",
}


class AtsResult(NamedTuple):
    score:       float       # 0–100 weighted score
    matched:     list[str]   # JD keywords found in resume
    missing:     list[str]   # JD keywords absent from resume (add these!)
    best_resume: str         # filename of recommended resume
    label:       str         # HOT / GOOD / OK / SKIP


# ── Helpers ───────────────────────────────────────────────────────────────────

def _term_weight(term: str) -> float:
    """Specificity-based base weight."""
    if " " in term:
        return 2.0   # multi-word phrase: "oracle apex", "hcm data loader"
    if any(c in term for c in "/.-_"):
        return 1.5   # separator term: "pl/sql", "suitescript 2.0"
    return 1.0       # single word


def _wb(term: str) -> re.Pattern:
    """Compile a word-boundary regex for a keyword (cached implicitly by Python)."""
    return re.compile(r"\b" + re.escape(term) + r"\b")


def _build_jd_profile(jd_text: str, jd_title: str, domain: str = "") -> dict[str, float]:
    """
    Scan THIS job description for every known technical keyword.

    Returns {keyword: weight} — the 'requirement profile' of this JD.
    Only terms actually present in the JD are included, so every entry
    is something the employer genuinely mentioned.

    domain (optional): if provided, uses DOMAIN_KEYWORD_BANKS[domain] instead of the
    merged _KEYWORD_BANK.  This prevents cross-domain contamination (e.g. Oracle
    "packages/benefits/functions" keywords matching DevOps JD HR boilerplate).

    Title boost: keywords that also appear in the job title get 2× their
    base weight (they are the employer's headline requirements).
    """
    bank = DOMAIN_KEYWORD_BANKS.get(domain, _KEYWORD_BANK) if domain else _KEYWORD_BANK

    jd_lower    = jd_text.lower()
    title_lower = jd_title.lower()
    profile: dict[str, float] = {}

    for kw in bank:
        # Skip if already captured as part of a longer phrase
        if any(kw in longer for longer in profile if len(longer) > len(kw)):
            continue
        if _wb(kw).search(jd_lower):
            w = _term_weight(kw)
            if _wb(kw).search(title_lower):
                w *= 2.0        # title boost
            profile[kw] = w

    return profile


# ── Core scoring ──────────────────────────────────────────────────────────────

def score_resume(
    resume_text: str,
    jd_text:     str,
    job_type:    str = "",     # kept for API compat; not used for keyword extraction
    jd_title:    str = "",
    domain:      str = "",     # role_classifier domain key (e.g. "devops_cloud")
) -> tuple[float, list[str], list[str]]:
    """
    Score one resume against a job description.

    Returns (weighted_score%, matched_keywords, missing_keywords).

    matched = JD keywords present in resume   (already covered ✓)
    missing = JD keywords absent from resume  (add these to improve score)

    domain: if provided, restricts keyword extraction to that domain's bank.
    Pass the output of role_classifier.classify(jd_text)[0] for best results.
    """
    profile = _build_jd_profile(jd_text, jd_title, domain)
    if not profile:
        return 0.0, [], []

    resume_lower  = resume_text.lower()
    total_weight  = sum(profile.values())
    matched_w     = 0.0
    matched: list[str] = []
    missing: list[str] = []

    for kw, w in profile.items():
        if _wb(kw).search(resume_lower):
            matched.append(kw)
            matched_w += w
        else:
            missing.append(kw)

    score = (matched_w / total_weight) * 100 if total_weight else 0.0
    return round(score, 1), sorted(matched), sorted(missing)


def score_job(job: dict, resumes: dict[str, str]) -> AtsResult:
    """
    Score a job against all loaded resumes; return best match.

    Selection:
      1. Score every resume using the JD profile.
      2. Find the highest scorer.
      3. If the primary resume for this job_type is within
         _PRIORITY_TOLERANCE points, prefer it (domain fit > marginal gain).
    """
    job_type  = job.get("job_type", "")
    jd_text   = job.get("description", "") or ""
    jd_title  = job.get("title", "")        or ""

    if not resumes:
        return AtsResult(0.0, [], [], "No resumes loaded", "SKIP")

    # Score every resume
    results: dict[str, tuple[float, list, list]] = {
        fname: score_resume(rtext, jd_text, job_type, jd_title)
        for fname, rtext in resumes.items()
    }

    best_name  = max(results, key=lambda f: results[f][0])
    best_score = results[best_name][0]

    # Apply primary-resume priority
    primary = _PRIMARY_RESUME.get(job_type.lower(), "")
    chosen  = best_name
    if (primary
            and primary in results
            and results[primary][0] >= best_score - _PRIORITY_TOLERANCE):
        chosen = primary
        log.debug(
            "Resume priority: %s (%.1f) over %s (%.1f) for %s",
            primary, results[primary][0], best_name, best_score, job_type,
        )

    chosen_score, matched, missing = results[chosen]

    if chosen_score >= SCORE_HIGH:   label = "HOT"
    elif chosen_score >= 70:         label = "GOOD"
    elif chosen_score >= SCORE_LOW:  label = "OK"
    else:                            label = "SKIP"

    return AtsResult(chosen_score, matched, missing, chosen, label)
