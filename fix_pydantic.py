import os

faq_schema_path = r"f:\0- Acompañar\Acompaniar-bf\backend-acompanar\app\schemas\faq.py"
with open(faq_schema_path, "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("orm_mode = True", "from_attributes = True")

with open(faq_schema_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Fixed Pydantic config")
