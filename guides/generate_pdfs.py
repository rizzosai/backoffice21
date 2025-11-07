import os
import sys
import markdown2
from weasyprint import HTML

def md_to_pdf(md_path, pdf_path, username):
    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read().replace('{{USERNAME}}', username)
        html = markdown2.markdown(md_content)
    HTML(string=html).write_pdf(pdf_path)

if __name__ == "__main__":
    # Usage: python generate_pdfs.py [username]
    username = 'yourusername'
    if len(sys.argv) > 1:
        if sys.argv[1] == 'admin4':
            username = 'rizzosai'
        else:
            username = sys.argv[1]

    guides = [
        ("upgrade_stripe_account.md", "upgrade_stripe_account.pdf"),
        ("make_money_online_beginner.md", "make_money_online_beginner.pdf")
    ]
    for md, pdf in guides:
        md_path = os.path.join(os.path.dirname(__file__), md)
        pdf_path = os.path.join(os.path.dirname(__file__), pdf)
        md_to_pdf(md_path, pdf_path, username)
    print(f"PDFs generated successfully for username: {username}")
