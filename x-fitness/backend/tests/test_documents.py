from fastapi.testclient import TestClient

from app.main import app

FILES = ["XFitness-Chatbot_Presentation-Deck.html", "XFitness-Chatbot_Presentation_Summary.html",
         "XFitness-Chatbot_Presentation.pptx", "XFitness-Chatbot_Project-Report.docx"]


def test_documents_index_links_every_file():
    page = TestClient(app).get("/documents/")
    assert page.status_code == 200
    assert all(f'href="{name}"' in page.text for name in FILES)


def test_documents_files_download():
    client = TestClient(app)
    assert all(client.head(f"/documents/{name}").status_code == 200 for name in FILES)
    assert client.get("/docs").status_code == 200          # Swagger keeps its address
