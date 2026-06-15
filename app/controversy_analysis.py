from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Tuple
from collections import defaultdict, Counter
import json
import re

from app import crud, schemas, models
from datetime import datetime


HISTORICAL_PERIODS = [
    {"label": "先秦", "year_start": -221, "year_end": 206},
    {"label": "两汉", "year_start": 206, "year_end": 220},
    {"label": "魏晋南北朝", "year_start": 220, "year_end": 589},
    {"label": "隋唐", "year_start": 589, "year_end": 907},
    {"label": "五代十国", "year_start": 907, "year_end": 960},
    {"label": "宋", "year_start": 960, "year_end": 1279},
    {"label": "元", "year_start": 1279, "year_end": 1368},
    {"label": "明", "year_start": 1368, "year_end": 1644},
    {"label": "清", "year_start": 1644, "year_end": 1912},
    {"label": "民国", "year_start": 1912, "year_end": 1949},
    {"label": "现代", "year_start": 1949, "year_end": 2100},
]


def parse_year_to_numeric(year_str: Optional[str]) -> Optional[int]:
    if not year_str:
        return None
    year_str = str(year_str).strip()
    match = re.search(r'(-?\d+)', year_str)
    if match:
        return int(match.group(1))
    return None


def get_period_label(year_numeric: Optional[int]) -> str:
    if year_numeric is None:
        return "未知时期"
    for period in HISTORICAL_PERIODS:
        if period["year_start"] <= year_numeric < period["year_end"]:
            return period["label"]
    return "未知时期"


def calculate_controversy_score(
    total_proposals: int,
    total_votes: int,
    agree_count: int,
    disagree_count: int,
    total_discussions: int,
    evidence_conflict_count: int
) -> Tuple[int, str]:
    base_score = 0
    base_score += min(total_proposals * 10, 30)
    base_score += min(total_votes * 5, 20)
    if total_votes > 0:
        vote_divergence = min(abs(agree_count - disagree_count) / total_votes * 100, 100)
        base_score += int((100 - vote_divergence) * 0.3)
    base_score += min(total_discussions * 3, 20)
    base_score += min(evidence_conflict_count * 15, 30)
    final_score = min(base_score, 100)
    if final_score >= 70:
        heat_level = "high"
    elif final_score >= 40:
        heat_level = "medium"
    else:
        heat_level = "low"
    return final_score, heat_level


def analyze_diff_controversy(db: Session, diff: models.Diff) -> Dict:
    proposals = crud.get_proposals_by_diff(db, diff.id)
    total_proposals = len(proposals)
    total_votes = 0
    agree_count = 0
    disagree_count = 0
    abstain_count = 0
    for p in proposals:
        vote_summary = crud.get_vote_summary(db, p.id)
        total_votes += vote_summary.total_votes
        agree_count += vote_summary.agree_count
        disagree_count += vote_summary.disagree_count
        abstain_count += vote_summary.abstain_count
    discussions = crud.get_discussions_by_diff(db, diff.id)
    total_discussions = len(discussions)
    citations = []
    for p in proposals:
        citations.extend(crud.get_citations_by_proposal(db, p.id))
    evidence_conflict_count = 0
    citation_contents = [c.title for c in citations]
    unique_citations = list(set(citation_contents))
    if len(citation_contents) != len(unique_citations):
        evidence_conflict_count = len(citation_contents) - len(unique_citations)
    controversy_score, heat_level = calculate_controversy_score(
        total_proposals=total_proposals,
        total_votes=total_votes,
        agree_count=agree_count,
        disagree_count=disagree_count,
        total_discussions=total_discussions,
        evidence_conflict_count=evidence_conflict_count
    )
    if total_votes > 0:
        vote_divergence = int((1 - abs(agree_count - disagree_count) / total_votes) * 100)
    else:
        vote_divergence = 0
    version = crud.get_version(db, diff.version_id)
    passage = crud.get_passage(db, diff.passage_id)
    return {
        "diff_id": diff.id,
        "diff_text": diff.text or "",
        "diff_type": diff.diff_type,
        "volume_no": passage.volume_no if passage else 0,
        "paragraph_no": passage.paragraph_no if passage else 0,
        "controversy_score": controversy_score,
        "heat_level": heat_level,
        "total_proposals": total_proposals,
        "total_votes": total_votes,
        "vote_divergence": vote_divergence,
        "evidence_conflict_count": evidence_conflict_count,
        "version_name": version.name if version else "未知",
        "status": diff.status,
        "agree_count": agree_count,
        "disagree_count": disagree_count,
        "abstain_count": abstain_count,
        "total_discussions": total_discussions
    }


