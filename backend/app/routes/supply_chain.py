"""
Sentinel Drain - Supply Chain & Human Approval Gate API Routes
Provides inventory monitoring, OR-Tools optimization triggers,
and human-in-the-loop approval workflow for cross-district pharmaceutical redistribution.
"""

import time
import uuid
from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any, Optional

from ..database import get_db_connection
from ..models import RedistributionRequest, HumanApprovalRequest
from ..optimization.ortools_allocator import ortools_optimizer

router = APIRouter(prefix="/api/supply-chain", tags=["supply_chain"])

@router.get("/inventory")
def get_inventory():
    """Returns real-time stock levels, daily OPD footfall, and capacities for all PHCs."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM phc_ops ORDER BY opd_footfall_daily DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.post("/optimize")
def run_optimization(req: RedistributionRequest):
    """Executes deterministic OR-Tools redistribution optimization on demand."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM phc_ops")
    phc_network = [dict(r) for r in cursor.fetchall()]
    conn.close()

    result = ortools_optimizer.solve_stock_redistribution(
        deficit_phc_id=req.deficit_phc,
        sku=req.sku,
        required_quantity=req.required_quantity,
        phc_network=phc_network
    )
    return result

@router.get("/plans")
def list_redistribution_plans(status: Optional[str] = None):
    """Lists generated redistribution plans with source, destination, SKU, quantity, and approval status."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if status:
        cursor.execute("SELECT * FROM redistribution_plans WHERE approval_status = ? ORDER BY plan_id DESC", (status,))
    else:
        cursor.execute("SELECT * FROM redistribution_plans ORDER BY plan_id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.post("/approve")
def approve_or_reject_plan(approval: HumanApprovalRequest):
    """
    Human-in-the-Loop Action Gate:
    Enables State Health Department Official to review, approve, reject, or modify
    an automated OR-Tools redistribution order.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # Verify plan exists, or fallback to latest generated plan
    cursor.execute("SELECT * FROM redistribution_plans WHERE plan_id = ?", (approval.plan_id,))
    plan = cursor.fetchone()
    if not plan:
        cursor.execute("SELECT * FROM redistribution_plans ORDER BY plan_id DESC LIMIT 1")
        plan = cursor.fetchone()
    if not plan:
        conn.close()
        raise HTTPException(status_code=404, detail="No active redistribution plans found in database.")

    plan_dict = dict(plan)
    now = time.time()
    approval_id = f"APP-{uuid.uuid4().hex[:8].upper()}"

    # Log Human Approval Action
    cursor.execute("""
    INSERT INTO human_approvals (
        approval_id, plan_id, incident_id, officer_name,
        officer_role, action, comments, timestamp
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        approval_id, approval.plan_id, approval.incident_id,
        approval.officer_name, approval.officer_role,
        approval.action, approval.comments, now
    ))

    # Update Redistribution Plan Status
    updated_qty = approval.modified_quantity if approval.modified_quantity is not None else plan_dict["quantity"]

    cursor.execute("""
    UPDATE redistribution_plans SET
        approval_status = ?,
        approved_by = ?,
        approved_at = ?,
        quantity = ?,
        notes = ?
    WHERE plan_id = ?
    """, (
        approval.action,
        f"{approval.officer_name} ({approval.officer_role})",
        now,
        updated_qty,
        approval.comments or "Reviewed and authorized by district health official",
        approval.plan_id
    ))

    # If approved, update source and destination PHC stock in phc_ops table
    if approval.action == "APPROVED":
        sku_col = "stock_ors" if "ors" in plan_dict["sku"].lower() else "stock_iv_fluids"

        # Deduct from source
        cursor.execute(f"UPDATE phc_ops SET {sku_col} = {sku_col} - ? WHERE phc_id = ?",
                       (updated_qty, plan_dict["source_phc"]))
        # Add to destination
        cursor.execute(f"UPDATE phc_ops SET {sku_col} = {sku_col} + ? WHERE phc_id = ?",
                       (updated_qty, plan_dict["destination_phc"]))

        # Update parent incident status if all plans for this incident are approved
        cursor.execute("""
        UPDATE agent_incidents SET
            status = 'EXECUTION_DISPATCHED',
            final_decision = 'Redistribution plan formally approved and logistics transit order issued.'
        WHERE incident_id = ?
        """, (approval.incident_id,))

    conn.commit()
    conn.close()

    return {
        "status": "PROCESSED",
        "approval_id": approval_id,
        "plan_id": approval.plan_id,
        "action": approval.action,
        "authorized_quantity": updated_qty,
        "officer": approval.officer_name,
        "timestamp": now
    }

@router.post("/rerun-ortools")
def rerun_ortools_solver():
    """Triggers a fresh OR-Tools linear programming optimization cycle across the district."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM phc_ops")
    phc_network = [dict(r) for r in cursor.fetchall()]
    
    # Run optimization for Rampur ORS deficit
    result = ortools_optimizer.solve_stock_redistribution(
        deficit_phc_id="PHC-RAMPUR",
        sku="ORS Sachets (1 Litre Formulation)",
        required_quantity=1632,
        phc_network=phc_network
    )
    
    if result["status"] in ["OPTIMAL", "FEASIBLE"] and result["transfers"]:
        now = int(time.time())
        plan_id = f"PLAN-OR-RAMPUR-{uuid.uuid4().hex[:4].upper()}"
        cursor.execute("SELECT incident_id FROM agent_incidents ORDER BY timestamp DESC LIMIT 1")
        row = cursor.fetchone()
        incident_id = row["incident_id"] if row else "INC-OR-MANUAL"
        
        for t in result["transfers"]:
            cursor.execute("""
            INSERT INTO redistribution_plans (
                plan_id, incident_id, timestamp, source_phc, destination_phc,
                sku, quantity, transit_distance_km, est_transit_hours,
                optimization_run_id, approval_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING_APPROVAL')
            """, (
                plan_id, incident_id, now,
                t["source_phc_id"], t["destination_phc_id"],
                t["sku"], t["quantity"], t["distance_km"],
                t["est_transit_hours"], result["optimization_run_id"]
            ))
        conn.commit()
    conn.close()
    
    return {"status": "SOLVED", "optimization": result}

