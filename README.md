# Smart Cash & Carry

An e-commerce storefront and administration backend system built with Python, FastAPI, and SQLAlchemy. 

## 🚀 Features
- **Storefront & Administration API:** Separate interfaces for customers and store administrators.
- **Role-Based Access Control (RBAC):** Secure admin panel with granular permissions.
- **Product Management:** Manage categories, products, variants, and galleries.
- **Inventory & Pricing:** Stock management, variable pricing, and bulk price imports via Excel.
- **Order Management:** Track customer orders, including WhatsApp-integrated orders.
- **Media Management:** Support for local media uploads and Cloudinary integration.
- **Content Management:** Customizable storefront content and dynamic displays.

## 🛠️ Technology Stack
- **Backend:** FastAPI, Python 3.x
- **Database:** PostgreSQL (SQLAlchemy ORM, psycopg)
- **Frontend / Templates:** Jinja2, HTML/CSS/JS
- **Authentication / Security:** pwdlib (Argon2)
- **Media & File Handling:** Pillow, python-multipart, Cloudinary
- **Data Imports:** openpyxl, xlrd (Excel support)
- **Server:** Uvicorn