def analyze_controversy_heat(
    db: Session,
    project_id: int,
    time_period_start: Optional[str] = None,
    time_period_end: Optional[str] = None,
    region_filter: Optional[str] = None,
    diff_type_filter: Optional[str] = None,
    version_system_filter: Optional[str] = None
) -> schemas.ControversyAnalysisResult:
    project = crud.get_project(db, project_id)
    if not project:
        raise ValueError("项目不存在")
    diffs = crud.get_diffs_with_filters(
        db, project_id,
        time_period_start, time_period_end,
        region_filter, diff_type_filter, version_system_filter
    )
    heat_items = []
    high_count = 0
    medium_count = 0
    low_count = 0
    for diff in diffs:
        controversy_data = analyze_diff_controversy(db, diff)
        heat_items.append(schemas.ControversyHeatItem(**controversy_data))
        if controversy_data["heat_level"] == "high":
            high_count += 1
        elif controversy_data["heat_level"] == "medium":
            medium_count += 1
        else:
            low_count += 1
    heat_items.sort(key=lambda x: x.controversy_score, reverse=True)
    temporal_evolution = analyze_temporal_evolution(db, project_id, diff_type_filter, region_filter)
    regional_distribution = analyze_regional_distribution(db, project_id, diff_type_filter)
    version_system_distribution = analyze_version_system_distribution(db, project_id, diff_type_filter)
    key_findings = generate_controversy_key_findings(
        heat_items, high_count, medium_count, low_count,
        temporal_evolution, regional_distribution
    )
    return schemas.ControversyAnalysisResult(
        project_id=project_id,
        analysis_type="controversy_heat",
        total_diffs_analyzed=len(diffs),
        high_controversy_count=high_count,
        medium_controversy_count=medium_count,
        low_controversy_count=low_count,
        heat_items=heat_items,
        temporal_evolution=temporal_evolution,
        regional_distribution=regional_distribution,
        version_system_distribution=version_system_distribution,
        time_period_start=time_period_start,
        time_period_end=time_period_end,
        region_filter=region_filter,
        diff_type_filter=diff_type_filter,
        version_system_filter=version_system_filter,
        key_findings=key_findings,
        analysis_method="multi_factor_controversy_analysis"
    )


