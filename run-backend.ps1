.\venv\Scripts\Activate.ps1
Set-Location backend
uvicorn app.main:app --reload
