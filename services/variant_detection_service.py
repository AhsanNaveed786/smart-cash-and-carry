import re
from collections import defaultdict
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from models import ProductImportRow
from services.excel_price_service import clean_product_name

VARIANT_PATTERN = re.compile(
    r'\b(?:'
    r'(?:\d+(?:\.\d+)?(?:x\d+)?(?:-\d+)?)\s*'
    r'(?:ml|l|ltr|litre|liter|g|gm|gram|grams|kg|kilogram|'
    r'oz|lb|pcs?|pieces?|pack|rolls?|sheets?|capsules?|tablets?|'
    r'sachets?|strips?|units?|inch|inches|cm|m|meter|meters|'
    r'mm|v|w|watt|watts)'
    r'|'
    r'small|medium|large|extra\s*large|mini|jumbo|xl|xxl'
    r'|'
    r'red|blue|green|yellow|black|white|pink|purple|orange|brown|grey|silver|gold'
    r'|'
    r'pack\s*of\s*\d+'
    r')\b',
    re.IGNORECASE
)


def extract_base_name_and_size(name: str) -> tuple[str, str | None]:
    """
    Extract the base product name and size label from a product name.
    'Lipton Tea 200g' → ('Lipton Tea', '200g')
    'Normal Product' → ('Normal Product', None)
    'Nestle Milk 1.5 Liter' → ('Nestle Milk', '1.5 Liter')
    'T-Shirt Black XL' → ('T-Shirt', 'Black XL')
    """
    if not name:
        return (name, None)

    cleaned = clean_product_name(name)
    if not cleaned:
        return (name, None)

    matches = list(VARIANT_PATTERN.finditer(cleaned))
    if not matches:
        return (cleaned, None)

    split_index = -1
    for m in matches:
        if m.start() > 0:
            base_cand = cleaned[:m.start()].strip()
            base_cand = re.sub(r'[\s\-_/:]+$', '', base_cand).strip()
            if base_cand:
                split_index = m.start()
                break

    if split_index == -1:
        return (cleaned, None)

    base_name = cleaned[:split_index].strip()
    base_name = re.sub(r'[\s\-_/:]+$', '', base_name).strip()
    size_label = cleaned[split_index:].strip()

    return (base_name, size_label)


def detect_variant_groups(
    rows: list[dict],  # Each dict has 'id', 'item_name', 'uploaded_price'
) -> dict[str, list[dict]]:
    """
    Given a list of import rows, detect potential variant groups.
    Returns a dict keyed by variant_group_key (lowered base name),
    where each value is a list of rows that share the same base name
    but have different sizes.
    
    Only returns groups with 2+ members.
    """
    groups = defaultdict(list)
    
    for row in rows:
        cleaned_name = row.get('item_name', '') or ''
        base_name, size_label = extract_base_name_and_size(cleaned_name)
        
        if size_label:
            group_key = base_name.strip().lower()
            groups[group_key].append({
                'row_id': row['id'],
                'item_name': cleaned_name,
                'base_name': base_name,
                'size_label': size_label,
                'uploaded_price': row.get('uploaded_price'),
            })
    
    # Only keep groups with 2+ members (actual variant groups)
    return {
        key: members
        for key, members in groups.items()
        if len(members) >= 2
    }


def apply_variant_detection_to_batch(
    db: Session,
    batch_id: int,
) -> dict:
    """
    Detect variant groups in a batch and update rows with group info.
    Called during import preview creation.
    Returns summary of detected groups.
    """
    # Get all valid rows from the batch
    rows = list(
        db.scalars(
            select(ProductImportRow)
            .where(
                ProductImportRow.batch_id == batch_id,
                ProductImportRow.item_name.isnot(None),
                ProductImportRow.status.in_({'pending_category', 'ready'}),
            )
            .order_by(ProductImportRow.excel_row_number)
        ).all()
    )
    
    if not rows:
        return {'variant_groups_detected': 0, 'variant_rows': 0}
    
    row_dicts = [
        {'id': row.id, 'item_name': row.item_name, 'uploaded_price': row.uploaded_price}
        for row in rows
    ]
    
    groups = detect_variant_groups(row_dicts)
    
    if not groups:
        return {'variant_groups_detected': 0, 'variant_rows': 0}
    
    # Build lookup of row_id -> (group_key, size_label)
    row_updates = {}
    for group_key, members in groups.items():
        for member in members:
            row_updates[member['row_id']] = {
                'variant_group_key': group_key,
                'variant_size_label': member['size_label'],
            }
    
    # Bulk update rows
    for row in rows:
        if row.id in row_updates:
            row.variant_group_key = row_updates[row.id]['variant_group_key']
            row.variant_size_label = row_updates[row.id]['variant_size_label']
    
    db.flush()
    
    total_variant_rows = sum(len(members) for members in groups.values())
    
    return {
        'variant_groups_detected': len(groups),
        'variant_rows': total_variant_rows,
    }


