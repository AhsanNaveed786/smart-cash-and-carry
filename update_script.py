import re

file1 = 'schemas.py'
with open(file1, 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(
    r'(    error_message: str \| None\n)',
    r'\g<1>    variant_group_key: str | None = None\n    variant_size_label: str | None = None\n    merge_as_variant: bool = False\n',
    content
)

variant_schemas = '''

class VariantGroupMember(SchemaBase):
    row_id: int
    item_name: str | None
    size_label: str | None
    uploaded_price: Decimal | None
    merge_as_variant: bool
    is_master: bool


class VariantGroupResponse(SchemaBase):
    group_key: str
    base_name: str
    member_count: int
    is_merged: bool
    master_row_id: int | None
    members: list[VariantGroupMember]


class VariantGroupsResponse(SchemaBase):
    batch_id: int
    total_groups: int
    total_variant_rows: int
    groups: list[VariantGroupResponse]


class VariantMergeResponse(SchemaBase):
    group_key: str
    merged: bool
    master_row_id: int | None = None
    member_count: int
'''
content = re.sub(
    r'(class ProductImportQuickCategorizeResponse\(SchemaBase\):.*?    message: str\n)',
    r'\g<1>' + variant_schemas,
    content,
    flags=re.DOTALL
)

with open(file1, 'w', encoding='utf-8') as f:
    f.write(content)

file2 = 'routers/product_import_router.py'
with open(file2, 'r', encoding='utf-8') as f:
    content2 = f.read()

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

# Also ensure `status` and `AdminSession` are imported correctly in file2 since endpoints use them
if 'status' not in content2:
    content2 = content2.replace('from fastapi import (', 'from fastapi import (\n    status,')
if 'AdminSession' not in content2:
    content2 = content2.replace('from dependencies.admin_access import permission_required', 'from dependencies.admin_access import permission_required, require_admin_access\nfrom schemas import AdminSession')
# Wait, what is the type of `_admin: AdminSession = Depends(require_admin_access)`? 
# Usually AdminSession is defined in schemas, and require_admin_access in dependencies.admin_access.
# Let's check imports. Wait, AdminResponse is in schemas. Let's just blindly add it and see if it fails.
if 'require_admin_access' not in content2:
    content2 = content2.replace('from dependencies.admin_access import permission_required', 'from dependencies.admin_access import permission_required, require_admin_access')
    
content2 = re.sub(r'from schemas import \(', 'from schemas import AdminSession,\n    ', content2, count=1)


endpoints = '''

@router.get(
    "/{batch_id}/variant-groups",
    response_model=VariantGroupsResponse,
    status_code=status.HTTP_200_OK,
)
def get_batch_variant_groups(
    batch_id: int,
    db: Session = Depends(get_db),
    _admin: AdminSession = Depends(require_admin_access),
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
    _admin: AdminSession = Depends(require_admin_access),
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
    _admin: AdminSession = Depends(require_admin_access),
):
    return unmerge_variant_group(
        db=db,
        batch_id=batch_id,
        group_key=group_key,
    )
'''
content2 = content2.rstrip() + '\\n' + endpoints + '\\n'

with open(file2, 'w', encoding='utf-8') as f:
    f.write(content2)
