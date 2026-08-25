import re
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, insert, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import Category, Product, ProductImportBatch, ProductImportRow, ProductVariant
from services.category_service import generate_unique_slug
from services.excel_price_service import clean_product_name
from services.product_service import bulk_generate_product_slugs
from services.variant_detection_service import extract_base_name_and_size


CHUNK_SIZE = 5000


def _resolve_new_categories(
    db: Session,
    selected_rows: list[ProductImportRow],
) -> list[str]:
    requested_names: dict[str, str] = {}
    for row in selected_rows:
        if row.confirmed_category_name:
            clean_name = " ".join(
                row.confirmed_category_name.strip().split()
            )
            requested_names.setdefault(clean_name.casefold(), clean_name)

    if not requested_names:
        return []

    categories_by_name = {
        category.name.casefold(): category
        for category in db.scalars(
            select(Category).where(
                func.lower(Category.name).in_(
                    [name.lower() for name in requested_names.values()]
                )
            )
        ).all()
    }
    next_order = (
        db.scalar(select(func.max(Category.display_order))) or 0
    ) + 1
    created_names: list[str] = []

    for key, requested_name in requested_names.items():
        category = categories_by_name.get(key)
        if category is None:
            category = Category(
                name=requested_name,
                slug=generate_unique_slug(db=db, name=requested_name),
                description="Created from a reviewed product import.",
                image_url=None,
                display_order=next_order,
                is_active=True,
            )
            next_order += 1
            db.add(category)
            db.flush()
            categories_by_name[key] = category
            created_names.append(category.name)
        elif category.slug == "deals":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Deals cannot be used as a product category.",
            )
        elif not category.is_active:
            category.is_active = True

    for row in selected_rows:
        if row.confirmed_category_name:
            key = " ".join(
                row.confirmed_category_name.strip().split()
            ).casefold()
            row.confirmed_category_id = categories_by_name[key].id

    return created_names


