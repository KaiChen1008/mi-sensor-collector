from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.alert_rule import AlertLog, AlertRule
from app.schemas.alert_rule import AlertLogOut, AlertRuleCreate, AlertRuleOut, AlertRuleUpdate
from app.services.notifiers import NOTIFIERS

router = APIRouter()


@router.get("", response_model=list[AlertRuleOut])
async def list_rules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AlertRule).order_by(AlertRule.created_at))
    return result.scalars().all()


@router.post("", response_model=AlertRuleOut, status_code=status.HTTP_201_CREATED)
async def create_rule(body: AlertRuleCreate, db: AsyncSession = Depends(get_db)):
    rule = AlertRule(**body.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.get("/logs", response_model=list[AlertLogOut])
async def list_logs(
    rule_id: int | None = Query(None),
    limit: int = Query(50, le=500),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AlertLog).order_by(AlertLog.triggered_at.desc()).limit(limit)
    if rule_id:
        stmt = stmt.where(AlertLog.rule_id == rule_id)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{rule_id}", response_model=AlertRuleOut)
async def get_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    rule = await db.get(AlertRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.patch("/{rule_id}", response_model=AlertRuleOut)
async def update_rule(rule_id: int, body: AlertRuleUpdate, db: AsyncSession = Depends(get_db)):
    rule = await db.get(AlertRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(rule, field, value)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    rule = await db.get(AlertRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    await db.delete(rule)
    await db.commit()


@router.post("/{rule_id}/test")
async def test_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    """Send a test notification for the given rule."""
    rule = await db.get(AlertRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    notifier = NOTIFIERS.get(rule.channel)
    if not notifier:
        raise HTTPException(status_code=400, detail=f"Unknown channel: {rule.channel}")

    try:
        await notifier.send(
            rule.channel_target,
            f"[Test] {rule.name}",
            f"This is a test notification for rule '{rule.name}'.\n"
            f"Condition: {rule.metric} {rule.operator} {rule.threshold}",
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return {"status": "sent"}