def get_variant_groups(
    db: Session,
    batch_id: int,
) -> list[dict]:
    """
    Get all detected variant groups for a batch.
    Returns list of groups, each with their member rows.
    """
    rows = list(
        db.scalars(
            select(ProductImportRow)
            .where(
                ProductImportRow.batch_id == batch_id,
                ProductImportRow.variant_group_key.isnot(None),
            )
            .order_by(
                ProductImportRow.variant_group_key,
                ProductImportRow.uploaded_price,
            )
        ).all()
    )

    if not rows:
        # Check if there are active rows that need detection run
        has_pending = db.scalar(
            select(func.count(ProductImportRow.id)).where(
                ProductImportRow.batch_id == batch_id,
                ProductImportRow.item_name.isnot(None),
            )
        )
        if has_pending and has_pending > 0:
            apply_variant_detection_to_batch(db=db, batch_id=batch_id)
            db.commit()

            rows = list(
                db.scalars(
                    select(ProductImportRow)
                    .where(
                        ProductImportRow.batch_id == batch_id,
                        ProductImportRow.variant_group_key.isnot(None),
                    )
                    .order_by(
                        ProductImportRow.variant_group_key,
                        ProductImportRow.uploaded_price,
                    )
                ).all()
            )

    groups = defaultdict(list)
    for row in rows:
        groups[row.variant_group_key].append(row)
    
    result = []
    for group_key, members in groups.items():
        # Sort by price — lowest first (likely the base/smallest variant)
        members.sort(key=lambda r: r.uploaded_price or 0)
        
        # Master is the one with lowest price
        master_row = members[0]
        
        result.append({
            'group_key': group_key,
            'base_name': extract_base_name_and_size(master_row.item_name or '')[0],
            'member_count': len(members),
            'is_merged': any(m.merge_as_variant for m in members),
            'master_row_id': master_row.id if any(m.merge_as_variant for m in members) else None,
            'members': [
                {
                    'row_id': m.id,
                    'item_name': m.item_name,
                    'size_label': m.variant_size_label,
                    'uploaded_price': float(m.uploaded_price) if m.uploaded_price else None,
                    'merge_as_variant': m.merge_as_variant,
                    'is_master': m.id == master_row.id,
                }
                for m in members
            ],
        })
    
    return result


def merge_variant_group(
    db: Session,
    batch_id: int,
    group_key: str,
) -> dict:
    """
    Mark a variant group for merging. The lowest-priced row becomes master.
    """
    clean_key = group_key.strip().lower()
    rows = list(
        db.scalars(
            select(ProductImportRow)
            .where(
                ProductImportRow.batch_id == batch_id,
                func.lower(ProductImportRow.variant_group_key) == clean_key,
            )
            .order_by(ProductImportRow.uploaded_price)
        ).all()
    )

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Variant group not found.',
        )

    if len(rows) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Variant group has fewer than 2 members.',
        )

    master_row = rows[0]  # lowest price = master

    for row in rows:
        row.merge_as_variant = True
        row.variant_master_row_id = master_row.id

    db.commit()

    return {
        'group_key': group_key,
        'merged': True,
        'master_row_id': master_row.id,
        'member_count': len(rows),
    }


def unmerge_variant_group(
    db: Session,
    batch_id: int,
    group_key: str,
) -> dict:
    """
    Unmark a variant group — all rows will be imported as separate products.
    """
    clean_key = group_key.strip().lower()
    rows = list(
        db.scalars(
            select(ProductImportRow)
            .where(
                ProductImportRow.batch_id == batch_id,
                func.lower(ProductImportRow.variant_group_key) == clean_key,
            )
        ).all()
    )

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Variant group not found.',
        )

    for row in rows:
        row.merge_as_variant = False
        row.variant_master_row_id = None

    db.commit()

    return {
        'group_key': group_key,
        'merged': False,
        'member_count': len(rows),
    }


def merge_all_variant_groups(
    db: Session,
    batch_id: int,
) -> dict:
    """
    High-speed 1-click merge of ALL detected variant groups in a batch.
    """
    rows = list(
        db.scalars(
            select(ProductImportRow)
            .where(
                ProductImportRow.batch_id == batch_id,
                ProductImportRow.variant_group_key.isnot(None),
            )
            .order_by(
                ProductImportRow.variant_group_key,
                ProductImportRow.uploaded_price,
            )
        ).all()
    )

    if not rows:
        return {'batch_id': batch_id, 'merged_groups': 0, 'merged_rows': 0}

    groups = defaultdict(list)
    for row in rows:
        groups[row.variant_group_key.strip().lower()].append(row)

    merged_groups_count = 0
    merged_rows_count = 0

    for group_key, members in groups.items():
        if len(members) < 2:
            continue
        members.sort(key=lambda r: r.uploaded_price or 0)
        master_row = members[0]
        for row in members:
            row.merge_as_variant = True
            row.variant_master_row_id = master_row.id
        merged_groups_count += 1
        merged_rows_count += len(members)

    db.commit()

    return {
        'batch_id': batch_id,
        'merged_groups': merged_groups_count,
        'merged_rows': merged_rows_count,
    }


def unmerge_all_variant_groups(
    db: Session,
    batch_id: int,
) -> dict:
    """
    High-speed 1-click unmerge of ALL variant groups in a batch.
    """
    db.execute(
        update(ProductImportRow)
        .where(
            ProductImportRow.batch_id == batch_id,
            ProductImportRow.variant_group_key.isnot(None),
        )
        .values(
            merge_as_variant=False,
            variant_master_row_id=None,
        )
    )
    db.commit()

    return {
        'batch_id': batch_id,
        'unmerged': True,
    }