def analyze_temporal_evolution(
    db: Session,
    project_id: int,
    diff_type_filter: Optional[str] = None,
    region_filter: Optional[str] = None
) -> List[schemas.TemporalEvolutionDataPoint]:
    versions = crud.get_versions_with_metadata(db, project_id)
    period_data = defaultdict(lambda: {
        "versions": [],
        "diffs": [],
        "variant_texts": set(),
        "text_counter": Counter()
    })
    for v in versions:
        if region_filter and v.region != region_filter:
            continue
        year_numeric = v.year_numeric or parse_year_to_numeric(v.year)
        period_label = get_period_label(year_numeric)
        period_data[period_label]["versions"].append(v)
        diffs = crud.get_diffs_by_project(db, project_id)
        for d in diffs:
            if d.version_id == v.id:
                if diff_type_filter and d.diff_type != diff_type_filter:
                    continue
                period_data[period_label]["diffs"].append(d)
                if d.text:
                    period_data[period_label]["variant_texts"].add(d.text)
                    period_data[period_label]["text_counter"][d.text] += 1
    result = []
    sorted_periods = sorted(
        period_data.items(),
        key=lambda x: next((p["year_start"] for p in HISTORICAL_PERIODS if p["label"] == x[0]), 9999)
    )
    for period_label, data in sorted_periods:
        period_info = next((p for p in HISTORICAL_PERIODS if p["label"] == period_label), None)
        variant_texts = list(data["variant_texts"])
        dominant_text = ""
        if data["text_counter"]:
            dominant_text = data["text_counter"].most_common(1)[0][0]
        stability_score = calculate_stability_score(data["diffs"], variant_texts)
        change_rate = calculate_change_rate(data["diffs"], len(data["versions"]))
        result.append(schemas.TemporalEvolutionDataPoint(
            period_label=period_label,
            year_start=period_info["year_start"] if period_info else None,
            year_end=period_info["year_end"] if period_info else None,
            version_count=len(data["versions"]),
            diff_count=len(data["diffs"]),
            variant_texts=variant_texts,
            dominant_text=dominant_text,
            stability_score=stability_score,
            change_rate=change_rate
        ))
    crud.delete_temporal_snapshots_by_project(db, project_id)
    for dp in result:
        snapshot_data = schemas.TemporalEvolutionSnapshotCreate(
            project_id=project_id,
            period_label=dp.period_label,
            year_start=dp.year_start,
            year_end=dp.year_end,
            region=region_filter
        )
        snapshot = crud.create_temporal_snapshot(db, snapshot_data)
        crud.update_controversy_analysis(
            db, snapshot.id,
            version_count=dp.version_count,
            diff_count=dp.diff_count,
            variant_texts=json.dumps(dp.variant_texts, ensure_ascii=False),
            dominant_text=dp.dominant_text,
            stability_score=dp.stability_score,
            change_rate=dp.change_rate
        )
    return result


def analyze_regional_distribution(
    db: Session,
    project_id: int,
    diff_type_filter: Optional[str] = None
) -> List[schemas.RegionalDistributionItem]:
    versions = crud.get_versions_with_metadata(db, project_id)
    region_data = defaultdict(lambda: {
        "versions": [],
        "diffs": [],
        "variant_texts": set(),
        "text_counter": Counter(),
        "controversy_scores": []
    })
    for v in versions:
        region = v.region or "未知地域"
        region_data[region]["versions"].append(v)
        diffs = crud.get_diffs_by_project(db, project_id)
        for d in diffs:
            if d.version_id == v.id:
                if diff_type_filter and d.diff_type != diff_type_filter:
                    continue
                region_data[region]["diffs"].append(d)
                if d.text:
                    region_data[region]["variant_texts"].add(d.text)
                    region_data[region]["text_counter"][d.text] += 1
                controversy_data = analyze_diff_controversy(db, d)
                region_data[region]["controversy_scores"].append(controversy_data["controversy_score"])
    result = []
    for region, data in region_data.items():
        unique_variants = list(data["variant_texts"])
        dominant_variant = ""
        if data["text_counter"]:
            dominant_variant = data["text_counter"].most_common(1)[0][0]
        avg_controversy = int(sum(data["controversy_scores"]) / len(data["controversy_scores"])) if data["controversy_scores"] else 0
        result.append(schemas.RegionalDistributionItem(
            region=region,
            version_count=len(data["versions"]),
            diff_count=len(data["diffs"]),
            unique_variants=unique_variants,
            dominant_variant=dominant_variant,
            controversy_score=avg_controversy
        ))
    result.sort(key=lambda x: x.controversy_score, reverse=True)
    return result


