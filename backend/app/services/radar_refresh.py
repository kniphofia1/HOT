from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.db.models import FetchRun, Source
from app.services.clustering import ClusterRunResult, run_event_clustering
from app.services.connector_runner import run_enabled_sources, run_source_fetch
from app.services.editorial import EditorialRunResult, edit_event_clusters
from app.services.industry_classifier import IndustryClassificationRunResult, classify_event_clusters
from app.services.scoring import ScoreRunResult, recompute_hot_scores
from app.services.translation import TranslationRunResult, translate_event_clusters


@dataclass
class RadarRefreshResult:
    fetch_runs: list[FetchRun]
    clustering: ClusterRunResult
    classification: IndustryClassificationRunResult
    translation: TranslationRunResult
    editorial: EditorialRunResult
    scoring: ScoreRunResult
    errors: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        return "partial" if self.errors else "success"


def refresh_all_sources(
    db: Session,
    *,
    cluster_limit: int = 100,
    translation_limit: int = 100,
    editorial_limit: int = 100,
) -> RadarRefreshResult:
    fetch_runs = run_enabled_sources(db)
    return _finish_refresh(
        db,
        fetch_runs=fetch_runs,
        cluster_limit=cluster_limit,
        translation_limit=translation_limit,
        editorial_limit=editorial_limit,
    )


def refresh_single_source(
    db: Session,
    source: Source,
    *,
    cluster_limit: int = 100,
    translation_limit: int = 100,
    editorial_limit: int = 100,
) -> RadarRefreshResult:
    fetch_run = run_source_fetch(db, source)
    return _finish_refresh(
        db,
        fetch_runs=[fetch_run],
        cluster_limit=cluster_limit,
        translation_limit=translation_limit,
        editorial_limit=editorial_limit,
    )


def _finish_refresh(
    db: Session,
    *,
    fetch_runs: list[FetchRun],
    cluster_limit: int,
    translation_limit: int,
    editorial_limit: int,
) -> RadarRefreshResult:
    clustering = run_event_clustering(db, limit=cluster_limit)
    classification = classify_event_clusters(db, limit=cluster_limit)
    translation = translate_event_clusters(db, limit=translation_limit)
    editorial = edit_event_clusters(db, limit=editorial_limit)
    scoring = recompute_hot_scores(db)
    errors = [run.error_message for run in fetch_runs if run.error_message]
    errors.extend(clustering.errors)
    errors.extend(classification.errors)
    errors.extend(translation.errors)
    errors.extend(editorial.errors)
    return RadarRefreshResult(
        fetch_runs=fetch_runs,
        clustering=clustering,
        classification=classification,
        translation=translation,
        editorial=editorial,
        scoring=scoring,
        errors=errors,
    )
