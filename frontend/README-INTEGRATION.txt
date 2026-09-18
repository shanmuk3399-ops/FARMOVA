FarmDirect frontend integration package
1. Replace the contents of the repo's frontend folder with these files.
2. The frontend now uses /auth/login, /auth/register, /produce/all, /produce/add, /offers/*, /aggregation/* and /api/ai/predict-price.
3. Set the deployed backend URL in browser localStorage as farmDirectApiBase when deploying the frontend.
4. The current GitHub backend does not expose a logistics endpoint or produce DELETE endpoint, so logistics uses the existing client-side map estimate and the farmer dashboard does not pretend delete is supported.
5. AI request is sent as JSON to POST /api/ai/predict-price and falls back to an estimate if the AI service rejects/unavailable.