def analyze_version_system_distribution(
    db: Session,
    project_id: int,
    diff_type_filter: Optional[str] = None
) -> List[schemas.VersionSystemDistributionItem]:
    versions = crud.get_versions_with_metadata(db, project_id)
    system_data = defaultdict(lambda: {
        "versions": [],
        "diffs": [],
        "variant_texts": set(),
        "text_counter": Counter()
    })
    for v in versions:
        system = v.version_system or "未知系统"
        system_data[system]["versions"].append(v)
        diffs = crud.get_diffs_by_project(db, project_id)
        for d in diffs:
            if d.version_id == v.id:
                if diff_type_filter and d.diff_type != diff_type_filter:
                    continue
                system_data[system]["diffs"].append(d)
                if d.text:
                    system_data[system]["variant_texts"].add(d.text)
                    system_data[system]["text_counter"][d.text] += 1
    result = []
    for system, data in system_data.items():
        unique_variants = list(data["variant_texts"])
        dominant_variant = ""
        if data["text_counter"]:
            dominant_variant = data["text_counter"].most_common(1)[0][0]
        stability_score = calculate_stability_score(data["diffs"], unique_variants)
        result.append(schemas.VersionSystemDistributionItem(
            version_system=system,
            version_count=len(data["versions"]),
            diff_count=len(data["diffs"]),
            unique_variants=unique_variants,
            dominant_variant=dominant_variant,
            stability_score=stability_score
        ))
    result.sort(key=lambda x: x.stability_score, reverse=True)
    return result


def calculate_stability_score(diffs: List, variant_texts: List[str]) -> int:
    if not diffs:
        return 0
    total_diffs = len(diffs)
    unique_variants = len(variant_texts)
    if unique_variants == 0:
        return 100
    if unique_variants == 1:
        return 90
    if total_diffs > 0:
        ratio = unique_variants / total_diffs
        score = int(max(0, 100 - ratio * 100))
        return min(score, 100)
    return 50


def calculate_change_rate(diffs: List, version_count: int) -> int:
    if version_count == 0 or not diffs:
        return 0
    changes_per_version = len(diffs) / version_count
    score = int(min(changes_per_version * 20, 100))
    return score


def generate_controversy_key_findings(
    heat_items: List[schemas.ControversyHeatItem],
    high_count: int,
    medium_count: int,
    low_count: int,
    temporal_evolution: List[schemas.TemporalEvolutionDataPoint],
    regional_distribution: List[schemas.RegionalDistributionItem]
) -> List[str]:
    findings = []
    total = len(heat_items)
    if total == 0:
        findings.append("当前筛选条件下未发现异文数据")
        return findings
    findings.append(f"共分析 {total} 条异文的争议情况")
    findings.append(f"高争议异文 {high_count} 条（{int(high_count/total*100)}%），中争议 {medium_count} 条，低争议 {low_count} 条")
    if high_count > 0:
        top_controversial = heat_items[0]
        findings.append(f"争议度最高的异文：「{top_controversial.diff_text}」，争议分数 {top_controversial.controversy_score}")
    if temporal_evolution:
        periods_with_changes = [p for p in temporal_evolution if p.change_rate > 30]
        if periods_with_changes:
            top_change = max(periods_with_changes, key=lambda x: x.change_rate)
            findings.append(f"文本变化最剧烈的时期：{top_change.period_label}，变化率 {top_change.change_rate}%")
        stable_periods = [p for p in temporal_evolution if p.stability_score >= 70]
        if stable_periods:
            most_stable = max(stable_periods, key=lambda x: x.stability_score)
            findings.append(f"文本最稳定的时期：{most_stable.period_label}，稳定度 {most_stable.stability_score}%")
    if regional_distribution:
        high_controversy_regions = [r for r in regional_distribution if r.controversy_score >= 50]
        if high_controversy_regions:
            top_region = max(high_controversy_regions, key=lambda x: x.controversy_score)
            findings.append(f"争议度最高的地域：{top_region.region}，平均争议分数 {top_region.controversy_score}")
    return findings


