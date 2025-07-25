import requests

def submit_answers(team_token, document_url, questions, answers):
    payload = {
        "documents": document_url,
        "questions": questions,
        "answers": answers
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {team_token}"
    }

    response = requests.post("http://localhost:8000/api/v1/hackrx/run", headers=headers, json=payload)
    return response.status_code, response.json()

