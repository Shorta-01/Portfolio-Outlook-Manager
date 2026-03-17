import json
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.alert_event import AlertEvent
from app.models.alert_rule import AlertRule
from app.models.app_setting import AppSetting
from app.models.asset import Asset, AssetMode
from app.repositories.action_snapshot_repo import ActionSnapshotRepository
from app.repositories.alert_event_repo import AlertEventRepository
from app.repositories.alert_rule_repo import AlertRuleRepository
from app.repositories.asset_repo import AssetRepository
from app.repositories.market_quote_repo import MarketQuoteRepository
from app.repositories.outlook_snapshot_repo import OutlookSnapshotRepository
from app.repositories.settings_repo import SettingsRepository
from app.services.scheduler_state import scheduler_state
from app.services.valuation_service import ValuationService
from app.repositories.fx_rate_repo import FXRateRepository
from app.repositories.lot_repo import LotRepository


class AlertEngineService:
    def __init__(self, db: Session):
        self.db = db
        self.asset_repo = AssetRepository(db)
        self.rule_repo = AlertRuleRepository(db)
        self.event_repo = AlertEventRepository(db)
        self.quote_repo = MarketQuoteRepository(db)
        self.outlook_repo = OutlookSnapshotRepository(db)
        self.action_repo = ActionSnapshotRepository(db)
        self.settings_repo = SettingsRepository(db)
        self.valuation_service = ValuationService(LotRepository(db), MarketQuoteRepository(db), FXRateRepository(db))

    def ensure_default_settings(self) -> AppSetting:
        settings = self.settings_repo.get_first()
        if settings is None:
            settings = self.settings_repo.upsert({
                "portfolio_base_currency": "EUR",
                "default_poll_every_minutes": 5,
                "use_market_hours_default": False,
                "alerts_enabled_global": True,
                "default_alert_cooldown_minutes": 60,
                "default_maturity_soon_days": 30,
            })
            self.db.flush()
        return settings

    def run_once(self) -> dict:
        try:
            settings = self.ensure_default_settings()
            if not settings.alerts_enabled_global:
                scheduler_state.mark_job_success("alerts")
                return {"created": 0, "resolved": 0, "evaluated_rules": 0}

            created = 0
            resolved = 0
            rules = self.rule_repo.list_enabled()
            assets = self.asset_repo.list_all()
            for rule in rules:
                for asset in self._assets_for_rule(rule, assets):
                    fired = self._evaluate_rule(rule, asset, settings)
                    if fired:
                        created += 1
                    res = self._resolve_if_needed(rule, asset, settings)
                    if res:
                        resolved += 1
            scheduler_state.mark_job_success("alerts")
            return {"created": created, "resolved": resolved, "evaluated_rules": len(rules)}
        except Exception as exc:
            scheduler_state.mark_job_failure("alerts", str(exc))
            raise

    def _assets_for_rule(self, rule: AlertRule, all_assets: list[Asset]) -> list[Asset]:
        if rule.asset_id is not None:
            asset = self.asset_repo.get(rule.asset_id)
            return [asset] if asset else []
        assets = all_assets
        if rule.asset_mode_scope:
            assets = [a for a in assets if a.asset_mode.value == rule.asset_mode_scope]
        if rule.asset_type_scope:
            assets = [a for a in assets if a.asset_type.value == rule.asset_type_scope]
        if rule.rule_type == "maturity_soon":
            assets = [a for a in assets if a.asset_mode == AssetMode.TERM_DEPOSIT or a.asset_type.value == "term_deposit"]
        return assets

    def _parse_threshold(self, rule: AlertRule, default: Decimal = Decimal("0")) -> Decimal:
        if rule.threshold_value is None or rule.threshold_value == "":
            return default
        return Decimal(str(rule.threshold_value))

    def _should_skip_by_dedupe_or_cooldown(self, rule: AlertRule, asset_id: int | None, dedupe_key: str) -> bool:
        latest = self.event_repo.latest_by_rule_asset(rule.id, asset_id)
        if latest and latest.dedupe_key == dedupe_key and latest.is_active:
            return True
        if latest:
            cooldown = timedelta(minutes=rule.cooldown_minutes)
            if latest.timestamp_utc >= datetime.utcnow() - cooldown:
                return True
        return False

    def _create_event(self, *, rule: AlertRule, asset: Asset | None, dedupe_key: str, title: str, message: str, old_state: dict | None = None, new_state: dict | None = None) -> bool:
        if self._should_skip_by_dedupe_or_cooldown(rule, asset.id if asset else None, dedupe_key):
            return False
        event = AlertEvent(
            asset_id=asset.id if asset else None,
            alert_rule_id=rule.id,
            timestamp_utc=datetime.utcnow(),
            severity=rule.severity,
            alert_type=rule.rule_type,
            title=title,
            message=message,
            old_state_json=json.dumps(old_state) if old_state else None,
            new_state_json=json.dumps(new_state) if new_state else None,
            dedupe_key=dedupe_key,
            is_read=False,
            is_active=True,
            created_by_engine=True,
        )
        self.event_repo.add(event)
        return True

    def _evaluate_rule(self, rule: AlertRule, asset: Asset, settings: AppSetting) -> bool:
        if rule.rule_type in {"price_up_pct", "price_down_pct", "price_above", "price_below", "quote_stale", "incomplete_valuation"}:
            latest = self.quote_repo.latest_for_asset(asset.id)
            if latest is None:
                if rule.rule_type == "incomplete_valuation":
                    dedupe = f"{asset.id}:{rule.id}:incomplete:no_quote"
                    return self._create_event(rule=rule, asset=asset, dedupe_key=dedupe, title=f"{asset.display_name} valuation incomplete", message="Valuation is incomplete because no quote is available.")
                return False

        if rule.rule_type == "price_up_pct":
            history = self.quote_repo.recent_for_asset(asset.id, limit=2)
            if len(history) < 2:
                return False
            latest, previous = history[0], history[1]
            change_pct = ((Decimal(latest.price) - Decimal(previous.price)) / Decimal(previous.price)) * Decimal("100")
            threshold = self._parse_threshold(rule, Decimal("2"))
            if change_pct >= threshold:
                dedupe = f"{asset.id}:{rule.id}:price_up:{latest.provider_timestamp_utc.isoformat()}:{threshold}"
                return self._create_event(rule=rule, asset=asset, dedupe_key=dedupe, title=f"{asset.display_name} moved up {change_pct:.2f}%", message=f"Latest stored quote increased from {previous.price} to {latest.price}.", old_state={"price": str(previous.price)}, new_state={"price": str(latest.price), "change_pct": str(change_pct)})

        if rule.rule_type == "price_down_pct":
            history = self.quote_repo.recent_for_asset(asset.id, limit=2)
            if len(history) < 2:
                return False
            latest, previous = history[0], history[1]
            change_pct = ((Decimal(previous.price) - Decimal(latest.price)) / Decimal(previous.price)) * Decimal("100")
            threshold = self._parse_threshold(rule, Decimal("2"))
            if change_pct >= threshold:
                dedupe = f"{asset.id}:{rule.id}:price_down:{latest.provider_timestamp_utc.isoformat()}:{threshold}"
                return self._create_event(rule=rule, asset=asset, dedupe_key=dedupe, title=f"{asset.display_name} moved down {change_pct:.2f}%", message=f"Latest stored quote decreased from {previous.price} to {latest.price}.", old_state={"price": str(previous.price)}, new_state={"price": str(latest.price), "change_pct": str(change_pct)})

        if rule.rule_type == "price_above":
            history = self.quote_repo.recent_for_asset(asset.id, limit=2)
            if len(history) < 2:
                return False
            latest, previous = history[0], history[1]
            threshold = self._parse_threshold(rule)
            crossed = Decimal(previous.price) <= threshold < Decimal(latest.price)
            if crossed:
                dedupe = f"{asset.id}:{rule.id}:cross_above:{threshold}:{latest.provider_timestamp_utc.isoformat()}"
                return self._create_event(rule=rule, asset=asset, dedupe_key=dedupe, title=f"{asset.display_name} crossed above {threshold}", message=f"Price crossed from {previous.price} to {latest.price}.")

        if rule.rule_type == "price_below":
            history = self.quote_repo.recent_for_asset(asset.id, limit=2)
            if len(history) < 2:
                return False
            latest, previous = history[0], history[1]
            threshold = self._parse_threshold(rule)
            crossed = Decimal(previous.price) >= threshold > Decimal(latest.price)
            if crossed:
                dedupe = f"{asset.id}:{rule.id}:cross_below:{threshold}:{latest.provider_timestamp_utc.isoformat()}"
                return self._create_event(rule=rule, asset=asset, dedupe_key=dedupe, title=f"{asset.display_name} crossed below {threshold}", message=f"Price crossed from {previous.price} to {latest.price}.")

        if rule.rule_type == "outlook_changed":
            snapshots = self.outlook_repo.get_recent_history_by_asset(asset.id, limit=2)
            if len(snapshots) >= 2 and snapshots[0].short_term_outlook != snapshots[1].short_term_outlook:
                dedupe = f"{asset.id}:{rule.id}:outlook:{snapshots[1].short_term_outlook}->{snapshots[0].short_term_outlook}:{snapshots[0].timestamp_utc.isoformat()}"
                return self._create_event(rule=rule, asset=asset, dedupe_key=dedupe, title=f"{asset.display_name} outlook changed", message=f"Outlook changed from {snapshots[1].short_term_outlook} to {snapshots[0].short_term_outlook}.")

        if rule.rule_type == "action_changed":
            snapshots = self.action_repo.get_recent_history_by_asset(asset.id, limit=2)
            if len(snapshots) >= 2 and snapshots[0].action_label != snapshots[1].action_label:
                dedupe = f"{asset.id}:{rule.id}:action:{snapshots[1].action_label}->{snapshots[0].action_label}:{snapshots[0].timestamp_utc.isoformat()}"
                return self._create_event(rule=rule, asset=asset, dedupe_key=dedupe, title=f"{asset.display_name} action changed", message=f"Action changed from {snapshots[1].action_label} to {snapshots[0].action_label}.")

        if rule.rule_type == "quote_stale":
            latest = self.quote_repo.latest_for_asset(asset.id)
            freshness = self.valuation_service._freshness_from_timestamp(latest.provider_timestamp_utc)
            active = self.event_repo.latest_active_by_rule_asset(rule.id, asset.id)
            if freshness == "stale" and active is None:
                dedupe = f"{asset.id}:{rule.id}:quote_stale:{latest.provider_timestamp_utc.isoformat()}"
                return self._create_event(rule=rule, asset=asset, dedupe_key=dedupe, title=f"{asset.display_name} quote is stale", message="Latest quote freshness transitioned to stale.")

        if rule.rule_type == "incomplete_valuation":
            base_currency = self.settings_repo.get_first().portfolio_base_currency if self.settings_repo.get_first() else "EUR"
            valuation = self.valuation_service.value_for_asset(asset, Decimal("1"), Decimal("1"), base_currency)
            active = self.event_repo.latest_active_by_rule_asset(rule.id, asset.id)
            if not valuation.has_base_value and active is None:
                dedupe = f"{asset.id}:{rule.id}:incomplete:{valuation.valuation_warning or 'unknown'}"
                return self._create_event(rule=rule, asset=asset, dedupe_key=dedupe, title=f"{asset.display_name} valuation incomplete", message=valuation.valuation_warning or "Valuation incomplete.")

        if rule.rule_type == "maturity_soon":
            if not asset.maturity_date:
                return False
            cfg = json.loads(rule.config_json) if rule.config_json else {}
            days_threshold = int(cfg.get("days", settings.default_maturity_soon_days))
            days_left = (asset.maturity_date - datetime.utcnow().date()).days
            active = self.event_repo.latest_active_by_rule_asset(rule.id, asset.id)
            if 0 <= days_left <= days_threshold and active is None:
                dedupe = f"{asset.id}:{rule.id}:maturity:{asset.maturity_date.isoformat()}:{days_threshold}"
                return self._create_event(rule=rule, asset=asset, dedupe_key=dedupe, title=f"{asset.display_name} matures soon", message=f"Maturity date is {asset.maturity_date} ({days_left} days left).")
        return False

    def _resolve_if_needed(self, rule: AlertRule, asset: Asset, settings: AppSetting) -> bool:
        active = self.event_repo.latest_active_by_rule_asset(rule.id, asset.id)
        if active is None:
            return False
        should_resolve = False
        if rule.rule_type == "quote_stale":
            latest = self.quote_repo.latest_for_asset(asset.id)
            should_resolve = latest is not None and self.valuation_service._freshness_from_timestamp(latest.provider_timestamp_utc) != "stale"
        elif rule.rule_type == "incomplete_valuation":
            base_currency = self.settings_repo.get_first().portfolio_base_currency if self.settings_repo.get_first() else "EUR"
            valuation = self.valuation_service.value_for_asset(asset, Decimal("1"), Decimal("1"), base_currency)
            should_resolve = valuation.has_base_value
        elif rule.rule_type == "maturity_soon":
            should_resolve = asset.maturity_date is None or asset.maturity_date < datetime.utcnow().date()
        elif rule.rule_type == "price_above":
            latest = self.quote_repo.latest_for_asset(asset.id)
            threshold = self._parse_threshold(rule)
            should_resolve = latest is not None and Decimal(latest.price) <= threshold
        elif rule.rule_type == "price_below":
            latest = self.quote_repo.latest_for_asset(asset.id)
            threshold = self._parse_threshold(rule)
            should_resolve = latest is not None and Decimal(latest.price) >= threshold
        if should_resolve:
            active.is_active = False
            active.resolved_at_utc = datetime.utcnow()
            self.db.flush()
            return True
        return False

    def unread_count(self) -> int:
        return self.event_repo.unread_count()

    def active_count(self) -> int:
        return self.event_repo.active_count()
