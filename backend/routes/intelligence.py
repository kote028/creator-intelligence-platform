from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, selectinload

from app.auth_dependencies import get_current_user
from app.database import get_db
from app.llm import LLMUnavailable, grounded_answer
from app.models.campaign import Campaign
from app.models.creator import Creator
from app.models.creator_metric import CreatorMetric
from app.models.social_account import SocialAccount
from app.models.sponsorship import Sponsorship
from app.models.user import User
from app.semantic_search import semantic_scores
from schemas.intelligence import (
    IntelligenceAskRequest,
    IntelligenceAskResponse,
    IntelligenceSource,
)

router = APIRouter(prefix="/intelligence", tags=["Marketplace intelligence"])


def _latest_metrics(db: Session, accounts: list[SocialAccount]) -> dict[int, CreatorMetric]:
    account_ids = [account.account_id for account in accounts]
    if not account_ids:
        return {}
    rows = (
        db.query(CreatorMetric)
        .filter(
            CreatorMetric.account_id.in_(account_ids),
            CreatorMetric.data_source != "youtube_public",
        )
        .order_by(CreatorMetric.metric_date.desc(), CreatorMetric.metric_id.desc())
        .all()
    )
    latest = {}
    for row in rows:
        latest.setdefault(row.account_id, row)
    return latest


def _creator_sources(db: Session, question: str) -> list[dict]:
    creators = (
        db.query(Creator)
        .options(selectinload(Creator.social_accounts))
        .order_by(Creator.creator_id)
        .limit(1000)
        .all()
    )
    if not creators:
        return []
    documents = [
        " ".join((c.display_name or "", c.bio or "", c.niche or "", c.country or "", c.city or "", " ".join(a.platform for a in c.social_accounts)))
        for c in creators
    ]
    scores = semantic_scores(question, documents)
    accounts = [account for creator in creators for account in creator.social_accounts]
    metrics = _latest_metrics(db, accounts)
    matches = []
    for creator, score in zip(creators, scores):
        stats = [metrics[account.account_id] for account in creator.social_accounts if account.account_id in metrics]
        metric = max(stats, key=lambda row: (int(row.avg_views or 0), int(row.followers or 0)), default=None)
        followers = int(metric.followers or 0) if metric else max((int(a.followers or 0) for a in creator.social_accounts), default=0)
        facts = {
            "creator_id": creator.creator_id,
            "display_name": creator.display_name or creator.username,
            "username": creator.username,
            "bio": (creator.bio or "")[:600],
            "niche": creator.niche,
            "location": ", ".join(v for v in [creator.city, creator.country] if v) or None,
            "platforms": sorted({a.platform for a in creator.social_accounts}),
            "followers": followers,
            "average_views_per_post": int(metric.avg_views or 0) if metric else None,
            "engagement_rate_percent": float(metric.engagement_rate or 0) if metric else None,
            "text_relevance_score_percent": round(max(0, min(1, score)) * 100, 1),
        }
        if score > 0 or not question.strip():
            matches.append({
                "source_id": f"creator_{creator.creator_id}",
                "kind": "creator",
                "label": f"{facts['display_name']} · {creator.niche or 'Creator'}",
                "facts": facts,
                "_score": score,
            })
    matches.sort(key=lambda row: row["_score"], reverse=True)
    for match in matches:
        match.pop("_score", None)
    return matches[:6]


def _campaign_source(campaign: Campaign, audience: str, sponsorships: list[Sponsorship] | None = None) -> dict:
    facts = {
        "campaign_id": campaign.campaign_id,
        "campaign_name": campaign.campaign_name,
        "brief": (campaign.description or "")[:700],
        "status": campaign.status,
        "advertising_field": campaign.advertising_field,
        "target_niche": campaign.target_niche,
        "target_country": campaign.target_country,
        "target_platform": campaign.target_platform,
        "budget": float(campaign.budget or 0) if audience == "brand" else None,
        "budget_visibility": "company-only" if audience == "brand" else "not shared with creators",
    }
    if sponsorships is not None:
        status_counts: dict[str, int] = defaultdict(int)
        impressions = clicks = conversions = 0
        revenue = 0.0
        reported_count = 0
        for sponsorship in sponsorships:
            status_counts[sponsorship.status] += 1
            result = sponsorship.result
            if result:
                reported_count += 1
                impressions += int(result.impressions)
                clicks += int(result.clicks)
                conversions += int(result.conversions)
                revenue += float(result.attributed_revenue)
        facts.update({
            "partnership_count": len(sponsorships),
            "partnerships_by_status": dict(status_counts),
            "campaigns_with_reported_results": reported_count,
            "reported_impressions": impressions,
            "reported_clicks": clicks,
            "reported_conversions": conversions,
            "reported_attributed_revenue": round(revenue, 2),
        })
    return {
        "source_id": f"campaign_{campaign.campaign_id}",
        "kind": "campaign",
        "label": campaign.campaign_name,
        "facts": facts,
    }