def get_diff_controversy_detail(db: Session, diff_id: int) -> schemas.DiffControversyDetail:
    diff = crud.get_diff(db, diff_id)
    if not diff:
        raise ValueError("异文不存在")
    controversy_data = analyze_diff_controversy(db, diff)
    proposals = crud.get_proposals_by_diff(db, diff_id)
    proposal_dicts = []
    supporting_evidences = []
    opposing_evidences = []
    for p in proposals:
        vote_summary = crud.get_vote_summary(db, p.id)
        citations = crud.get_citations_by_proposal(db, p.id)
        review_records = crud.get_review_records_by_proposal(db, p.id)
        proposal_dicts.append({
            "id": p.id,
            "title": p.title,
            "author": p.author,
            "proposed_text": p.proposed_text,
            "rationale": p.rationale,
            "is_accepted": p.is_accepted,
            "created_at": p.created_at,
            "agree_count": vote_summary.agree_count,
            "disagree_count": vote_summary.disagree_count,
            "abstain_count": vote_summary.abstain_count,
            "citations": [{"title": c.title, "author": c.author, "quote_text": c.quote_text} for c in citations],
            "review_records": [{"reviewer": r.reviewer, "result": r.review_result, "comment": r.review_comment} for r in review_records]
        })
        for c in citations:
            evidence = {
                "id": c.id,
                "source": c.title,
                "content": c.quote_text or c.note or "",
                "strength": 80 if c.quote_text else 50,
                "author": c.author
            }
            if p.is_accepted:
                supporting_evidences.append(evidence)
            else:
                opposing_evidences.append(evidence)
    discussions = crud.get_discussions_by_diff(db, diff_id)
    discussion_dicts = []
    for d in discussions:
        discussion_dicts.append({
            "id": d.id,
            "author": d.author,
            "content": d.content,
            "reply_to_id": d.reply_to_id,
            "created_at": d.created_at
        })
    evolution_path = get_diff_evolution_path(db, diff)
    temporal_trend = generate_temporal_trend(db, diff)
    return schemas.DiffControversyDetail(
        diff_id=diff.id,
        diff_text=diff.text or "",
        diff_type=diff.diff_type,
        status=diff.status,
        volume_no=controversy_data["volume_no"],
        paragraph_no=controversy_data["paragraph_no"],
        version_name=controversy_data["version_name"],
        controversy_score=controversy_data["controversy_score"],
        heat_level=controversy_data["heat_level"],
        total_proposals=controversy_data["total_proposals"],
        total_votes=controversy_data["total_votes"],
        total_discussions=controversy_data["total_discussions"],
        vote_divergence=controversy_data["vote_divergence"],
        evidence_conflict_count=controversy_data["evidence_conflict_count"],
        agree_count=controversy_data["agree_count"],
        disagree_count=controversy_data["disagree_count"],
        abstain_count=controversy_data["abstain_count"],
        proposals=proposal_dicts,
        discussions=discussion_dicts,
        supporting_evidences=supporting_evidences,
        opposing_evidences=opposing_evidences,
        evolution_path=evolution_path,
        temporal_trend=temporal_trend
    )


def get_diff_evolution_path(db: Session, diff: models.Diff) -> List[schemas.DiffEvolutionPathItem]:
    versions = crud.get_versions_with_metadata(db, diff.project_id)
    diffs = crud.get_diffs_by_project(db, diff.project_id)
    target_text = diff.text or ""
    path_items = []
    for v in versions:
        year_numeric = v.year_numeric or parse_year_to_numeric(v.year)
        period_label = get_period_label(year_numeric)
        for d in diffs:
            if d.version_id == v.id and d.text == target_text:
                passage = crud.get_passage(db, d.passage_id)
                if passage and passage.volume_no == crud.get_passage(db, diff.passage_id).volume_no:
                    path_items.append(schemas.DiffEvolutionPathItem(
                        diff_id=d.id,
                        diff_text=d.text or "",
                        version_name=v.name,
                        version_year=v.year,
                        version_region=v.region,
                        version_system=v.version_system,
                        year_numeric=year_numeric,
                        diff_type=d.diff_type,
                        status=d.status,
                        period_label=period_label
                    ))
    path_items.sort(key=lambda x: x.year_numeric or 9999)
    return path_items


