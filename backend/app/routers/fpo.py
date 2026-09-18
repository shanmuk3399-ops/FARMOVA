from datetime import datetime
import json

from fastapi import APIRouter, HTTPException, Depends

from ..database import get_db
from ..security import get_current_user


router = APIRouter(prefix="/api/fpo", tags=["FPO"])


def fpo_for_user(uid):
    conn = get_db()

    row = conn.execute(
        "SELECT * FROM fpos WHERE created_by=? ORDER BY id DESC LIMIT 1",
        (uid,)
    ).fetchone()

    conn.close()

    return row


@router.post("/create")
def create_fpo(
    name: str,
    location: str = "",
    current=Depends(get_current_user)
):
    uid, role = current

    if role != "FPO":
        raise HTTPException(
            403,
            "Only FPO users can create an FPO"
        )

    if not name.strip():
        raise HTTPException(
            400,
            "FPO name is required"
        )

    conn = get_db()

    cur = conn.execute(
        """
        INSERT INTO fpos
        (name, location, created_by, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            name.strip(),
            location.strip(),
            uid,
            datetime.utcnow().isoformat()
        )
    )

    conn.execute(
        "UPDATE users SET fpo_id=? WHERE id=?",
        (
            cur.lastrowid,
            uid
        )
    )

    conn.commit()

    fid = cur.lastrowid

    conn.close()

    return {
        "message": "FPO created successfully",
        "fpo_id": fid
    }


@router.get("/my")
def my_fpo(
    current=Depends(get_current_user)
):
    uid, role = current

    if role != "FPO":
        raise HTTPException(
            403,
            "Only FPO users can access this page"
        )

    row = fpo_for_user(uid)

    return dict(row) if row else {
        "id": None,
        "name": "",
        "location": "",
        "created_by": uid
    }


# ---------------------------------------------------------
# GET ALL REGISTERED FARMERS
# ---------------------------------------------------------
@router.get("/farmers")
def all_farmers(
    current=Depends(get_current_user)
):
    uid, role = current

    if role != "FPO":
        raise HTTPException(
            403,
            "Only FPO users can view farmers"
        )

    conn = get_db()

    rows = conn.execute(
        """
        SELECT
            id,
            name,
            phone,
            location,
            language,
            fpo_id AS member_fpo_id
        FROM users
        WHERE role='FARMER'
        ORDER BY id ASC
        """
    ).fetchall()

    conn.close()

    return [dict(r) for r in rows]


# ---------------------------------------------------------
# ADD FARMER TO FPO
# ---------------------------------------------------------
@router.post("/add-farmer")
def add_farmer(
    fpo_id: int,
    farmer_id: int,
    current=Depends(get_current_user)
):
    uid, role = current

    if role != "FPO":
        raise HTTPException(
            403,
            "Only FPO users can add farmers"
        )

    conn = get_db()

    # Check farmer
    farmer = conn.execute(
        """
        SELECT
            id,
            role,
            name,
            phone,
            location,
            language,
            fpo_id
        FROM users
        WHERE id=?
        """,
        (farmer_id,)
    ).fetchone()

    # Check that this FPO belongs to the logged-in FPO user
    fpo = conn.execute(
        """
        SELECT id
        FROM fpos
        WHERE id=? AND created_by=?
        """,
        (
            fpo_id,
            uid
        )
    ).fetchone()

    if farmer is None or farmer["role"] != "FARMER":
        conn.close()

        raise HTTPException(
            404,
            "Farmer not found"
        )

    if fpo is None:
        conn.close()

        raise HTTPException(
            403,
            "FPO access denied"
        )

    # Already belongs to this FPO
    if farmer["fpo_id"] is not None:

        if int(farmer["fpo_id"]) == int(fpo_id):
            conn.close()

            return {
                "message": "Farmer is already a member of this FPO",
                "fpo_id": fpo_id,
                "farmer_id": farmer_id,
                "farmer_name": farmer["name"]
            }

        conn.close()

        raise HTTPException(
            400,
            "Farmer already belongs to another FPO"
        )

    # Add farmer
    conn.execute(
        """
        INSERT INTO fpo_members
        (fpo_id, farmer_id, joined_at)
        VALUES (?, ?, ?)
        """,
        (
            fpo_id,
            farmer_id,
            datetime.utcnow().isoformat()
        )
    )

    # Also store FPO ID in users table
    conn.execute(
        """
        UPDATE users
        SET fpo_id=?
        WHERE id=?
        """,
        (
            fpo_id,
            farmer_id
        )
    )

    conn.commit()

    conn.close()

    return {
        "message": "Farmer added to FPO",
        "fpo_id": fpo_id,
        "farmer_id": farmer_id,
        "farmer_name": farmer["name"]
    }


# ---------------------------------------------------------
# GET FPO MEMBERS
# ---------------------------------------------------------
@router.get("/members/{fpo_id}")
def members(
    fpo_id: int
):
    conn = get_db()

    rows = conn.execute(
        """
        SELECT
            u.id,
            u.name,
            u.phone,
            u.location,
            u.language
        FROM fpo_members m
        JOIN users u
            ON u.id=m.farmer_id
        WHERE m.fpo_id=?
        ORDER BY u.name
        """,
        (fpo_id,)
    ).fetchall()

    conn.close()

    return [dict(r) for r in rows]


# ---------------------------------------------------------
# AVAILABLE MEMBER PRODUCE
# ---------------------------------------------------------
@router.get("/{fpo_id}/available-produce")
def available_produce(
    fpo_id: int
):
    conn = get_db()

    rows = conn.execute(
        """
        SELECT
            p.*,
            u.name AS farmer_name
        FROM produce p
        JOIN users u
            ON u.id=p.farmer_id
        JOIN fpo_members m
            ON m.farmer_id=p.farmer_id
        WHERE
            m.fpo_id=?
            AND p.active=1
            AND p.quantity>0
        ORDER BY
            p.crop_name,
            p.id DESC
        """,
        (fpo_id,)
    ).fetchall()

    conn.close()

    return [dict(r) for r in rows]


# ---------------------------------------------------------
# AI SUITABILITY SCORES
# ---------------------------------------------------------
@router.get("/{fpo_id}/suitability-scores")
def suitability(
    fpo_id: int
):
    conn = get_db()

    rows = conn.execute(
        """
        SELECT
            p.*,
            u.name AS farmer_name
        FROM produce p
        JOIN users u
            ON u.id=p.farmer_id
        JOIN fpo_members m
            ON m.farmer_id=p.farmer_id
        WHERE
            m.fpo_id=?
            AND p.active=1
            AND p.quantity>0
        ORDER BY
            p.id DESC
        """,
        (fpo_id,)
    ).fetchall()

    result = []

    for r in rows:

        score = 60

        quality = str(r["quality_grade"] or "").lower()

        if "premium" in quality:
            score += 20

        elif "a" in quality:
            score += 10

        if float(r["quantity"] or 0) >= 50:
            score += 10

        if float(r["expected_price"] or 0) > 0:
            score += 10

        result.append({
            "produce_id": r["id"],
            "crop_name": r["crop_name"],
            "farmer_name": r["farmer_name"],
            "quantity": r["quantity"],
            "quality_grade": r["quality_grade"],
            "score": min(score, 100)
        })

    conn.close()

    return result


# ---------------------------------------------------------
# CREATE AGGREGATION
# ---------------------------------------------------------
@router.post("/aggregation/create")
def create_aggregation(
    crop_name: str,
    required_quantity: float,
    unit: str = "Qtl",
    location: str = "",
    current=Depends(get_current_user)
):
    uid, role = current

    if role != "FPO":
        raise HTTPException(
            403,
            "Only FPO users can create aggregation batches"
        )

    if required_quantity <= 0:
        raise HTTPException(
            400,
            "Required quantity must be greater than zero"
        )

    fp = fpo_for_user(uid)

    if not fp:
        raise HTTPException(
            400,
            "Create an FPO first"
        )

    conn = get_db()

    cur = conn.execute(
        """
        INSERT INTO aggregations
        (
            fpo_id,
            crop_name,
            required_quantity,
            unit,
            location,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            fp["id"],
            crop_name.strip(),
            required_quantity,
            unit.strip(),
            location.strip(),
            datetime.utcnow().isoformat()
        )
    )

    conn.commit()

    aid = cur.lastrowid

    conn.close()

    return {
        "message": "Aggregation created successfully",
        "aggregation_id": aid,
        "fpo_id": fp["id"]
    }