def _viewer_context(db: Session, user: User, question: str) -> list[dict]:
    sources: list[dict] = []
    if user.role == "brand" and user.brand:
        sources.extend(_creator_sources(db, question))
        campaigns = (
            db.query(Campaign)
            .filter(Campaign.brand_id == user.brand.brand_id)
            .order_by(Campaign.campaign_id.desc())
            .limit(10)
            .all()
        )
        for campaign in campaigns:
            partnerships = (
                db.query(Sponsorship)
                .options(selectinload(Sponsorship.result))
                .filter(Sponsorship.campaign_id == campaign.campaign_id)
                .all()
            )
            sources.append(_campaign_source(campaign, "brand", partnerships))
        return sources[:12]

    if user.role == "creator" and user.creator:
        creator = user.creator
        accounts = db.query(SocialAccount).filter(SocialAccount.creator_id == creator.creator_id).all()
        metrics = _latest_metrics(db, accounts)
        social_metrics = [metrics[account.account_id] for account in accounts if account.account_id in metrics]
        profile_facts = {
            "creator_id": creator.creator_id,
            "display_name": creator.display_name or creator.username,
            "username": creator.username,
            "bio": (creator.bio or "")[:600],
            "niche": creator.niche,
            "location": ", ".join(v for v in [creator.city, creator.country] if v) or None,
            "platforms": sorted({account.platform for account in accounts}),
            "followers": max((int(row.followers or 0) for row in social_metrics), default=0),
            "average_views_per_post": max((int(row.avg_views or 0) for row in social_metrics), default=0),
            "engagement_rate_percent": max((float(row.engagement_rate or 0) for row in social_metrics), default=0),
        }
        sources.append({
            "source_id": f"creator_{creator.creator_id}",
            "kind": "your_profile",
            "label": f"Your profile · {profile_facts['display_name']}",
            "facts": profile_facts,
        })

        partnerships = (
            db.query(Sponsorship)
            .join(Campaign)
            .options(selectinload(Sponsorship.result))
            .filter(Sponsorship.creator_id == creator.creator_id)
            .order_by(Sponsorship.created_at.desc())
            .limit(8)
            .all()
        )
        by_field: dict[str, dict] = {}
        for sponsorship in partnerships:
            campaign = sponsorship.campaign
            result = sponsorship.result
            facts = {
                "campaign_id": campaign.campaign_id,
                "campaign_name": campaign.campaign_name,
                "advertising_field": campaign.advertising_field or campaign.target_niche,
                "status": sponsorship.status,
                "agreed_amount": float(sponsorship.agreed_amount),
                "has_brand_reported_results": bool(result),
                "reported_impressions": int(result.impressions) if result else None,
                "reported_clicks": int(result.clicks) if result else None,
                "reported_conversions": int(result.conversions) if result else None,
                "reported_attributed_revenue": float(result.attributed_revenue) if result else None,
            }
            sources.append({
                "source_id": f"partnership_{sponsorship.sponsorship_id}",
                "kind": "partnership",
                "label": f"{campaign.campaign_name} · {sponsorship.status}",
                "facts": facts,
            })
            if result:
                field = str(facts["advertising_field"] or "Other / uncategorized")
                row = by_field.setdefault(field, {"field": field, "reported_campaigns": 0, "impressions": 0, "clicks": 0, "conversions": 0, "attributed_revenue": 0.0})
                row["reported_campaigns"] += 1
                row["impressions"] += int(result.impressions)
                row["clicks"] += int(result.clicks)
                row["conversions"] += int(result.conversions)
                row["attributed_revenue"] += float(result.attributed_revenue)
        for field, facts in by_field.items():
            sources.append({
                "source_id": f"field_{len(sources)}",
                "kind": "advertising_field_results",
                "label": f"Reported results · {field}",
                "facts": facts,
            })

        campaigns = db.query(Campaign).filter(Campaign.status == "active").order_by(Campaign.campaign_id.desc()).limit(100).all()
        campaign_docs = [" ".join((c.campaign_name, c.description or "", c.advertising_field or "", c.target_niche or "", c.target_platform or "")) for c in campaigns]
        campaign_scores = semantic_scores(question, campaign_docs) if campaign_docs else []
        active_matches = sorted(zip(campaign_scores, campaigns), key=lambda item: item[0], reverse=True)
        for score, campaign in active_matches[:5]:
            if score <= 0:
                continue
            sources.append(_campaign_source(campaign, "creator"))
        return sources[:12]
    return []