def generate_temporal_trend(db: Session, diff: models.Diff) -> List[Dict]:
    versions = crud.get_versions_with_metadata(db, diff.project_id)
    period_trend = defaultdict(lambda: {"count": 0, "variants": set()})
    target_text = diff.text or ""
    for v in versions:
        year_numeric = v.year_numeric or parse_year_to_numeric(v.year)
        period_label = get_period_label(year_numeric)
        diffs = crud.get_diffs_by_project(db, diff.project_id)
        for d in diffs:
            if d.version_id == v.id:
                passage = crud.get_passage(db, d.passage_id)
                diff_passage = crud.get_passage(db, diff.passage_id)
                if passage and diff_passage and passage.paragraph_no == diff_passage.paragraph_no:
                    period_trend[period_label]["count"] += 1
                    if d.text:
                        period_trend[period_label]["variants"].add(d.text)
    trend = []
    for period_label, data in sorted(
        period_trend.items(),
        key=lambda x: next((p["year_start"] for p in HISTORICAL_PERIODS if p["label"] == x[0]), 9999)
    ):
        period_info = next((p for p in HISTORICAL_PERIODS if p["label"] == period_label), None)
        trend.append({
            "period_label": period_label,
            "year_start": period_info["year_start"] if period_info else None,
            "year_end": period_info["year_end"] if period_info else None,
            "diff_count": data["count"],
            "variant_count": len(data["variants"]),
            "has_target_text": target_text in data["variants"]
        })
    return trend


def generate_controversy_timeline(
    db: Session,
    project_id: int
) -> List[schemas.ControversyTimelineItem]:
    versions = crud.get_versions_with_metadata(db, project_id)
    period_data = defaultdict(lambda: {
        "diff_count": 0,
        "new_variants": 0,
        "resolved_count": 0,
        "controversy_scores": [],
        "discussion_count": 0,
        "key_events": []
    })
    all_variant_texts = set()
    for v in versions:
        year_numeric = v.year_numeric or parse_year_to_numeric(v.year)
        period_label = get_period_label(year_numeric)
        diffs = crud.get_diffs_by_project(db, project_id)
        period_diffs = [d for d in diffs if d.version_id == v.id]
        period_data[period_label]["diff_count"] += len(period_diffs)
        for d in period_diffs:
            if d.text and d.text not in all_variant_texts:
                all_variant_texts.add(d.text)
                period_data[period_label]["new_variants"] += 1
            if d.status == "finalized":
                period_data[period_label]["resolved_count"] += 1
            controversy_data = analyze_diff_controversy(db, d)
            period_data[period_label]["controversy_scores"].append(controversy_data["controversy_score"])
            discussions = crud.get_discussions_by_diff(db, d.id)
            period_data[period_label]["discussion_count"] += len(discussions)
    timeline = []
    for period_label, data in sorted(
        period_data.items(),
        key=lambda x: next((p["year_start"] for p in HISTORICAL_PERIODS if p["label"] == x[0]), 9999)
    ):
        period_info = next((p for p in HISTORICAL_PERIODS if p["label"] == period_label), None)
        avg_controversy = int(sum(data["controversy_scores"]) / len(data["controversy_scores"])) if data["controversy_scores"] else 0
        key_events = []
        if data["new_variants"] > 0:
            key_events.append(f"新增 {data['new_variants']} 种异文变体")
        if data["resolved_count"] > 0:
            key_events.append(f"{data['resolved_count']} 条异文达成定论")
        if avg_controversy >= 50:
            key_events.append(f"学术争议活跃度较高")
        timeline.append(schemas.ControversyTimelineItem(
            period_label=period_label,
            year_start=period_info["year_start"] if period_info else None,
            year_end=period_info["year_end"] if period_info else None,
            diff_count=data["diff_count"],
            new_variants=data["new_variants"],
            resolved_count=data["resolved_count"],
            controversy_score=avg_controversy,
            discussion_count=data["discussion_count"],
            key_events=key_events
        ))
    return timeline


def classify_diff_evolution_type(
    db: Session,
    diff: models.Diff
) -> str:
    evolution_path = get_diff_evolution_path(db, diff)
    if len(evolution_path) < 2:
        return "insufficient_data"
    periods = [item.period_label for item in evolution_path]
    unique_periods = len(set(periods))
    total_periods = len(periods)
    if unique_periods == total_periods and len(evolution_path) >= 3:
        texts = [item.diff_text for item in evolution_path]
        if len(set(texts)) == 1:
            return "stable_inheritance"
    latest_year = evolution_path[-1].year_numeric or 0
    earliest_year = evolution_path[0].year_numeric or 0
    if latest_year - earliest_year < 100 and len(evolution_path) <= 2:
        return "late_addition"
    controversy_data = analyze_diff_controversy(db, diff)
    if controversy_data["controversy_score"] >= 50 and diff.status != "finalized":
        return "unresolved_controversy"
    if len(set([item.diff_text for item in evolution_path])) >= 3:
        return "divergent_evolution"
    return "gradual_evolution"


