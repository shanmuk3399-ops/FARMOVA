# Farmova Main Backend
Run the main Farmova API with:
python -m uvicorn app.main:app --reload --port 8000
Main API: http://127.0.0.1:8000
Swagger: http://127.0.0.1:8000/docs
Frontend should use the main backend on port 8000 for /api/ai and /api/logistics.
Demand forecasting is available at GET /api/ai/demand-forecast and uses recorded marketplace demand from demand history, buyer offers, and completed/active orders.
The separate ai_service and logistics_service folders remain available as modular services, but the main Farmova web flow does not require clients to call their ports directly.
