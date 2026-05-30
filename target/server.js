const express = require("express");
const Redis = require("ioredis");
const fetch = require("node-fetch");

const app = express();
const PORT = process.env.PORT || 3000;
const REDIS_PORT = parseInt(process.env.REDIS_PORT || "6380");
const REDIS_HOST = process.env.REDIS_HOST || "redis";
const PAYMENT_URL = process.env.PAYMENT_URL || "http://payment-provider:3003";
const ENABLE_BACKOFF = process.env.ENABLE_BACKOFF !== "false";
const MAX_PAYMENT_RETRIES = parseInt(process.env.MAX_PAYMENT_RETRIES || "3");

const redis = new Redis({ host: REDIS_HOST, port: REDIS_PORT, lazyConnect: true });

redis.on("error", () => {});

async function callPaymentProvider(attempt = 1) {
  const res = await fetch(`${PAYMENT_URL}/charge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ amount: 100 }),
  });

  if (res.status === 429 && attempt < MAX_PAYMENT_RETRIES) {
    if (ENABLE_BACKOFF) {
      await new Promise((r) => setTimeout(r, Math.pow(2, attempt) * 100));
    }
    return callPaymentProvider(attempt + 1);
  }

  return res;
}

app.get("/health", async (req, res) => {
  const errors = [];

  // Check Redis
  try {
    await redis.ping();
  } catch (err) {
    errors.push(`redis: ${err.message}`);
  }

  // Check payment provider
  try {
    const payRes = await callPaymentProvider();
    if (!payRes.ok && payRes.status !== 429) {
      errors.push(`payment: HTTP ${payRes.status}`);
    }
  } catch (err) {
    errors.push(`payment: ${err.message}`);
  }

  if (errors.length > 0) {
    return res.status(503).json({ status: "unhealthy", errors });
  }

  res.json({ status: "ok", redis_port: REDIS_PORT, backoff: ENABLE_BACKOFF });
});

app.get("/", (req, res) => res.json({ service: "target", version: process.env.VERSION || "v1" }));

app.listen(PORT, () => {
  console.log(`target service listening on :${PORT} (redis=${REDIS_HOST}:${REDIS_PORT} backoff=${ENABLE_BACKOFF})`);
});