def generate_controversy_report_content(
    db: Session,
    project_id: int,
    analysis_result: schemas.ControversyAnalysisResult,
    created_by: Optional[str] = None
) -> Tuple[str, str, Dict]:
    project = crud.get_project(db, project_id)
    sections = []
    sections.append("=" * 60)
    sections.append("异文时空演化与学术争议分析报告")
    sections.append("=" * 60)
    sections.append("")
    sections.append("一、基本信息")
    sections.append("-" * 40)
    sections.append(f"项目: {project.name if project else '未知'}")
    sections.append(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    sections.append(f"分析方法: {analysis_result.analysis_method}")
    sections.append(f"分析人员: {created_by or '系统自动'}")
    sections.append("")
    filter_info = []
    if analysis_result.time_period_start:
        filter_info.append(f"起始时期: {analysis_result.time_period_start}")
    if analysis_result.time_period_end:
        filter_info.append(f"结束时期: {analysis_result.time_period_end}")
    if analysis_result.region_filter:
        filter_info.append(f"地域: {analysis_result.region_filter}")
    if analysis_result.diff_type_filter:
        filter_info.append(f"异文类型: {analysis_result.diff_type_filter}")
    if analysis_result.version_system_filter:
        filter_info.append(f"版本系统: {analysis_result.version_system_filter}")
    if filter_info:
        sections.append("筛选条件:")
        for info in filter_info:
            sections.append(f"  - {info}")
        sections.append("")
    sections.append("二、争议概况")
    sections.append("-" * 40)
    sections.append(f"分析异文总数: {analysis_result.total_diffs_analyzed}")
    sections.append(f"高争议异文: {analysis_result.high_controversy_count} 条")
    sections.append(f"中争议异文: {analysis_result.medium_controversy_count} 条")
    sections.append(f"低争议异文: {analysis_result.low_controversy_count} 条")
    sections.append("")
    if analysis_result.heat_items:
        sections.append("三、高争议异文排行")
        sections.append("-" * 40)
        for i, item in enumerate(analysis_result.heat_items[:10], 1):
            sections.append(f"{i}. 「{item.diff_text}」(ID:{item.diff_id})")
            sections.append(f"   争议分数: {item.controversy_score} | 类型: {item.diff_type}")
            sections.append(f"   位置: 第{item.volume_no}卷第{item.paragraph_no}段 | 版本: {item.version_name}")
            sections.append(f"   提案数: {item.total_proposals} | 投票数: {item.total_votes}")
            sections.append("")
    if analysis_result.temporal_evolution:
        sections.append("四、时空演化分析")
        sections.append("-" * 40)
        for dp in analysis_result.temporal_evolution:
            period_range = f"({dp.year_start}-{dp.year_end}年)" if dp.year_start else ""
            sections.append(f"{dp.period_label} {period_range}:")
            sections.append(f"  版本数: {dp.version_count} | 异文数: {dp.diff_count}")
            sections.append(f"  稳定度: {dp.stability_score}% | 变化率: {dp.change_rate}%")
            sections.append(f"  主导文本: {dp.dominant_text or '无'}")
            if dp.variant_texts:
                sections.append(f"  变体: {', '.join(dp.variant_texts[:5])}")
            sections.append("")
    if analysis_result.regional_distribution:
        sections.append("五、地域分布分析")
        sections.append("-" * 40)
        for item in analysis_result.regional_distribution:
            sections.append(f"{item.region}:")
            sections.append(f"  版本数: {item.version_count} | 异文数: {item.diff_count}")
            sections.append(f"  平均争议度: {item.controversy_score}%")
            sections.append(f"  主导变体: {item.dominant_variant or '无'}")
            sections.append("")
    if analysis_result.key_findings:
        sections.append("六、主要发现")
        sections.append("-" * 40)
        for i, finding in enumerate(analysis_result.key_findings, 1):
            sections.append(f"{i}. {finding}")
        sections.append("")
    sections.append("七、分类统计")
    sections.append("-" * 40)
    high_controversy_count = analysis_result.high_controversy_count
    stable_inheritance_count = 0
    late_addition_count = 0
    unresolved_count = 0
    for item in analysis_result.heat_items:
        diff = crud.get_diff(db, item.diff_id)
        if diff:
            evo_type = classify_diff_evolution_type(db, diff)
            if evo_type == "stable_inheritance":
                stable_inheritance_count += 1
            elif evo_type == "late_addition":
                late_addition_count += 1
            elif evo_type == "unresolved_controversy":
                unresolved_count += 1
    sections.append(f"长期稳定传承: {stable_inheritance_count} 条")
    sections.append(f"后期增改: {late_addition_count} 条")
    sections.append(f"争议未决: {unresolved_count} 条")
    sections.append("")
    sections.append("八、建议")
    sections.append("-" * 40)
    suggestions = generate_analysis_suggestions(analysis_result, stable_inheritance_count, late_addition_count, unresolved_count)
    for i, suggestion in enumerate(suggestions, 1):
        sections.append(f"{i}. {suggestion}")
    sections.append("")
    sections.append("=" * 60)
    sections.append("报告结束")
    sections.append("=" * 60)
    content = "\n".join(sections)
    summary = f"异文争议分析报告。共分析 {analysis_result.total_diffs_analyzed} 条异文，其中高争议 {analysis_result.high_controversy_count} 条，稳定传承 {stable_inheritance_count} 条，争议未决 {unresolved_count} 条。"
    stats = {
        "high_controversy_count": high_controversy_count,
        "stable_inheritance_count": stable_inheritance_count,
        "late_addition_count": late_addition_count,
        "unresolved_count": unresolved_count
    }
    return content, summary, stats


def generate_analysis_suggestions(
    analysis_result: schemas.ControversyAnalysisResult,
    stable_count: int,
    late_count: int,
    unresolved_count: int
) -> List[str]:
    suggestions = []
    if analysis_result.high_controversy_count > 0:
        suggestions.append(f"建议优先处理 {analysis_result.high_controversy_count} 条高争议异文，组织专家进行专题研讨")
    if unresolved_count > 0:
        suggestions.append(f"对 {unresolved_count} 条争议未决的异文，建议补充更多文献证据，必要时进行学术投票")
    if late_count > 0:
        suggestions.append(f"识别出 {late_count} 条可能为后期增改的异文，建议结合版本序跋和避讳字等进行断代研究")
    if stable_count > 0:
        suggestions.append(f"{stable_count} 条异文呈现长期稳定传承特征，可作为版本谱系划分的重要依据")
    if analysis_result.temporal_evolution:
        high_change_periods = [p for p in analysis_result.temporal_evolution if p.change_rate > 50]
        if high_change_periods:
            period_names = "、".join([p.period_label for p in high_change_periods])
            suggestions.append(f"{period_names}时期文本变化剧烈，建议重点考察该时期的社会文化背景对文本的影响")
    if not suggestions:
        suggestions.append("当前数据分布较为均衡，建议结合具体研究需求进行深入分析")
    return suggestions


def get_heat_level_label(level: str) -> str:
    labels = {
        "high": "高争议",
        "medium": "中争议",
        "low": "低争议"
    }
    return labels.get(level, level)


def get_evolution_type_label(evo_type: str) -> str:
    labels = {
        "stable_inheritance": "长期稳定传承",
        "late_addition": "后期增改",
        "unresolved_controversy": "争议未决",
        "divergent_evolution": "分化演变",
        "gradual_evolution": "渐进演变",
        "insufficient_data": "数据不足"
    }
    return labels.get(evo_type, evo_type)
