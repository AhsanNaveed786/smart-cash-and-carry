import re

with open(r'd:\Projects\smart-cash-and-carry\frontend\routers\frontend_router.py', 'r') as f:
    content = f.read()

# Add db: Session = Depends(get_db) to all route defs
content = re.sub(
    r'def (storefront_home|storefront_shop|storefront_product|storefront_cart|storefront_checkout|storefront_track_order|admin_login_page|admin_dashboard_page)\(([^)]*)\):',
    r'def \1(\2, db: Session = Depends(get_db)):',
    content
)
# Add Depends to imports if not there
if 'Depends' not in content:
    content = content.replace('from fastapi import APIRouter, Request', 'from fastapi import APIRouter, Request, Depends')

# Pass db to page_context
content = re.sub(
    r'page_context\(\s*request,\s*"([^"]+)",\s*"([^"]+)"(.*?)\)',
    r'page_context(request, "\1", "\2", db=db\3)',
    content,
    flags=re.DOTALL
)

with open(r'd:\Projects\smart-cash-and-carry\frontend\routers\frontend_router.py', 'w') as f:
    f.write(content)
print("Router patched!")
