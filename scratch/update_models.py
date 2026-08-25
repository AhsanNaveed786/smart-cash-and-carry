import sys

with open('d:/Projects/smart-cash-and-carry/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = """    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )"""

replacement = """    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    variant_group_key: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    variant_size_label: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    merge_as_variant: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    variant_master_row_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "product_import_rows.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )"""

new_content = content.replace(target, replacement)

if new_content == content:
    print("No changes made!")
    sys.exit(1)

with open('d:/Projects/smart-cash-and-carry/models.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Updated models.py successfully.")