# ---------------------------------------------------------
# ALL AGGREGATIONS
# ---------------------------------------------------------
@router.get("/aggregation/all")
def all_aggregations():

    conn = get_db()

    rows = conn.execute(
        """
        SELECT
            a.*,
            f.name AS fpo_name
        FROM aggregations a
        JOIN fpos f
            ON f.id=a.fpo_id
        ORDER BY
            a.created_at DESC
        """
    ).fetchall()

    conn.close()

    return [dict(r) for r in rows]


# ---------------------------------------------------------
# FPO BATCHES
# ---------------------------------------------------------
@router.get("/{fpo_id}/batches")
def fpo_batches(
    fpo_id: int
):
    conn = get_db()

    rows = conn.execute(
        """
        SELECT
            a.*,
            COUNT(ai.id) AS contributor_count
        FROM aggregations a
        LEFT JOIN aggregation_items ai
            ON ai.aggregation_id=a.id
        WHERE a.fpo_id=?
        GROUP BY a.id
        ORDER BY a.id DESC
        """,
        (fpo_id,)
    ).fetchall()

    conn.close()

    return [dict(r) for r in rows]


# ---------------------------------------------------------
# ADD FARMER PRODUCE TO AGGREGATION
# ---------------------------------------------------------
@router.post("/aggregation/add-produce")
def add_to_aggregation(
    aggregation_id: int,
    produce_id: int,
    quantity: float,
    current=Depends(get_current_user)
):
    uid, role = current

    if role != "FARMER":
        raise HTTPException(
            403,
            "Only farmers can contribute produce"
        )

    if quantity <= 0:
        raise HTTPException(
            400,
            "Quantity must be greater than zero"
        )

    conn = get_db()

    aggregation = conn.execute(
        """
        SELECT *
        FROM aggregations
        WHERE id=?
        """,
        (aggregation_id,)
    ).fetchone()

    produce = conn.execute(
        """
        SELECT *
        FROM produce
        WHERE id=?
        """,
        (produce_id,)
    ).fetchone()

    if aggregation is None:
        conn.close()

        raise HTTPException(
            404,
            "Aggregation not found"
        )

    if produce is None or produce["farmer_id"] != uid:
        conn.close()

        raise HTTPException(
            403,
            "You can contribute only your own produce"
        )

    if produce["crop_name"].lower() != aggregation["crop_name"].lower():
        conn.close()

        raise HTTPException(
            400,
            "Crop does not match aggregation"
        )

    remaining = (
        float(aggregation["required_quantity"])
        - float(aggregation["total_quantity"])
    )

    if quantity > float(produce["quantity"]):
        conn.close()

        raise HTTPException(
            400,
            "Quantity exceeds available produce"
        )

    if quantity > remaining:
        conn.close()

        raise HTTPException(
            400,
            "Quantity exceeds aggregation requirement"
        )

    conn.execute(
        """
        INSERT INTO aggregation_items
        (
            aggregation_id,
            farmer_id,
            produce_id,
            quantity,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            aggregation_id,
            uid,
            produce_id,
            quantity,
            datetime.utcnow().isoformat()
        )
    )

    new_total = (
        float(aggregation["total_quantity"])
        + quantity
    )

    new_status = (
        "COMPLETED"
        if new_total >= float(aggregation["required_quantity"])
        else "OPEN"
    )

    conn.execute(
        """
        UPDATE produce
        SET quantity=quantity-?
        WHERE id=?
        """,
        (
            quantity,
            produce_id
        )
    )

    conn.execute(
        """
        UPDATE aggregations
        SET total_quantity=?,
            status=?
        WHERE id=?
        """,
        (
            new_total,
            new_status,
            aggregation_id
        )
    )

    conn.commit()

    conn.close()

    return {
        "message": "Produce added to aggregation successfully",
        "aggregation_id": aggregation_id,
        "produce_id": produce_id,
        "quantity_added": quantity,
        "total_quantity": new_total,
        "status": new_status
    }


# ---------------------------------------------------------
# AUTO AGGREGATE
# ---------------------------------------------------------
@router.post("/{fpo_id}/aggregate")
def auto_aggregate(
    fpo_id: int,
    current=Depends(get_current_user)
):
    uid, role = current

    if role != "FPO":
        raise HTTPException(
            403,
            "Only FPO users can aggregate"
        )

    conn = get_db()

    fp = conn.execute(
        """
        SELECT id
        FROM fpos
        WHERE id=? AND created_by=?
        """,
        (
            fpo_id,
            uid
        )
    ).fetchone()

    if fp is None:
        conn.close()

        raise HTTPException(
            403,
            "FPO access denied"
        )

    batches = conn.execute(
        """
        SELECT *
        FROM aggregations
        WHERE
            fpo_id=?
            AND status='OPEN'
        ORDER BY id
        """,
        (fpo_id,)
    ).fetchall()

    results = []

    for aggregation in batches:

        remaining = (
            float(aggregation["required_quantity"])
            - float(aggregation["total_quantity"])
        )

        items = conn.execute(
            """
            SELECT
                p.*
            FROM produce p
            JOIN fpo_members m
                ON m.farmer_id=p.farmer_id
            WHERE
                m.fpo_id=?
                AND p.active=1
                AND p.quantity>0
                AND lower(p.crop_name)=lower(?)
            ORDER BY
                CASE
                    WHEN lower(p.quality_grade) LIKE '%premium%'
                    THEN 0
                    ELSE 1
                END,
                p.id
            """,
            (
                fpo_id,
                aggregation["crop_name"]
            )
        ).fetchall()

        added = 0

        for produce in items:

            if remaining <= 0:
                break

            available = float(produce["quantity"])

            q = min(
                available,
                remaining
            )

            conn.execute(
                """
                INSERT INTO aggregation_items
                (
                    aggregation_id,
                    farmer_id,
                    produce_id,
                    quantity,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    aggregation["id"],
                    produce["farmer_id"],
                    produce["id"],
                    q,
                    datetime.utcnow().isoformat()
                )
            )

            conn.execute(
                """
                UPDATE produce
                SET quantity=quantity-?
                WHERE id=?
                """,
                (
                    q,
                    produce["id"]
                )
            )

            remaining -= q
            added += q

        if added > 0:

            new_total = (
                float(aggregation["total_quantity"])
                + added
            )

            new_status = (
                "COMPLETED"
                if new_total >= float(
                    aggregation["required_quantity"]
                )
                else "OPEN"
            )

            conn.execute(
                """
                UPDATE aggregations
                SET
                    total_quantity=?,
                    status=?
                WHERE id=?
                """,
                (
                    new_total,
                    new_status,
                    aggregation["id"]
                )
            )

            results.append({
                "aggregation_id": aggregation["id"],
                "added": added,
                "total_quantity": new_total,
                "required_quantity": aggregation["required_quantity"],
                "status": new_status
            })

    conn.commit()

    conn.close()

    return {
        "message": "Aggregation run completed",
        "results": results
    }


