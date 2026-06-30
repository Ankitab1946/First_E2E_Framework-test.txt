"""Run the FastAPI application with: poetry run python -m DataDictionaryAdminApp.api"""
import uvicorn

if __name__ == '__main__':
    uvicorn.run('DataDictionaryAdminApp.api.swagger_app:app', host='0.0.0.0', port=8502, reload=True)
