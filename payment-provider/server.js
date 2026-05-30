const express = require("express");

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 3003;

// Deterministic 50% rate limit: every other request by sequence number gets 429
let requestCount = 0;

app.post("/charge", (req, res) => {
  requestCount++;
  // odd requests succeed, even requests get rate-limited
  if (requestCount % 2 === 0) {
    return res.status(429).json({ error: "rate_limited", retry_after: 1 });
  }
  res.json({ status: "charged", amount: req.body?.amount || 0 });
});

app.get("/health", (req, res) => {
  res.json({ status: "ok", requests_served: requestCount });
});

app.listen(PORT, () => {
  console.log(`payment-provider listening on :${PORT} (50% deterministic rate-limit)`);
});