# ---------------------------------------------------------
# BULK ORDER MATCHING
# ---------------------------------------------------------
@router.post("/{fpo_id}/match-bulk-order")
def match_bulk_order(
    fpo_id: int,
    required_quantity: float,
    crop_name: str,
    current=Depends(get_current_user)
):
    uid, role = current

    if role != "FPO":
        raise HTTPException(
            403,
            "Only FPO users can match bulk orders"
        )

    if required_quantity <= 0:
        raise HTTPException(
            400,
            "Required quantity must be greater than zero"
        )

    conn = get_db()

    fp = conn.execute(
        """
        SELECT id
        FROM fpos
        WHERE id=? AND created_by=?
        """,
        (
            fpo_id,
            uid
        )
    ).fetchone()

    if fp is None:
        conn.close()

        raise HTTPException(
            403,
            "FPO access denied"
        )

    rows = conn.execute(
        """
        SELECT
            p.id,
            p.crop_name,
            p.quantity,
            p.unit,
            p.quality_grade,
            p.expected_price,
            p.location,
            u.name AS farmer_name
        FROM produce p
        JOIN fpo_members m
            ON m.farmer_id=p.farmer_id
        JOIN users u
            ON u.id=p.farmer_id
        WHERE
            m.fpo_id=?
            AND p.active=1
            AND p.quantity>0
            AND lower(p.crop_name)=lower(?)
        ORDER BY
            CASE
                WHEN lower(p.quality_grade) LIKE '%premium%'
                THEN 0
                ELSE 1
            END,
            p.id DESC
        """,
        (
            fpo_id,
            crop_name
        )
    ).fetchall()

    remain = float(required_quantity)

    matches = []

    for row in rows:

        if remain <= 0:
            break

        q = min(
            float(row["quantity"]),
            remain
        )

        matches.append({
            **dict(row),
            "matched_quantity": q
        })

        remain -= q

    conn.close()

    return {
        "crop_name": crop_name,
        "required_quantity": required_quantity,
        "matched_quantity": (
            required_quantity - remain
        ),
        "remaining_quantity": remain,
        "fully_matched": remain <= 0,
        "matches": matches
    }