def apply_product_import(
    db: Session,
    batch_id: int,
    commit_changes: bool = True,
    fallback_category_id: int | None = None,
    auto_assign_default: bool = False,
) -> dict:
    try:
        batch = db.scalar(
            select(ProductImportBatch)
            .where(ProductImportBatch.id == batch_id)
            .with_for_update()
        )
        if not batch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product import batch not found.",
            )
        if batch.status == "applied":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This product import has already been applied.",
            )
        if batch.status in {"cancelled", "failed"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This product import cannot be applied.",
            )

        # If fallback category or auto-assign is requested, resolve fallback category
        resolved_fallback_id = fallback_category_id
        if auto_assign_default and resolved_fallback_id is None:
            first_active_cat = db.scalar(
                select(Category.id)
                .where(Category.is_active.is_(True), Category.slug != "deals")
                .order_by(Category.display_order, Category.id)
            )
            if not first_active_cat:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No active product category exists to assign as default.",
                )
            resolved_fallback_id = first_active_cat

        if resolved_fallback_id is not None:
            # Assign fallback category to any selected row missing category
            db.execute(
                update(ProductImportRow)
                .where(
                    ProductImportRow.batch_id == batch_id,
                    ProductImportRow.apply_selected.is_(True),
                    or_(
                        ProductImportRow.status == "pending_category",
                        (
                            (ProductImportRow.status == "ready")
                            & ProductImportRow.confirmed_category_id.is_(None)
                            & ProductImportRow.confirmed_category_name.is_(None)
                        ),
                    ),
                )
                .values(
                    confirmed_category_id=resolved_fallback_id,
                    confirmed_category_name=None,
                    status="ready",
                    category_source="manual",
                )
            )
            db.flush()

        selected_pending = db.scalar(
            select(func.count(ProductImportRow.id)).where(
                ProductImportRow.batch_id == batch_id,
                ProductImportRow.apply_selected.is_(True),
                or_(
                    ProductImportRow.status == "pending_category",
                    (
                        (ProductImportRow.status == "ready")
                        & ProductImportRow.confirmed_category_id.is_(None)
                        & ProductImportRow.confirmed_category_name.is_(None)
                    ),
                ),
            )
        ) or 0
        if selected_pending:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": (
                        "Every selected product must have a reviewed "
                        "category before final confirmation. You can use 'Quick Auto-Categorize' "
                        "or assign a default category to remaining rows."
                    ),
                    "remaining_selected_rows": selected_pending,
                },
            )

        selected_rows = list(
            db.scalars(
                select(ProductImportRow)
                .where(
                    ProductImportRow.batch_id == batch_id,
                    ProductImportRow.status == "ready",
                    ProductImportRow.apply_selected.is_(True),
                )
                .order_by(ProductImportRow.excel_row_number)
                .with_for_update()
            ).all()
        )

        if not selected_rows:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No reviewable products are selected for import.",
            )

        incomplete_rows = [
            row.excel_row_number
            for row in selected_rows
            if (
                not row.barcode
                or not row.item_name
                or row.uploaded_price is None
                or (
                    row.confirmed_category_id is None
                    and not row.confirmed_category_name
                )
            )
        ]
        if incomplete_rows:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Some selected rows contain incomplete data.",
                    "excel_rows": incomplete_rows[:50],
                },
            )

        selected_barcodes = [row.barcode for row in selected_rows]
        if len(selected_barcodes) != len(set(selected_barcodes)):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Selected rows contain duplicate barcodes.",
            )
        if selected_barcodes:
            # Check existing barcodes in chunks for large lists
            for i in range(0, len(selected_barcodes), CHUNK_SIZE):
                chunk_barcodes = selected_barcodes[i : i + CHUNK_SIZE]
                existing_products = list(
                    db.scalars(
                        select(Product)
                        .where(Product.barcode.in_(chunk_barcodes))
                        .with_for_update()
                    ).all()
                )
                existing_variants = list(
                    db.scalars(
                        select(ProductVariant)
                        .where(ProductVariant.barcode.in_(chunk_barcodes))
                        .with_for_update()
                    ).all()
                )
                if existing_products or existing_variants:
                    collision_barcodes = [
                        p.barcode for p in existing_products if p.barcode
                    ] + [
                        v.barcode for v in existing_variants if v.barcode
                    ]
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail={
                            "message": (
                                "Some products were added after preview. "
                                "Create a fresh preview."
                            ),
                            "existing_barcodes": collision_barcodes[:50],
                        },
                    )

        created_categories = _resolve_new_categories(db, selected_rows)
        category_ids = {
            row.confirmed_category_id
            for row in selected_rows
            if row.confirmed_category_id is not None
        }
        valid_category_ids = set()
        if category_ids:
            valid_category_ids = set(
                db.scalars(
                    select(Category.id).where(
                        Category.id.in_(category_ids),
                        Category.is_active.is_(True),
                        Category.slug != "deals",
                    )
                ).all()
            )
        if category_ids - valid_category_ids:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A confirmed category is missing or inactive.",
            )

        # Partition rows into merged variant groups and standalone products
        selected_by_id = {row.id: row for row in selected_rows}
        master_to_members: dict[int, list[ProductImportRow]] = defaultdict(list)
        non_master_merged_row_ids: set[int] = set()

        for row in selected_rows:
            if row.merge_as_variant and row.variant_master_row_id:
                master_id = row.variant_master_row_id
                if master_id in selected_by_id and master_id != row.id:
                    master_to_members[master_id].append(row)
                    non_master_merged_row_ids.add(row.id)

        product_rows_to_create = [
            row for row in selected_rows if row.id not in non_master_merged_row_ids
        ]

        product_names = []
        for row in product_rows_to_create:
            if row.id in master_to_members:
                base_name, _ = extract_base_name_and_size(row.item_name or "")
                product_names.append(base_name or clean_product_name(row.item_name))
            else:
                product_names.append(clean_product_name(row.item_name))

        existing_slugs = set(db.scalars(select(Product.slug)).all())
        slugs = bulk_generate_product_slugs(product_names, existing_slugs)

        now_dt = datetime.now(timezone.utc)
        master_rows_to_create = [r for r in product_rows_to_create if r.id in master_to_members]
        standalone_rows_to_create = [r for r in product_rows_to_create if r.id not in master_to_members]

        # Bulk insert standalone products
        standalone_records = []
        for row in standalone_rows_to_create:
            idx = product_rows_to_create.index(row)
            standalone_records.append({
                "barcode": row.barcode.strip(),
                "name": product_names[idx],
                "slug": slugs[idx],
                "description": None,
                "unit_size": None,
                "master_price": row.uploaded_price,
                "image_url": None,
                "category_id": row.confirmed_category_id,
                "is_active": True,
                "created_at": now_dt,
                "updated_at": now_dt,
            })

        for i in range(0, len(standalone_records), CHUNK_SIZE):
            chunk = standalone_records[i : i + CHUNK_SIZE]
            db.execute(insert(Product).values(chunk))
            db.flush()

        # Insert master products and their variant options
        created_variants_count = 0
        if master_rows_to_create:
            existing_skus = set(db.scalars(select(ProductVariant.sku)).all())
            for row in master_rows_to_create:
                idx = product_rows_to_create.index(row)
                prod = Product(
                    barcode=row.barcode.strip(),
                    name=product_names[idx],
                    slug=slugs[idx],
                    description=None,
                    unit_size=None,
                    master_price=row.uploaded_price,
                    image_url=None,
                    category_id=row.confirmed_category_id,
                    is_active=True,
                    created_at=now_dt,
                    updated_at=now_dt,
                )
                db.add(prod)
                db.flush()

                # Base variant for master product
                base_name = row.variant_size_label or "Standard"
                base_sku_raw = re.sub(r'[^A-Za-z0-9_-]', '', row.barcode or prod.slug).upper() or f"PROD{prod.id}"
                base_sku = f"{base_sku_raw}-BASE"[:100]
                counter = 1
                while base_sku in existing_skus:
                    base_sku = f"{base_sku_raw}-BASE-{counter}"[:100]
                    counter += 1
                existing_skus.add(base_sku)

                base_variant = ProductVariant(
                    product_id=prod.id,
                    name=base_name,
                    sku=base_sku,
                    barcode=row.barcode.strip() if row.barcode else None,
                    attributes={"size": row.variant_size_label} if row.variant_size_label else {},
                    price_adjustment=Decimal("0.00"),
                    display_order=0,
                    is_default=True,
                    is_active=True,
                    created_at=now_dt,
                    updated_at=now_dt,
                )
                db.add(base_variant)
                created_variants_count += 1

                # Member variants
                members = master_to_members[row.id]
                for v_idx, member in enumerate(members, start=1):
                    member_size = member.variant_size_label or member.item_name or f"Option {v_idx}"
                    member_sku_raw = re.sub(r'[^A-Za-z0-9_-]', '', member.barcode or f"{prod.slug}-{member_size}").upper() or f"VAR{v_idx}"
                    member_sku = f"{member_sku_raw}-VAR"[:100]
                    counter = 1
                    while member_sku in existing_skus:
                        member_sku = f"{member_sku_raw}-VAR-{counter}"[:100]
                        counter += 1
                    existing_skus.add(member_sku)

                    master_price = Decimal(str(row.uploaded_price or 0))
                    member_price = Decimal(str(member.uploaded_price or 0))
                    price_diff = member_price - master_price

                    member_variant = ProductVariant(
                        product_id=prod.id,
                        name=member_size,
                        sku=member_sku,
                        barcode=member.barcode.strip() if member.barcode else None,
                        attributes={"size": member.variant_size_label} if member.variant_size_label else {},
                        price_adjustment=price_diff,
                        display_order=v_idx,
                        is_default=False,
                        is_active=True,
                        created_at=now_dt,
                        updated_at=now_dt,
                    )
                    db.add(member_variant)
                    created_variants_count += 1

            db.flush()

        # Chunked bulk update of applied ProductImportRow statuses
        selected_row_ids = [row.id for row in selected_rows]
        for i in range(0, len(selected_row_ids), CHUNK_SIZE):
            chunk_ids = selected_row_ids[i : i + CHUNK_SIZE]
            db.execute(
                update(ProductImportRow)
                .where(ProductImportRow.id.in_(chunk_ids))
                .values(status="applied")
            )

        # Bulk update unselected rows to skipped
        skipped_count = db.scalar(
            select(func.count(ProductImportRow.id)).where(
                ProductImportRow.batch_id == batch_id,
                ProductImportRow.status.in_({"pending_category", "ready"}),
                ProductImportRow.apply_selected.is_(False),
            )
        ) or 0

        db.execute(
            update(ProductImportRow)
            .where(
                ProductImportRow.batch_id == batch_id,
                ProductImportRow.status.in_({"pending_category", "ready"}),
                ProductImportRow.apply_selected.is_(False),
            )
            .values(status="skipped")
        )

        batch.status = "applied"
        batch.applied_at = now_dt

        if commit_changes:
            db.commit()
        else:
            db.flush()

        return {
            "batch_id": batch.id,
            "status": batch.status,
            "created_products": len(product_rows_to_create),
            "created_variants": created_variants_count,
            "created_categories": created_categories,
            "skipped_rows": skipped_count,
            "applied_at": now_dt,
        }
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A product barcode, category or slug conflict occurred. "
                "No changes were saved."
            ),
        ) from error
    except Exception:
        db.rollback()
        raise
