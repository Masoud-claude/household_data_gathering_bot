"""
Source definitions for all monitored Canadian financial data outlets.

Each source has:
  - name: Display name
  - category: "Government" | "Research" | "Media"
  - url: Homepage / canonical URL
  - feeds: List of RSS feed URLs to poll
  - keywords: Topic-matching keywords (used in addition to global filter)
"""

from dataclasses import dataclass, field
from typing import List

GLOBAL_KEYWORDS = [
    # Households / individuals
    "household", "personal finance", "consumer", "canadian",
    "family", "individual", "resident",
    # Debt & credit
    "debt", "mortgage", "credit card", "loan", "borrowing",
    "debt-to-income", "insolvency", "bankruptcy", "BNPL", "buy now pay later",
    # Savings & wealth
    "savings", "TFSA", "RRSP", "FHSA", "retirement", "pension",
    "net worth", "emergency fund", "investment",
    # Housing
    "housing", "rent", "affordability", "home price", "real estate",
    "homeowner", "renter", "landlord", "vacancy",
    # Income & wages
    "income", "wage", "salary", "minimum wage", "employment income",
    "inequality", "low-income", "poverty",
    # Cost of living
    "inflation", "cost of living", "grocery", "food price", "energy cost",
    "utility", "CPI", "consumer price",
    # Financial health
    "financial stress", "financial literacy", "financial wellbeing",
    "mental health", "anxiety",
    # Banking & fintech
    "banking", "fintech", "digital payment", "open banking", "credit score",
    "credit bureau", "equifax", "transunion",
    # Tax
    "tax", "tax return", "benefit", "CRA", "GST", "HST",
    # Surveys / reports
    "survey", "poll", "report", "study", "index", "data release",
    # Generational
    "millennial", "gen z", "boomer", "generation",
]

# Credibility tag for message formatting
CATEGORY_TAGS = {
    "Government": "🏛️ Government",
    "Research": "🔬 Research",
    "Media": "📰 Media",
}


@dataclass
class Source:
    name: str
    category: str          # "Government" | "Research" | "Media"
    url: str
    feeds: List[str]
    extra_keywords: List[str] = field(default_factory=list)