# ---------------------------------------------------------
# AGGREGATION CONTRIBUTORS
# ---------------------------------------------------------
@router.get("/aggregation/{aggregation_id}/contributors")
def contributors(
    aggregation_id: int
):
    conn = get_db()

    rows = conn.execute(
        """
        SELECT
            ai.*,
            u.name AS farmer_name,
            p.crop_name,
            p.unit,
            p.quality_grade
        FROM aggregation_items ai
        JOIN users u
            ON u.id=ai.farmer_id
        JOIN produce p
            ON p.id=ai.produce_id
        WHERE ai.aggregation_id=?
        ORDER BY ai.created_at
        """,
        (aggregation_id,)
    ).fetchall()

    conn.close()

    return {
        "aggregation_id": aggregation_id,
        "contributors": [dict(r) for r in rows]
    }


# ---------------------------------------------------------
# CREATE BULK POOL
# ---------------------------------------------------------
@router.post("/pools")
def create_pool(
    payload: dict,
    current=Depends(get_current_user)
):
    uid, role = current

    if role != "FPO":
        raise HTTPException(
            403,
            "Only FPO users can create bulk pools"
        )

    required = [
        "pool_name",
        "target_quantity",
        "target_amount",
        "selected_products"
    ]

    missing = [
        key
        for key in required
        if key not in payload
    ]

    if missing:
        raise HTTPException(
            422,
            f"Missing field: {missing[0]}"
        )

    if not payload["selected_products"]:
        raise HTTPException(
            400,
            "Select at least one product"
        )

    conn = get_db()

    fp = conn.execute(
        """
        SELECT id
        FROM fpos
        WHERE created_by=?
        ORDER BY id DESC
        LIMIT 1
        """,
        (uid,)
    ).fetchone()

    cur = conn.execute(
        """
        INSERT INTO bulk_pools
        (
            pool_name,
            target_quantity,
            target_amount,
            status,
            selected_products,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            str(payload["pool_name"]).strip(),
            float(payload["target_quantity"]),
            float(payload["target_amount"]),
            "ACTIVE",
            json.dumps(
                payload["selected_products"]
            ),
            datetime.utcnow().isoformat()
        )
    )

    conn.commit()

    pid = cur.lastrowid

    conn.close()

    return {
        "message": "Bulk pool created successfully!",
        "pool_id": pid,
        "fpo_id": fp["id"] if fp else None
    }


# ---------------------------------------------------------
# GET BULK POOLS
# ---------------------------------------------------------
@router.get("/pools")
def pools():

    conn = get_db()

    rows = conn.execute(
        """
        SELECT *
        FROM bulk_pools
        ORDER BY id DESC
        """
    ).fetchall()

    conn.close()

    result = []

    for row in rows:

        item = dict(row)

        try:
            item["selected_products"] = json.loads(
                item["selected_products"]
            )
        except Exception:
            item["selected_products"] = []

        result.append(item)

    return result