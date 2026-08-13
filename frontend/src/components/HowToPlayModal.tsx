import { useState, useEffect } from "react";

interface HowToPlayModalProps {
  onClose: () => void;
}

export function HowToPlayModal({ onClose }: HowToPlayModalProps) {
  const [dontShow, setDontShow] = useState(false);

  useEffect(() => {
    // Prevent scrolling on body when modal is open
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = "auto";
    };
  }, []);

  const handleClose = () => {
    if (dontShow) {
      localStorage.setItem("kadi_intro_seen", "true");
    }
    onClose();
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <button className="modal-close-btn" onClick={handleClose}>
          ✕
        </button>
        
        <div className="modal-header">
          <h2>Welcome to Kadi Teeri</h2>
          <p className="muted">A partnership trick-taking game</p>
        </div>

        <div className="modal-body">
          <section>
            <h3>🌐 How to Connect & Join</h3>
            <p><strong>Online Play:</strong> Select "Online" mode. The host creates a room and shares the 6-letter room code. Others join using that code over the internet.</p>
            <p><strong>Local Network Play:</strong> Select "Local" mode. All players must be on the same WiFi or Hotspot. The host creates a room and shares the local URL (e.g., <code>http://192.168.x.x:8000</code>). Others open this URL in their browser and enter the room code. No internet required!</p>
          </section>

          <section>
            <h3>🎯 The Objective</h3>
            <p>Players bid for the right to choose the Trump suit and call hidden partners (Bherus). The bidding side must capture enough points to match their bid, while the defending side tries to stop them.</p>
            <ul>
              <li><strong>3 of Spades:</strong> 30 points (The most valuable card!)</li>
              <li><strong>A, K, Q, J, 10:</strong> 10 points each</li>
              <li><strong>5:</strong> 5 points each</li>
              <li>All other cards are worth 0 points.</li>
            </ul>
          </section>

          <section>
            <h3>🗣️ How to Bid</h3>
            <p>Bidding starts at 150 points and goes up in increments of 5. You can bid higher or "Pass". If everyone passes, the last player is forced to take a minimum bid of 150. The highest bidder wins the right to choose the Trump suit.</p>
          </section>

          <section>
            <h3>🕵️ Calling Bherus (Hidden Partners)</h3>
            <p>After choosing Trump, the bidder calls specific cards (e.g., "Ace of Hearts"). Whoever holds those cards becomes the bidder's hidden partner. <strong>Nobody knows who the partners are until the called card is played during the game!</strong></p>
            <ul>
              <li><strong>1-Deck games:</strong> You just name the card you want as your partner.</li>
              <li><strong>2-Deck games:</strong> You can call "Fix" (you hold one copy, you want the other), "Both" (you want whoever holds either copy), or "Second" (whoever plays the card second becomes the partner).</li>
            </ul>
          </section>

          <section>
            <h3>🃏 How to Play</h3>
            <p>The bidder leads the first trick. You <strong>must follow the lead suit</strong> if you have it. If you don't, you can play a Trump card to win the trick, or throw any other card.</p>
            <p>The highest Trump wins the trick. If no Trump is played, the highest card of the lead suit wins. The winner of the trick collects the points and leads the next trick.</p>
          </section>
        </div>

        <div className="modal-footer">
          <label className="dont-show-label">
            <input 
              type="checkbox" 
              checked={dontShow} 
              onChange={(e) => setDontShow(e.target.checked)} 
            />
            Don't show this again
          </label>
          <button className="btn btn-primary" onClick={handleClose}>
            Let's Play!
          </button>
        </div>
      </div>
    </div>
  );
}
