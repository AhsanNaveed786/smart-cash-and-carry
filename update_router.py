import re

file2 = 'routers/product_import_router.py'
with open(file2, 'r', encoding='utf-8') as f:
    content2 = f.read()

content2 = content2.replace('from fastapi import (', 'from fastapi import (\n    status,')
content2 = re.sub(
    r'(from schemas import \(\n.*?    ProductImportReviewSummary,\n\))',
    r'\g<1>\nfrom schemas import VariantGroupsResponse, VariantMergeResponse',
    content2,
    flags=re.DOTALL
)
content2 = re.sub(
    r'(from services.product_import_service import \(\n.*?    update_all_product_import_row_selection,\n\))',
    r'\g<1>\nfrom services.variant_detection_service import (\n    get_variant_groups,\n    merge_variant_group,\n    unmerge_variant_group,\n)',
    content2,
    flags=re.DOTALL
)

endpoints = '''

@router.get(
    "/{batch_id}/variant-groups",
    response_model=VariantGroupsResponse,
    status_code=status.HTTP_200_OK,
)
def get_batch_variant_groups(
    batch_id: int,
    db: Session = Depends(get_db),
):
    groups = get_variant_groups(db=db, batch_id=batch_id)
    total_variant_rows = sum(g['member_count'] for g in groups)
    return {
        'batch_id': batch_id,
        'total_groups': len(groups),
        'total_variant_rows': total_variant_rows,
        'groups': groups,
    }


@router.post(
    "/{batch_id}/variant-groups/{group_key}/merge",
    response_model=VariantMergeResponse,
    status_code=status.HTTP_200_OK,
)
def merge_batch_variant_group(
    batch_id: int,
    group_key: str,
    db: Session = Depends(get_db),
):
    return merge_variant_group(
        db=db,
        batch_id=batch_id,
        group_key=group_key,
    )


@router.post(
    "/{batch_id}/variant-groups/{group_key}/unmerge",
    response_model=VariantMergeResponse,
    status_code=status.HTTP_200_OK,
)
def unmerge_batch_variant_group(
    batch_id: int,
    group_key: str,
    db: Session = Depends(get_db),
):
    return unmerge_variant_group(
        db=db,
        batch_id=batch_id,
        group_key=group_key,
    )
'''
content2 = content2.rstrip() + '\n' + endpoints + '\n'

with open(file2, 'w', encoding='utf-8') as f:
    f.write(content2)