SOURCES: List[Source] = [
    # ------------------------------------------------------------------ #
    #  GOVERNMENT & REGULATORY                                            #
    # ------------------------------------------------------------------ #
    Source(
        name="Statistics Canada",
        category="Government",
        url="https://www.statcan.gc.ca",
        feeds=[
            "https://www150.statcan.gc.ca/rss/daily-quotidien/daily-rss.xml",
            "https://www150.statcan.gc.ca/rss/new-nouveau/latest-dernier-rss.xml",
        ],
        extra_keywords=["statcan", "census", "labour force survey", "LFS", "SLID",
                        "survey of financial security", "SFS"],
    ),
    Source(
        name="Bank of Canada",
        category="Government",
        url="https://www.bankofcanada.ca",
        feeds=[
            "https://www.bankofcanada.ca/feed/",
            "https://www.bankofcanada.ca/feed/news/",
            "https://www.bankofcanada.ca/feed/publications/",
        ],
        extra_keywords=["monetary policy", "interest rate", "financial stability",
                        "business outlook", "senior loan officer"],
    ),
    Source(
        name="Canada Revenue Agency",
        category="Government",
        url="https://www.canada.ca/en/revenue-agency.html",
        feeds=[
            "https://www.canada.ca/en/revenue-agency/news/newsroom.atom",
        ],
        extra_keywords=["CRA", "tax filing", "NETFILE", "benefit payment",
                        "tax deadline", "refund"],
    ),
    Source(
        name="OSFI",
        category="Government",
        url="https://www.osfi-bsif.gc.ca",
        feeds=[
            "https://www.osfi-bsif.gc.ca/en/news/rss",
        ],
        extra_keywords=["capital", "guideline", "stress test", "B-20",
                        "federally regulated", "DSTI"],
    ),
    Source(
        name="Financial Consumer Agency of Canada",
        category="Government",
        url="https://www.canada.ca/en/financial-consumer-agency.html",
        feeds=[
            "https://www.canada.ca/en/financial-consumer-agency/news/newsroom.atom",
        ],
        extra_keywords=["FCAC", "consumer protection", "financial product",
                        "complaint", "prepaid card"],
    ),
    Source(
        name="CMHC",
        category="Government",
        url="https://www.cmhc-schl.gc.ca",
        feeds=[
            "https://www.cmhc-schl.gc.ca/api/rss/news",
            "https://www.cmhc-schl.gc.ca/api/rss/housing-market-data",
        ],
        extra_keywords=["CMHC", "housing starts", "rental market", "HPI",
                        "housing affordability"],
    ),

    # ------------------------------------------------------------------ #
    #  NON-GOVERNMENTAL & RESEARCH                                        #
    # ------------------------------------------------------------------ #
    Source(
        name="Angus Reid Institute",
        category="Research",
        url="https://angusreid.org",
        feeds=[
            "https://angusreid.org/feed/",
        ],
        extra_keywords=["angus reid", "poll", "survey", "public opinion"],
    ),
    Source(
        name="Nanos Research",
        category="Research",
        url="https://www.nanosresearch.com",
        feeds=[
            "https://www.nanosresearch.com/feed/",
        ],
        extra_keywords=["nanos", "tracking poll", "confidence index"],
    ),
    Source(
        name="Canadian Centre for Policy Alternatives",
        category="Research",
        url="https://www.policyalternatives.ca",
        feeds=[
            "https://www.policyalternatives.ca/rss.xml",
        ],
        extra_keywords=["CCPA", "policy alternative", "progressive"],
    ),
    Source(
        name="C.D. Howe Institute",
        category="Research",
        url="https://www.cdhowe.org",
        feeds=[
            "https://www.cdhowe.org/rss.xml",
        ],
        extra_keywords=["CD Howe", "shadow MPR", "monetary policy council"],
    ),
    Source(
        name="Broadbent Institute",
        category="Research",
        url="https://www.broadbentinstitute.ca",
        feeds=[
            "https://www.broadbentinstitute.ca/feed/",
        ],
        extra_keywords=["broadbent", "inequality", "progressive policy"],
    ),
    Source(
        name="MNP Consumer Debt Index",
        category="Research",
        url="https://mnpdebt.ca",
        feeds=[
            "https://mnpdebt.ca/en/resources/mnp-debt-blog/feed",
        ],
        extra_keywords=["MNP", "debt index", "insolvency", "debt relief"],
    ),
    Source(
        name="Equifax Canada",
        category="Research",
        url="https://www.consumer.equifax.ca",
        feeds=[
            "https://www.equifax.com/personal/education/rss-feed/",
        ],
        extra_keywords=["equifax", "credit bureau", "credit score", "delinquency"],
    ),
    Source(
        name="TransUnion Canada",
        category="Research",
        url="https://www.transunion.ca",
        feeds=[
            "https://newsroom.transunion.com/rss/newsreleases",
        ],
        extra_keywords=["transunion", "credit report", "credit health", "delinquency rate",
                        "consumer credit", "credit demand"],
    ),
    Source(
        name="CPA Canada",
        category="Research",
        url="https://www.cpacanada.ca",
        feeds=[
            "https://www.cpacanada.ca/en/connecting-and-news/rss-feeds/news",
        ],
        extra_keywords=["CPA", "accountant", "financial literacy", "tax planning"],
    ),
    Source(
        name="Fraser Institute",
        category="Research",
        url="https://www.fraserinstitute.org",
        feeds=[
            "https://www.fraserinstitute.org/content/feed",
        ],
        extra_keywords=["fraser", "tax burden", "economic freedom", "fiscal"],
    ),

    # ------------------------------------------------------------------ #
    #  MEDIA & AGGREGATORS                                                #
    # ------------------------------------------------------------------ #
    Source(
        name="Financial Post",
        category="Media",
        url="https://financialpost.com",
        feeds=[
            "https://financialpost.com/feed/",
            "https://financialpost.com/category/personal-finance/feed/",
        ],
        extra_keywords=["financial post", "FP"],
    ),
    Source(
        name="Globe and Mail",
        category="Media",
        url="https://www.theglobeandmail.com",
        feeds=[
            "https://www.theglobeandmail.com/arc/outboundfeeds/rss/category/business/economy/",
            "https://www.theglobeandmail.com/arc/outboundfeeds/rss/category/real-estate/",
        ],
        extra_keywords=["globe and mail", "globe"],
    ),
    Source(
        name="CBC News Business",
        category="Media",
        url="https://www.cbc.ca/news/business",
        feeds=[
            "https://www.cbc.ca/cmlink/rss-business",
            "https://www.cbc.ca/cmlink/rss-canada",
        ],
        extra_keywords=["CBC", "business", "economy"],
    ),
    Source(
        name="BNN Bloomberg Canada",
        category="Media",
        url="https://www.bnnbloomberg.ca",
        feeds=[
            "https://www.bnnbloomberg.ca/feed/",
        ],
        extra_keywords=["BNN", "bloomberg", "market"],
    ),
]

# Topic tag map for classifying updates
TOPIC_TAGS = {
    "#debt": ["debt", "mortgage", "borrowing", "loan", "insolvency", "bankruptcy",
              "credit card", "BNPL", "buy now pay later", "overextended"],
    "#housing": ["housing", "rent", "affordability", "home price", "real estate",
                 "homeowner", "renter", "CMHC", "housing starts", "vacancy", "HPI"],
    "#savings": ["savings", "TFSA", "RRSP", "FHSA", "emergency fund", "net worth",
                 "retirement savings", "pension"],
    "#inflation": ["inflation", "CPI", "cost of living", "grocery", "food price",
                   "consumer price", "energy cost"],
    "#income": ["income", "wage", "salary", "minimum wage", "employment income",
                "poverty", "inequality", "low-income"],
    "#credit": ["credit score", "credit bureau", "equifax", "transunion",
                "credit rating", "delinquency", "arrears"],
    "#sentiment": ["confidence", "sentiment", "survey", "poll", "opinion",
                   "anxiety", "stress", "wellbeing"],
    "#tax": ["tax", "CRA", "GST", "HST", "benefit", "NETFILE", "tax return"],
    "#retirement": ["retirement", "pension", "CPP", "OAS", "RRSP", "annuity"],
    "#banking": ["banking", "fintech", "digital payment", "open banking",
                 "payment", "financial institution"],
    "#generational": ["millennial", "gen z", "boomer", "generation X",
                      "younger", "older", "youth"],
    "#investment": ["investment", "portfolio", "stock", "TFSA", "ETF", "mutual fund"],
}