def _local_answer(question: str, sources: list[dict]) -> tuple[str, list[str]]:
    if not sources:
        return (
            "I couldn’t find marketplace records to answer that yet. Add creator profile details, campaign briefs, or reported results, then ask again.",
            [],
        )
    query = question.casefold()
    creator_intent = any(word in query for word in ("creator", "influencer", "match", "find", "recommend", "profile", "niche"))
    campaign_intent = any(word in query for word in ("campaign", "offer", "application", "partnership", "brief", "budget"))
    impact_intent = any(word in query for word in ("impact", "field", "advertis", "impression", "click", "conversion", "revenue", "perform"))
    creators = [source for source in sources if source["kind"] == "creator"] if creator_intent else []
    campaigns = [source for source in sources if source["kind"] == "campaign"] if campaign_intent else []
    field_results = [source for source in sources if source["kind"] == "advertising_field_results"]
    if impact_intent and field_results:
        field_results.sort(key=lambda source: source["facts"].get("conversions", 0), reverse=True)
        selected = field_results[:3]
        lines = []
        for source in selected:
            facts = source["facts"]
            lines.append(
                f"{facts['field']}: {facts['reported_campaigns']} campaigns with brand-reported results, "
                f"{facts['impressions']:,} impressions, {facts['clicks']:,} clicks, "
                f"{facts['conversions']:,} conversions, and ${facts['attributed_revenue']:,.2f} attributed revenue."
            )
        return "Your reported advertising-field impact:\n" + "\n".join(lines), [source["source_id"] for source in selected]
    if creators:
        selected = creators[:3]
        lines = []
        for source in selected:
            facts = source["facts"]
            line = f"{facts['display_name']}"
            if facts.get("niche"):
                line += f" ({facts['niche']})"
            line += f" — {facts['followers']:,} followers"
            if facts.get("engagement_rate_percent") is not None:
                line += f", {facts['engagement_rate_percent']:.1f}% reported engagement"
            lines.append(line)
        return "Relevant creator profiles from marketplace data:\n" + "\n".join(lines), [source["source_id"] for source in selected]
    if campaigns:
        selected = campaigns[:3]
        lines = [
            f"{source['label']} — {source['facts'].get('advertising_field') or source['facts'].get('target_niche') or 'field not specified'}; status: {source['facts'].get('status', 'unknown')}"
            for source in selected
        ]
        return "Relevant campaign records:\n" + "\n".join(lines), [source["source_id"] for source in selected]
    selected = field_results[:3] or sources[:4]
    return (
        "I found these related marketplace records. The source cards show the exact profile, partnership, or reported outcome data available for your question.",
        [source["source_id"] for source in selected],
    )


@router.post("/ask", response_model=IntelligenceAskResponse)
def ask_marketplace_intelligence(
    request: IntelligenceAskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    question = request.question.strip()
    conversation = [turn.model_dump() for turn in request.conversation[-8:]]
    retrieval_query = " ".join([turn["content"] for turn in conversation if turn["role"] == "user"][-3:] + [question])
    all_sources = _viewer_context(db, current_user, retrieval_query)
    by_id = {source["source_id"]: source for source in all_sources}
    answer = None
    cited_ids: list[str] = []
    provider = "local"
    if all_sources:
        try:
            generated = grounded_answer(question, all_sources, conversation)
            if generated:
                source_ids = generated["source_ids"]
                if any(not isinstance(source_id, str) or source_id not in by_id for source_id in source_ids):
                    raise LLMUnavailable("The answer referenced unavailable marketplace records")
                answer = generated["answer"].strip()
                cited_ids = list(dict.fromkeys(source_ids))[:6]
                suggested_questions = [item.strip() for item in generated.get("suggested_questions", []) if isinstance(item, str) and item.strip()][:3]
                provider = "openai"
        except LLMUnavailable:
            provider = "local_fallback"
    if answer is None:
        answer, cited_ids = _local_answer(retrieval_query, all_sources)
        suggested_questions = []
        if current_user.role == "creator":
            suggested_questions = ["Which advertising field has my strongest reported results?", "What can improve my fit for active campaigns?"]
        else:
            suggested_questions = ["Which creators best match a campaign brief?", "Summarize my campaign applications and results."]
    return IntelligenceAskResponse(
        answer=answer,
        provider=provider,
        sources=[by_id[source_id] for source_id in cited_ids if source_id in by_id],
        suggested_questions=suggested_questions,
        grounded=True,
    )
