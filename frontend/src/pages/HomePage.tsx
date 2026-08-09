import { useState } from "react";
import { useGameStore } from "../store/gameStore";

const API_BASE =
  import.meta.env.VITE_API_URL || "";

export function HomePage() {
  const { playerName, setPlayerName, showToast } = useGameStore();
  const [name, setName] = useState(playerName || "");
  const [joinCode, setJoinCode] = useState("");
  const [loading, setLoading] = useState(false);


  const handleCreate = async () => {
    const trimmed = name.trim().slice(0, 18);
    if (!trimmed) {
      showToast("Enter your name first.");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/rooms`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ player_name: trimmed }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        showToast(err.detail || "Could not create room.");
        setLoading(false);
        return;
      }
      const data = await res.json();
      setPlayerName(trimmed);

      // Save session for reconnect
      localStorage.setItem(
        "kadi_session",
        JSON.stringify({
          roomId: data.room_id,
          playerId: data.player_id,
          playerName: trimmed,
        })
      );

      // Connect via WebSocket
      const connectWs = (window as any).__kadiConnect;
      if (connectWs) {
        connectWs(data.room_id, data.player_id, trimmed);
      }
    } catch {
      showToast("Could not create room. Check your connection.");
    }
    setLoading(false);
  };

  const handleJoin = async () => {
    const trimmed = name.trim().slice(0, 18);
    const code = joinCode.trim().toUpperCase();
    if (!trimmed) {
      showToast("Enter your name first.");
      return;
    }
    if (!code) {
      showToast("Enter a room code.");
      return;
    }
    setLoading(true);
    try {
      // Check room exists first
      const res = await fetch(`${API_BASE}/api/rooms/${code}`);
      const info = await res.json();
      if (!info.exists) {
        showToast("No room found with that code.");
        setLoading(false);
        return;
      }
      if (!info.can_join) {
        showToast(
          info.status !== "lobby"
            ? "That game has already started."
            : "That room is full."
        );
        setLoading(false);
        return;
      }

      setPlayerName(trimmed);

      // Connect via WebSocket
      const connectWs = (window as any).__kadiConnect;
      if (connectWs) {
        connectWs(code, null, trimmed);
      }
    } catch {
      showToast("Could not join room. Check your connection.");
    }
    setLoading(false);
  };

  return (
    <>
      <div className="hero">
        <svg className="logo-mark" width="60" height="68" viewBox="0 0 64 72">
          <path
            d="M32 4 C10 24 4 40 4 48 C4 58 12 64 22 64 C26 64 29 63 32 61 C29 68 24 70 18 70 L46 70 C40 70 35 68 32 61 C35 63 38 64 42 64 C52 64 60 58 60 48 C60 40 54 24 32 4 Z"
            fill="#171310"
            stroke="#d4af37"
            strokeWidth="1.5"
          />
          <text
            x="32"
            y="47"
            textAnchor="middle"
            fontFamily="Fraunces, serif"
            fontSize="26"
            fill="#d4af37"
            fontWeight="700"
          >
            3
          </text>
        </svg>
        <div className="eyebrow">A partnership trick-taking game</div>
        <h1>Kadi Teeri</h1>
        <p className="tag">
          Bid for points, name your trump, and quietly call a partner nobody else
          can see — not even you'll know their face until the card gives them
          away.
        </p>
      </div>

      <div className="panel">
        <div className="home-actions">
          <input
            className="name-field"
            placeholder="Your name"
            maxLength={18}
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
          />
          <button
            className="btn btn-primary btn-block"
            onClick={handleCreate}
            disabled={loading}
          >
            {loading ? "Creating…" : "Create a room"}
          </button>

          <div className="divider">or join with a code</div>

          <input
            className="name-field"
            placeholder="6-letter room code"
            maxLength={6}
            value={joinCode}
            onChange={(e) => setJoinCode(e.target.value.toUpperCase())}
            style={{
              textTransform: "uppercase",
              fontFamily: "var(--font-mono)",
              letterSpacing: ".1em",
            }}
            onKeyDown={(e) => e.key === "Enter" && handleJoin()}
          />
          <button
            className="btn btn-teal btn-block"
            onClick={handleJoin}
            disabled={loading}
          >
            {loading ? "Joining…" : "Join room"}
          </button>
        </div>
      </div>

      <div className="rules-note">
        <b>How a round works:</b> Players get equal cards. Players bid points
        (min 150) for the right to name trump. The winning bidder calls for
        bheru card(s) — whoever holds them becomes their hidden partner(s),
        unknown to everyone until those exact cards are played. The bidder's side
        needs to capture at least the bid in point-cards to win. The 3 of Spades
        alone is worth 30 points!
      </div>

      <div className="footer-note">
        Share your room code with friends to play together — no accounts needed.
      </div>
    </>
  );
}
