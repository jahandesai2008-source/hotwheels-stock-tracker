export default async function handler(req, res) {
  if (req.method !== "GET") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.TELEGRAM_CHAT_ID;

  if (!token || !chatId) {
    return res.status(500).json({
      error: "Telegram environment variables are missing"
    });
  }

  try {
    const response = await fetch(
      `https://api.telegram.org/bot${token}/sendMessage`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chat_id: chatId,
          text: "🚗 Hot Wheels Tracker is connected! Notifications are working."
        })
      }
    );

    const result = await response.json();

    return res.status(response.ok ? 200 : 502).json(result);
  } catch (error) {
    return res.status(500).json({ error: "Telegram request failed" });
  }
}
